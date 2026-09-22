from datetime import datetime, timezone
from enum import Enum
import os
from pathlib import Path
from typing import Optional
from uuid import uuid4
import secrets
import time
import json
import urllib.request
import urllib.error

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .ai_analyzer import analyze_image
from .auth import create_token, decode_token, hash_password, verify_password
from .database import find_user_by_email, init_db, load_reports, load_users, save_report, save_user, update_user_password
from .location_service import google_geolocate, google_reverse_geocode
from .ip_location import lookup_ip_location
from .notifications import notify_report_created, notify_reporter, send_otp_email

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Role(str, Enum):
    citizen = "citizen"
    administrator = "administrator"
    collector = "collector"


class ReportStatus(str, Enum):
    reported = "reported"
    ai_analyzed = "ai_analyzed"
    reviewed = "reviewed"
    assigned = "assigned"
    in_progress = "in_progress"
    collected = "collected"
    verified = "verified"
    rejected = "rejected"


class User(BaseModel):
    user_id: str
    name: str
    role: Role


class Report(BaseModel):
    report_id: str
    user_id: str
    image_reference: str
    ai_result: Optional[str] = None
    category: Optional[str] = None
    latitude: float
    longitude: float
    description: Optional[str] = None
    timestamp: datetime
    status: ReportStatus
    collector_id: Optional[str] = None
    evidence_reference: Optional[str] = None


class StatusUpdate(BaseModel):
    status: ReportStatus


class AssignmentRequest(BaseModel):
    collector_id: str = Field(min_length=1)


class EvidenceRequest(BaseModel):
    evidence_reference: str = Field(min_length=1)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=5, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=5, max_length=128)


class VerifyOtpRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    otp: str = Field(min_length=6, max_length=6)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)


class ResetPasswordRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    otp: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=5, max_length=128)


class GoogleLocationRequest(BaseModel):
    home_mobile_country_code: Optional[int] = Field(None, alias="homeMobileCountryCode")
    home_mobile_network_code: Optional[int] = Field(None, alias="homeMobileNetworkCode")
    radio_type: Optional[str] = Field(None, alias="radioType")
    carrier: Optional[str] = None
    consider_ip: bool = Field(True, alias="considerIp")

    class Config:
        populate_by_name = True


class CoordinatesRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


app = FastAPI(title="EcoTrack AI API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

users = {
    "citizen-demo": User(user_id="citizen-demo", name="Demo Citizen", role=Role.citizen),
    "admin-demo": User(user_id="admin-demo", name="Demo Admin", role=Role.administrator),
    "collector-demo": User(user_id="collector-demo", name="Demo Collector", role=Role.collector),
}
reports: dict[str, Report] = {}
otps: dict[str, dict[str, object]] = {}

UPLOADS_DIR = Path(os.getenv("ECOTRACK_UPLOADS_DIR", "uploads"))
REPORTS_DIR = UPLOADS_DIR / "reports"
EVIDENCE_DIR = UPLOADS_DIR / "evidence"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
init_db()
for demo_id, demo_name, demo_role, demo_email, demo_password in [
    ("admin-demo", "Demo Admin", Role.administrator, "admin@ecotrack.local", "admin12345"),
    ("collector-demo", "Demo Collector", Role.collector, "collector@ecotrack.local", "collector123"),
]:
    if not find_user_by_email(demo_email):
        save_user(demo_id, demo_name, demo_email, demo_role.value, hash_password(demo_password), datetime.now(timezone.utc).isoformat())
for stored_user in load_users():
    users[stored_user["user_id"]] = User(
        user_id=stored_user["user_id"], name=stored_user["name"], role=stored_user["role"]
    )
reports.update(load_reports())


def get_user(user_id: str) -> User:
    user = users.get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user")
    return user


def require_role(user_id: str, *roles: Role) -> User:
    user = get_user(user_id)
    if user.role not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return user


def get_report(report_id: str) -> Report:
    report = reports.get(report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/location/google")
def google_location(request: GoogleLocationRequest) -> dict[str, object]:
    try:
        return google_geolocate(request.model_dump(exclude_none=True))
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.post("/location/reverse-geocode")
def reverse_geocode(request: CoordinatesRequest) -> dict[str, object]:
    try:
        return google_reverse_geocode(request.latitude, request.longitude)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.get("/location/ip")
def ip_location(request: Request) -> dict[str, object]:
    forwarded_for = request.headers.get("x-forwarded-for")
    client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else request.client.host if request.client else None
    try:
        return lookup_ip_location(client_ip)
    except ValueError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.get("/")
def api_root() -> dict[str, str]:
    return {"name": "EcoTrack AI API", "docs": "/docs", "frontend": "http://127.0.0.1:5500/"}


@app.post("/auth/register", response_model=dict[str, str], status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest) -> dict[str, str]:
    email = request.email.strip().lower()
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise HTTPException(status_code=400, detail="A valid email address is required")
    if find_user_by_email(email):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user_id = f"usr-{uuid4().hex[:8]}"
    save_user(user_id, request.name.strip(), email, Role.citizen.value, hash_password(request.password), datetime.now(timezone.utc).isoformat())
    users[user_id] = User(user_id=user_id, name=request.name.strip(), role=Role.citizen)
    return {"access_token": create_token(user_id, Role.citizen.value), "token_type": "bearer", "user_id": user_id}


@app.post("/auth/login", response_model=dict[str, str])
def login(request: LoginRequest) -> dict[str, str]:
    email = request.email.strip().lower()
    
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise HTTPException(status_code=400, detail="A valid email address is required")
        
    stored_user = find_user_by_email(email)
    if not stored_user or not verify_password(request.password, stored_user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid ID or password. Please check your login details.")
    
    otp_code = "".join(secrets.choice("0123456789") for _ in range(6))
    otps[email] = {"otp": otp_code, "expires": time.time() + 300}
    
    send_status = send_otp_email(email, otp_code)
    
    response = {
        "status": "otp_sent",
        "email": email,
        "detail": send_status,
    }
    if send_status.startswith("dev-otp:"):
        response["otp"] = send_status.removeprefix("dev-otp:")
    return response


@app.post("/auth/verify-otp", response_model=dict[str, str])
def verify_otp(request: VerifyOtpRequest) -> dict[str, str]:
    email = request.email.strip().lower()
    stored_otp_data = otps.get(email)
    
    if not stored_otp_data:
        raise HTTPException(status_code=401, detail="No OTP requested or OTP expired")
        
    if time.time() > stored_otp_data["expires"]:
        del otps[email]
        raise HTTPException(status_code=401, detail="OTP expired")
        
    if request.otp != stored_otp_data["otp"]:
        raise HTTPException(status_code=401, detail="Invalid OTP")
        
    del otps[email]
    
    stored_user = find_user_by_email(email)
    if not stored_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return {
        "access_token": create_token(stored_user["user_id"], stored_user["role"]),
        "token_type": "bearer",
        "user_id": stored_user["user_id"],
    }


@app.post("/auth/forgot-password", response_model=dict[str, str])
def forgot_password(request: ForgotPasswordRequest) -> dict[str, str]:
    email = request.email.strip().lower()
    stored_user = find_user_by_email(email)
    if not stored_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    otp_code = "".join(secrets.choice("0123456789") for _ in range(6))
    otps[email] = {"otp": otp_code, "expires": time.time() + 300}
    
    send_status = send_otp_email(email, otp_code)
    
    return {
        "status": "otp_sent",
        "email": email,
        "detail": send_status,
    }


@app.post("/auth/reset-password", response_model=dict[str, str])
def reset_password(request: ResetPasswordRequest) -> dict[str, str]:
    email = request.email.strip().lower()
    stored_otp_data = otps.get(email)
    
    if not stored_otp_data:
        raise HTTPException(status_code=401, detail="No OTP requested or OTP expired")
        
    if time.time() > stored_otp_data["expires"]:
        del otps[email]
        raise HTTPException(status_code=401, detail="OTP expired")
        
    if request.otp != stored_otp_data["otp"]:
        raise HTTPException(status_code=401, detail="Invalid OTP")
        
    del otps[email]
    
    stored_user = find_user_by_email(email)
    if not stored_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    update_user_password(email, hash_password(request.new_password))
    
    return {
        "access_token": create_token(stored_user["user_id"], stored_user["role"]),
        "token_type": "bearer",
        "user_id": stored_user["user_id"],
    }


@app.get("/auth/me", response_model=User)
def current_user(authorization: Optional[str] = Header(None)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Bearer token is required")
    payload = decode_token(authorization[7:].strip())
    if not payload or payload.get("sub") not in users:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return users[payload["sub"]]


def authenticated_user(authorization: Optional[str]) -> User:
    return current_user(authorization)


@app.post("/reports", response_model=Report, status_code=status.HTTP_201_CREATED)
async def create_report(
    user_id: Optional[str] = Form(None),
    latitude: float = Form(..., ge=-90, le=90),
    longitude: float = Form(..., ge=-180, le=180),
    description: Optional[str] = Form(None, max_length=1000),
    image: UploadFile = File(...),
    authorization: Optional[str] = Header(None),
) -> Report:
    user = authenticated_user(authorization)
    if user.role != Role.citizen:
        raise HTTPException(status_code=403, detail="Only citizens can submit reports")
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if image.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, and WebP images are supported")
    filename = Path(image.filename or "upload").name
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded image is empty")
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image must be smaller than 10 MB")
    try:
        analysis = analyze_image(image_bytes, filename)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    image_path = REPORTS_DIR / f"{uuid4().hex[:8]}-{filename}"
    image_path.write_bytes(image_bytes)

    report = Report(
        report_id=f"rpt-{uuid4().hex[:8]}",
        user_id=user.user_id,
        image_reference=str(image_path),
        latitude=latitude,
        longitude=longitude,
        description=description,
        timestamp=datetime.now(timezone.utc),
        status=ReportStatus.ai_analyzed,
        ai_result=analysis["ai_result"],
        category=analysis["category"],
    )
    reports[report.report_id] = report
    save_report(report)
    
    notify_report_created(report.report_id, report.user_id)
    
    return report


@app.get("/reports/{report_id}", response_model=Report)
def report_detail(report_id: str, authorization: Optional[str] = Header(None)) -> Report:
    user = authenticated_user(authorization)
    report = get_report(report_id)
    if user.role == Role.administrator or report.user_id == user.user_id or report.collector_id == user.user_id:
        return report
    raise HTTPException(status_code=403, detail="You cannot access this report")


@app.get("/collectors", response_model=list[User])
def list_collectors(authorization: Optional[str] = Header(None)) -> list[User]:
    require_role(authenticated_user(authorization).user_id, Role.administrator)
    return [user for user in users.values() if user.role == Role.collector]


@app.get("/reports", response_model=list[Report])
def list_reports(
    status_filter: Optional[ReportStatus] = None,
    category: Optional[str] = None,
    authorization: Optional[str] = Header(None),
) -> list[Report]:
    user = authenticated_user(authorization)
    result = list(reports.values())
    if status_filter:
        result = [report for report in result if report.status == status_filter]
    if category:
        result = [report for report in result if report.category == category]
    if user.role == Role.citizen:
        result = [report for report in result if report.user_id == user.user_id]
    return result


@app.patch("/reports/{report_id}/status", response_model=Report)
def update_status(report_id: str, update: StatusUpdate, authorization: Optional[str] = Header(None)) -> Report:
    report = get_report(report_id)
    user = authenticated_user(authorization)
    if user.role == Role.administrator:
        allowed = set(ReportStatus)
    elif user.role == Role.collector and report.collector_id == user.user_id:
        allowed = {ReportStatus.in_progress, ReportStatus.collected}
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if update.status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid status transition for this role")
    report.status = update.status
    save_report(report)
    if report.status in (ReportStatus.collected, ReportStatus.verified):
        notify_reporter(report.report_id, report.user_id, None)
    return report


@app.post("/reports/{report_id}/assignment", response_model=Report)
def assign_report(report_id: str, request: AssignmentRequest, authorization: Optional[str] = Header(None)) -> Report:
    user = authenticated_user(authorization)
    require_role(user.user_id, Role.administrator)
    collector = require_role(request.collector_id, Role.collector)
    report = get_report(report_id)
    report.collector_id = collector.user_id
    report.status = ReportStatus.assigned
    save_report(report)
    return report


@app.post("/reports/{report_id}/evidence", response_model=Report)
async def submit_evidence(
    report_id: str,
    evidence: Optional[UploadFile] = File(None),
    evidence_reference: Optional[str] = Form(None, min_length=1),
    authorization: Optional[str] = Header(None),
) -> Report:
    report = get_report(report_id)
    user = authenticated_user(authorization)
    require_role(user.user_id, Role.collector)
    if report.collector_id != user.user_id or report.status != ReportStatus.collected:
        raise HTTPException(status_code=400, detail="Report is not ready for evidence submission")
    if evidence:
        if evidence.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise HTTPException(status_code=400, detail="Evidence must be a JPEG, PNG, or WebP image")
        safe_name = Path(evidence.filename or "evidence").name
        evidence_path = EVIDENCE_DIR / f"{report.report_id}-{safe_name}"
        evidence_path.write_bytes(await evidence.read())
        report.evidence_reference = str(evidence_path)
    elif evidence_reference:
        report.evidence_reference = evidence_reference
    else:
        raise HTTPException(status_code=400, detail="Upload evidence image or provide an evidence reference")
    save_report(report)
    return report


@app.post("/reports/{report_id}/verify", response_model=Report)
def verify_report(report_id: str, approved: bool, authorization: Optional[str] = Header(None)) -> Report:
    user = authenticated_user(authorization)
    require_role(user.user_id, Role.administrator)
    report = get_report(report_id)
    if not report.evidence_reference:
        raise HTTPException(status_code=400, detail="Completion evidence is required")
    report.status = ReportStatus.verified if approved else ReportStatus.rejected
    save_report(report)
    if approved:
        notify_reporter(report.report_id, report.user_id, None)
    return report


@app.get("/analytics")
def analytics(authorization: Optional[str] = Header(None)) -> dict[str, object]:
    user = authenticated_user(authorization)
    visible_reports = list(reports.values())
    if user.role == Role.citizen:
        visible_reports = [report for report in visible_reports if report.user_id == user.user_id]
    elif user.role == Role.collector:
        visible_reports = [report for report in visible_reports if report.collector_id == user.user_id]
    status_counts = {report_status.value: 0 for report_status in ReportStatus}
    category_counts: dict[str, int] = {}
    for report in visible_reports:
        status_counts[report.status.value] += 1
        if report.category:
            category_counts[report.category] = category_counts.get(report.category, 0) + 1
    return {
        "total_reports": len(visible_reports),
        "pending_reports": sum(
            count for report_status, count in status_counts.items()
            if report_status not in {ReportStatus.verified.value, ReportStatus.rejected.value}
        ),
        "collected_reports": status_counts[ReportStatus.collected.value] + status_counts[ReportStatus.verified.value],
        "status_counts": status_counts,
        "category_counts": category_counts,
    }


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
if UPLOADS_DIR.exists():
    app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

