import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

DATABASE_PATH = Path(os.getenv("ECOTRACK_DATABASE", "ecotrack.db"))


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                report_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                image_reference TEXT NOT NULL,
                ai_result TEXT,
                category TEXT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                description TEXT,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                collector_id TEXT,
                evidence_reference TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                notification_id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                details_json TEXT,
                target_role TEXT NOT NULL DEFAULT 'administrator',
                is_read INTEGER NOT NULL DEFAULT 0,
                timestamp TEXT NOT NULL
            )
            """
        )


def save_user(user_id: str, name: str, email: str, role: str, password_hash: str, created_at: str) -> None:
    with connect() as connection:
        connection.execute(
            "INSERT INTO users (user_id, name, email, role, password_hash, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, name, email, role, password_hash, created_at),
        )


def update_user_password(email: str, password_hash: str) -> None:
    with connect() as connection:
        connection.execute(
            "UPDATE users SET password_hash = ? WHERE email = ?",
            (password_hash, email.lower()),
        )


def find_user_by_email(email: str) -> dict[str, Any] | None:
    with connect() as connection:
        row = connection.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()
    return dict(row) if row else None


def find_user_by_id(user_id: str) -> dict[str, Any] | None:
    with connect() as connection:
        row = connection.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def load_users() -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute("SELECT user_id, name, email, role FROM users").fetchall()
    return [dict(row) for row in rows]


def load_reports() -> dict[str, Any]:
    from .main import Report

    with connect() as connection:
        rows = connection.execute("SELECT * FROM reports ORDER BY timestamp DESC").fetchall()
    return {
        row["report_id"]: Report(
            report_id=row["report_id"],
            user_id=row["user_id"],
            image_reference=row["image_reference"],
            ai_result=row["ai_result"],
            category=row["category"],
            latitude=row["latitude"],
            longitude=row["longitude"],
            description=row["description"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            status=row["status"],
            collector_id=row["collector_id"],
            evidence_reference=row["evidence_reference"],
        )
        for row in rows
    }


def save_report(report: Any) -> None:
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO reports (
                report_id, user_id, image_reference, ai_result, category,
                latitude, longitude, description, timestamp, status,
                collector_id, evidence_reference
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(report_id) DO UPDATE SET
                ai_result = excluded.ai_result,
                category = excluded.category,
                status = excluded.status,
                collector_id = excluded.collector_id,
                evidence_reference = excluded.evidence_reference
            """,
            (
                report.report_id,
                report.user_id,
                report.image_reference,
                report.ai_result,
                report.category,
                report.latitude,
                report.longitude,
                report.description,
                report.timestamp.isoformat(),
                report.status.value,
                report.collector_id,
                report.evidence_reference,
            ),
        )


def save_notification(
    notification_id: str,
    notification_type: str,
    title: str,
    message: str,
    details_json: str,
    target_role: str = "administrator",
    timestamp: str | None = None,
) -> None:
    from datetime import datetime, timezone

    ts = timestamp or datetime.now(timezone.utc).isoformat()
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO notifications (
                notification_id, type, title, message, details_json, target_role, is_read, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (notification_id, notification_type, title, message, details_json, target_role, ts),
        )


def load_notifications(target_role: str = "administrator", limit: int = 50) -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT notification_id, type, title, message, details_json, target_role, is_read, timestamp
            FROM notifications
            WHERE target_role = ? OR target_role = 'all'
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (target_role, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def mark_notification_read(notification_id: str) -> None:
    with connect() as connection:
        connection.execute(
            "UPDATE notifications SET is_read = 1 WHERE notification_id = ?",
            (notification_id,),
        )


def mark_all_notifications_read(target_role: str = "administrator") -> None:
    with connect() as connection:
        connection.execute(
            "UPDATE notifications SET is_read = 1 WHERE target_role = ? OR target_role = 'all'",
            (target_role,),
        )

