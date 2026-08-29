import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any


AUTH_SECRET = os.getenv("ECOTRACK_AUTH_SECRET", "change-this-development-secret").encode()
TOKEN_LIFETIME_SECONDS = 60 * 60 * 24


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"{base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_text, digest_text = stored_hash.split("$", 1)
        salt = base64.urlsafe_b64decode(salt_text.encode())
        expected = base64.urlsafe_b64decode(digest_text.encode())
    except (ValueError, UnicodeDecodeError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return hmac.compare_digest(actual, expected)


def _encode(value: dict[str, Any]) -> str:
    return base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":")).encode()).decode().rstrip("=")


def _decode(value: str) -> dict[str, Any]:
    padding = "=" * (-len(value) % 4)
    return json.loads(base64.urlsafe_b64decode(f"{value}{padding}".encode()))


def create_token(user_id: str, role: str) -> str:
    payload = {"sub": user_id, "role": role, "exp": int(time.time()) + TOKEN_LIFETIME_SECONDS}
    encoded = _encode(payload)
    signature = hmac.new(AUTH_SECRET, encoded.encode(), hashlib.sha256).digest()
    return f"{encoded}.{base64.urlsafe_b64encode(signature).decode().rstrip('=')}"


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        encoded, signature_text = token.split(".", 1)
        padding = "=" * (-len(signature_text) % 4)
        signature = base64.urlsafe_b64decode(f"{signature_text}{padding}".encode())
        expected = hmac.new(AUTH_SECRET, encoded.encode(), hashlib.sha256).digest()
        payload = _decode(encoded)
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None
    if not hmac.compare_digest(signature, expected) or payload.get("exp", 0) < time.time():
        return None
    return payload
