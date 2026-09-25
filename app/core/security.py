"""Security utilities, cryptographic routines, and token management for HealthSetu."""

from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Any
import uuid
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
import jwt

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedException

# Password Hasher using Argon2id with recommended OWASP baseline parameters
_ph = PasswordHasher(
    time_cost=2,
    memory_cost=65536,  # 64 MB
    parallelism=1,
    hash_len=32,
)

# Baseline secure headers configuration
SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=()",
}


def hash_password(password: str) -> str:
    """Hash password using Argon2id."""
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against Argon2id hash. Never raises, returns bool."""
    try:
        return _ph.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, Exception):
        return False


def generate_secure_token(length_bytes: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length_bytes)


def hash_token(raw_token: str) -> str:
    """Hash a token (such as a refresh token) with SHA-256 for secure persistence."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_access_token(
    user_id: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> tuple[str, int]:
    """Create short-lived JWT access token with minimal identity claims.

    CRITICAL HEALTHCARE PRIVACY RULE:
    Tokens MUST NOT contain clinical data, diagnoses, prescriptions, or PHI.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)

    if expires_delta is not None:
        expire = now + expires_delta
        expires_in = int(expires_delta.total_seconds())
    else:
        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        expire = now + timedelta(seconds=expires_in)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": str(role),
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": str(uuid.uuid4()),
    }

    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expires_in


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "exp", "type"]},
        )

        if payload.get("type") != "access":
            raise UnauthorizedException("Invalid token type.")

        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("Token has expired.")
    except (jwt.PyJWTError, Exception):
        raise UnauthorizedException("Could not validate credentials.")


def is_origin_allowed(origin: str, allowed_origins: list[str]) -> bool:
    """Validate whether an incoming origin is in the allowed list."""
    if not origin:
        return False
    clean_origin = origin.strip().rstrip("/")
    return clean_origin in allowed_origins or "*" in allowed_origins
