import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
import uuid
import datetime
from typing import Optional

from fastapi import Depends, Header, HTTPException
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import AUTH_SECRET_KEY, GOOGLE_CLIENT_ID, SMTP_EMAIL, SMTP_APP_PASSWORD
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
    
    existing_user = get_user_by_email(normalized_email)
    if existing_user:
        # sqlite3.Row does not have .get(), check via keys or direct access
        is_verified = existing_user["is_verified"] if "is_verified" in existing_user.keys() else 0
        if is_verified:
            raise HTTPException(status_code=409, detail="Email already registered")
        else:
            conn = get_conn()
            conn.execute(
                "UPDATE users SET password_hash=?, full_name=? WHERE id=?",
                (hash_password(password), full_name.strip(), existing_user["id"]),
            )
            conn.commit()
            conn.close()
            generate_otp(normalized_email)
            return {"requires_otp": True, "email": normalized_email}

    conn = get_conn()
    user_id = uuid.uuid4().hex
    conn.execute(
        """
        INSERT INTO users (id, email, password_hash, full_name, auth_provider, is_verified)
        VALUES (?, ?, ?, ?, ?, 0)
        """,
        (user_id, normalized_email, hash_password(password), full_name.strip(), "email"),
    )
    conn.commit()
    conn.close()
    
    generate_otp(normalized_email)
    return {"requires_otp": True, "email": normalized_email}


def authenticate_user(email: str, password: str) -> dict:
    normalized_email = normalize_email(email)
    row = get_user_by_email(normalized_email)
    if row is None or not verify_password(password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    is_verified = row["is_verified"] if "is_verified" in row.keys() else 0
    if not is_verified:
        generate_otp(normalized_email)
        return {"requires_otp": True, "email": normalized_email}
        
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


def generate_otp(email: str) -> str:
    normalized_email = normalize_email(email)
    if not validate_email(normalized_email):
        raise HTTPException(status_code=400, detail="Invalid email address")

    otp_code = "".join([str(secrets.randbelow(10)) for _ in range(6)])
    expires_at = datetime.datetime.now() + datetime.timedelta(minutes=10)

    conn = get_conn()
    conn.execute(
        """
        INSERT OR REPLACE INTO user_otps (email, otp_code, expires_at)
        VALUES (?, ?, ?)
        """,
        (normalized_email, otp_code, expires_at.isoformat()),
    )
    conn.commit()
    conn.close()

    if SMTP_EMAIL and SMTP_APP_PASSWORD:
        try:
            msg = MIMEMultipart()
            msg['From'] = f"Orlixa <{SMTP_EMAIL}>"
            msg['To'] = normalized_email
            msg['Subject'] = "Your Orlixa Verification Code"
            body = f"""
            <html>
              <body>
                <h2>Welcome to Orlixa!</h2>
                <p>Your OTP verification code is: <strong style="font-size: 24px; color: #4F46E5;">{otp_code}</strong></p>
                <p>This code will expire in 10 minutes.</p>
              </body>
            </html>
            """
            msg.attach(MIMEText(body, 'html'))
            
            server = smtplib.SMTP('smtp.gmail.com', 587, timeout=5)
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
            server.send_message(msg)
            server.quit()
            print(f"\n[OTP] Sent email to {normalized_email}\n")
        except Exception as e:
            print(f"\n[OTP EMAIL ERROR] {str(e)}\n")
            print(f"\n[OTP] Fallback logging Code for {normalized_email}: {otp_code}\n")
    else:
        print(f"\n[OTP] No SMTP configured. Code for {normalized_email}: {otp_code}\n")
        
    return otp_code


def verify_otp(email: str, otp_code: str) -> dict:
    normalized_email = normalize_email(email)
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM user_otps WHERE email=? AND otp_code=?", (normalized_email, otp_code)
    ).fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid OTP code")

    expires_at = datetime.datetime.fromisoformat(row["expires_at"])
    if expires_at < datetime.datetime.now():
        conn.execute("DELETE FROM user_otps WHERE email=?", (normalized_email,))
        conn.commit()
        conn.close()
        raise HTTPException(status_code=401, detail="OTP code expired")

    # Success: Delete OTP and return user
    conn.execute("DELETE FROM user_otps WHERE email=?", (normalized_email,))

    # Get or create user
    user_row = conn.execute("SELECT * FROM users WHERE email=?", (normalized_email,)).fetchone()
    if user_row:
        conn.execute("UPDATE users SET is_verified = 1 WHERE email=?", (normalized_email,))
        conn.commit()
        user_row = conn.execute("SELECT * FROM users WHERE email=?", (normalized_email,)).fetchone()
    else:
        user_id = uuid.uuid4().hex
        conn.execute(
            """
            INSERT INTO users (id, email, full_name, auth_provider, is_verified)
            VALUES (?, ?, ?, ?, 1)
            """,
            (user_id, normalized_email, normalized_email.split("@")[0], "otp"),
        )
        conn.commit()
        user_row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()

    conn.close()
    return serialize_user(user_row)


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
