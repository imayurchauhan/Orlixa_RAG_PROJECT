import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
import uuid
from typing import Optional

from fastapi import Depends, Header, HTTPException

from app.config import AUTH_SECRET_KEY, GOOGLE_CLIENT_ID
from app.db import get_conn

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PBKDF2_ITERATIONS = 480_000
_TOKEN_TTL_SECONDS = 60 * 60 * 24 * 7


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _token_secret() -> bytes:
    return AUTH_SECRET_KEY.encode("utf-8")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(normalize_email(email)))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${_b64url_encode(salt)}${_b64url_encode(digest)}"


def verify_password(password: str, stored_hash: Optional[str]) -> bool:
    if not stored_hash:
        return False
    try:
        algorithm, iterations, salt_b64, digest_b64 = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            _b64url_decode(salt_b64),
            int(iterations),
        )
        return hmac.compare_digest(_b64url_encode(digest), digest_b64)
    except Exception:
        return False


def _sign_token(message: bytes) -> str:
    signature = hmac.new(_token_secret(), message, hashlib.sha256).digest()
    return _b64url_encode(signature)


def create_access_token(user: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user["id"],
        "email": user["email"],
        "exp": int(time.time()) + _TOKEN_TTL_SECONDS,
    }
    header_part = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_part = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_part}.{payload_part}".encode("utf-8")
    return f"{header_part}.{payload_part}.{_sign_token(signing_input)}"


def decode_access_token(token: str) -> dict:
    try:
        header_part, payload_part, signature = token.split(".", 2)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")

    signing_input = f"{header_part}.{payload_part}".encode("utf-8")
    expected_signature = _sign_token(signing_input)
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid token signature")

    try:
        payload = json.loads(_b64url_decode(payload_part).decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    if payload.get("exp", 0) < int(time.time()):
        raise HTTPException(status_code=401, detail="Token expired")
    return payload


def serialize_user(row) -> dict:
    return {
        "id": row["id"],
        "email": row["email"],
        "full_name": row["full_name"] or "",
        "avatar_url": row["avatar_url"] or "",
        "auth_provider": row["auth_provider"],
    }


def get_user_by_id(user_id: str) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return serialize_user(row) if row else None


def get_user_by_email(email: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE email=?", (normalize_email(email),)).fetchone()
    conn.close()
    return row


def create_user(email: str, password: str, full_name: str = "") -> dict:
    normalized_email = normalize_email(email)
    if not validate_email(normalized_email):
        raise HTTPException(status_code=400, detail="Invalid email address")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if get_user_by_email(normalized_email):
        raise HTTPException(status_code=409, detail="Email already registered")

    conn = get_conn()
    user_id = uuid.uuid4().hex
    conn.execute(
        """
        INSERT INTO users (id, email, password_hash, full_name, auth_provider)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, normalized_email, hash_password(password), full_name.strip(), "email"),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return serialize_user(row)


def authenticate_user(email: str, password: str) -> dict:
    normalized_email = normalize_email(email)
    row = get_user_by_email(normalized_email)
    if row is None or not verify_password(password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return serialize_user(row)


# ── FUTURE SCOPE: Google Authentication ──────────────────────────────────────
# The following functions are kept for future implementation of Google login
# They can be re-enabled when Google OAuth2 integration is required


def verify_google_credential(credential: str) -> dict:
    """[FUTURE SCOPE] Verify Google OAuth2 credential token."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google login is not configured")
    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token
    except ImportError:
        raise HTTPException(status_code=503, detail="Google login dependency is not installed")
    try:
        info = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Google credential")

    email = normalize_email(info.get("email", ""))
    if not email:
        raise HTTPException(status_code=400, detail="Google account is missing an email")

    return {
        "email": email,
        "google_sub": info.get("sub", ""),
        "full_name": info.get("name", ""),
        "avatar_url": info.get("picture", ""),
    }


def upsert_google_user(credential: str) -> dict:
    """[FUTURE SCOPE] Upsert a Google OAuth2 user."""
    google_user = verify_google_credential(credential)
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE google_sub=? OR email=?",
        (google_user["google_sub"], google_user["email"]),
    ).fetchone()

    if row is None:
        user_id = uuid.uuid4().hex
        conn.execute(
            """
            INSERT INTO users (id, email, google_sub, full_name, avatar_url, auth_provider)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                google_user["email"],
                google_user["google_sub"],
                google_user["full_name"],
                google_user["avatar_url"],
                "google",
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    else:
        conn.execute(
            """
            UPDATE users
            SET google_sub=?, full_name=?, avatar_url=?, auth_provider=?
            WHERE id=?
            """,
            (
                google_user["google_sub"],
                google_user["full_name"],
                google_user["avatar_url"],
                "google",
                row["id"],
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE id=?", (row["id"],)).fetchone()

    conn.close()
    return serialize_user(row)


def build_auth_response(user: dict) -> dict:
    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "user": user,
    }


def get_current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)
    user = get_user_by_id(payload["sub"])
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user
