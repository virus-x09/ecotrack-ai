import json
import os
import smtplib
from email.message import EmailMessage
from urllib.error import URLError
from urllib.request import Request, urlopen

from .database import find_user_by_id


def _send_email(recipient: str, report_id: str, address: str) -> str:
    smtp_host = os.getenv("ECOTRACK_SMTP_HOST")
    smtp_user = os.getenv("ECOTRACK_SMTP_USER")
    smtp_password = os.getenv("ECOTRACK_SMTP_PASSWORD")
    smtp_port = int(os.getenv("ECOTRACK_SMTP_PORT", "587"))
    if not all([smtp_host, smtp_user, smtp_password]):
        return "email-not-configured"

    message = EmailMessage()
    message["Subject"] = f"EcoTrack AI: Your Report {report_id} has been Resolved"
    message["From"] = smtp_user
    message["To"] = recipient
    message.set_content(
        f"Hello,\n\nWe are pleased to inform you that your report (Reference No: {report_id}) has been successfully resolved and cleaned.\n\nThank you for helping keep the community clean!\n\nBest,\nThe EcoTrack AI Team"
    )
    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(message)
    return "email-sent"


def _send_agent_webhook(payload: dict[str, object]) -> str:
    webhook_url = os.getenv("ECOTRACK_AGENT_WEBHOOK")
    if not webhook_url:
        return "agent-not-configured"
    request = Request(
        webhook_url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10):
            return "agent-notified"
    except (URLError, TimeoutError):
        return "agent-unavailable"


def notify_reporter(report_id: str, reporter_id: str, address: str | None) -> dict[str, str]:
    user = find_user_by_id(reporter_id)
    if not user:
        return {"email": "reporter-not-found", "agent": "skipped"}
    location = address or "the reported location"
    result = {"email": "email-not-configured", "agent": "agent-not-configured"}
    if user.get("email"):
        try:
            result["email"] = _send_email(user["email"], report_id, location)
        except (OSError, smtplib.SMTPException):
            result["email"] = "email-failed"
    result["agent"] = _send_agent_webhook({
        "event": "location_cleaned",
        "report_id": report_id,
        "reporter_id": reporter_id,
        "reporter_email": user.get("email"),
        "address": address,
    })
    return result


def send_otp_email(recipient: str, otp: str) -> str:
    smtp_host = os.getenv("ECOTRACK_SMTP_HOST")
    smtp_user = os.getenv("ECOTRACK_SMTP_USER")
    smtp_password = os.getenv("ECOTRACK_SMTP_PASSWORD")
    smtp_port = int(os.getenv("ECOTRACK_SMTP_PORT", "587"))

    if not all([smtp_host, smtp_user, smtp_password]):
        print(f"\n[DEV MODE] OTP for {recipient} is: {otp}\n")
        return "email-not-configured-printed-to-console"

    message = EmailMessage()
    message["Subject"] = "Your EcoTrack AI Login OTP"
    message["From"] = smtp_user
    message["To"] = recipient
    message.set_content(f"Hello,\n\nYour One-Time Password (OTP) for logging into EcoTrack AI is:\n\n{otp}\n\nThis OTP will expire in 5 minutes. Do not share it with anyone."
    )
    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(message)
        return "email-sent"
    except (OSError, smtplib.SMTPException) as e:
        print(f"\n[DEV MODE] Failed to send email. OTP for {recipient} is: {otp} (Error: {e})\n")
        return "email-failed"


def notify_report_created(report_id: str, reporter_id: str) -> dict[str, str]:
    user = find_user_by_id(reporter_id)
    if not user:
        return {"email": "reporter-not-found"}
        
    reporter_email = user.get("email")
    if not reporter_email:
        return {"email": "email-not-configured"}
        
    smtp_host = os.getenv("ECOTRACK_SMTP_HOST")
    smtp_user = os.getenv("ECOTRACK_SMTP_USER")
    smtp_password = os.getenv("ECOTRACK_SMTP_PASSWORD")
    smtp_port = int(os.getenv("ECOTRACK_SMTP_PORT", "587"))

    if not all([smtp_host, smtp_user, smtp_password]):
        return {"email": "email-not-configured"}

    message = EmailMessage()
    message["Subject"] = f"EcoTrack AI: Your Report {report_id} has been Received"
    message["From"] = smtp_user
    message["To"] = reporter_email
    message.set_content(
        f"Hello,\n\nWe have successfully received your report. Your Tracking Reference Number is: {report_id}.\n\nYou can use this number to track the status of your complaint in our system.\n\nThank you for helping keep the community clean!\n\nBest,\nThe EcoTrack AI Team"
    )
    
    admin_message = EmailMessage()
    admin_message["Subject"] = f"EcoTrack AI: New Report {report_id} Submitted"
    admin_message["From"] = smtp_user
    admin_message["To"] = "dilipksharma1244@gmail.com"
    admin_message.set_content(
        f"Hello Admin,\n\nA new report has been submitted by {reporter_email} with Tracking Reference Number: {report_id}.\n\nPlease check the dashboard for more details.\n\nBest,\nThe EcoTrack AI System"
    )
    
    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(message)
            server.send_message(admin_message)
        return {"email": "email-sent"}
    except (OSError, smtplib.SMTPException) as e:
        return {"email": "email-failed"}
