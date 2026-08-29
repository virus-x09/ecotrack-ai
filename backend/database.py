import os
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime
from typing import Any

# Default to a local postgres or just fallback, but in Vercel it will use POSTGRES_URL
POSTGRES_URL = os.getenv("POSTGRES_URL")
if not POSTGRES_URL:
    # Fallback to local SQLite if POSTGRES_URL is missing, to not break completely locally if they don't have Postgres.
    # Wait, the plan was to completely migrate. But let's support Postgres only to keep it simple.
    pass

def connect():
    if not POSTGRES_URL:
        raise Exception("POSTGRES_URL environment variable is not set. Please connect Vercel Postgres.")
    connection = psycopg2.connect(POSTGRES_URL)
    connection.autocommit = True
    return connection


def init_db() -> None:
    try:
        with connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        user_id VARCHAR PRIMARY KEY,
                        name VARCHAR NOT NULL,
                        email VARCHAR UNIQUE NOT NULL,
                        role VARCHAR NOT NULL,
                        password_hash VARCHAR NOT NULL,
                        created_at VARCHAR NOT NULL
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS reports (
                        report_id VARCHAR PRIMARY KEY,
                        user_id VARCHAR NOT NULL,
                        image_reference VARCHAR NOT NULL,
                        ai_result VARCHAR,
                        category VARCHAR,
                        latitude DOUBLE PRECISION NOT NULL,
                        longitude DOUBLE PRECISION NOT NULL,
                        description TEXT,
                        timestamp VARCHAR NOT NULL,
                        status VARCHAR NOT NULL,
                        collector_id VARCHAR,
                        evidence_reference VARCHAR
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS notifications (
                        notification_id VARCHAR PRIMARY KEY,
                        type VARCHAR NOT NULL,
                        title VARCHAR NOT NULL,
                        message TEXT NOT NULL,
                        details_json TEXT,
                        target_role VARCHAR NOT NULL DEFAULT 'administrator',
                        is_read INTEGER NOT NULL DEFAULT 0,
                        timestamp VARCHAR NOT NULL
                    )
                    """
                )
    except Exception as e:
        print(f"Error initializing DB: {e}")


def save_user(user_id: str, name: str, email: str, role: str, password_hash: str, created_at: str) -> None:
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (user_id, name, email, role, password_hash, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                (user_id, name, email, role, password_hash, created_at),
            )


def update_user_password(email: str, password_hash: str) -> None:
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE email = %s",
                (password_hash, email.lower()),
            )


def find_user_by_email(email: str) -> dict[str, Any] | None:
    with connect() as connection:
        with connection.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email.lower(),))
            row = cursor.fetchone()
    return dict(row) if row else None


def find_user_by_id(user_id: str) -> dict[str, Any] | None:
    with connect() as connection:
        with connection.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            row = cursor.fetchone()
    return dict(row) if row else None


def load_users() -> list[dict[str, Any]]:
    with connect() as connection:
        with connection.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("SELECT user_id, name, email, role FROM users")
            rows = cursor.fetchall()
    return [dict(row) for row in rows]


def load_reports() -> dict[str, Any]:
    from .main import Report

    with connect() as connection:
        with connection.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("SELECT * FROM reports ORDER BY timestamp DESC")
            rows = cursor.fetchall()
            
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
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO reports (
                    report_id, user_id, image_reference, ai_result, category,
                    latitude, longitude, description, timestamp, status,
                    collector_id, evidence_reference
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (report_id) DO UPDATE SET
                    ai_result = EXCLUDED.ai_result,
                    category = EXCLUDED.category,
                    status = EXCLUDED.status,
                    collector_id = EXCLUDED.collector_id,
                    evidence_reference = EXCLUDED.evidence_reference
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
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO notifications (
                    notification_id, type, title, message, details_json, target_role, is_read, timestamp
                ) VALUES (%s, %s, %s, %s, %s, %s, 0, %s)
                """,
                (notification_id, notification_type, title, message, details_json, target_role, ts),
            )


def load_notifications(target_role: str = "administrator", limit: int = 50) -> list[dict[str, Any]]:
    with connect() as connection:
        with connection.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                """
                SELECT notification_id, type, title, message, details_json, target_role, is_read, timestamp
                FROM notifications
                WHERE target_role = %s OR target_role = 'all'
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                (target_role, limit),
            )
            rows = cursor.fetchall()
    return [dict(row) for row in rows]


def mark_notification_read(notification_id: str) -> None:
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE notifications SET is_read = 1 WHERE notification_id = %s",
                (notification_id,),
            )


def mark_all_notifications_read(target_role: str = "administrator") -> None:
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE notifications SET is_read = 1 WHERE target_role = %s OR target_role = 'all'",
                (target_role,),
            )
