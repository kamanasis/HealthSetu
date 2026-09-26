"""Tests for authentication and token security."""

from datetime import timedelta
import jwt
import pytest
from app.core.config import get_settings
from app.core.exceptions import UnauthorizedException
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_secure_token,
    hash_password,
    hash_token,
    verify_password,
)


def test_password_hashing_and_verification():
    """Verify Argon2id password hashing and verification."""
    password = "CorrectHorseBatteryStaple2026!"
    hashed = hash_password(password)

    assert hashed.startswith("$argon2id$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword123", hashed) is False


def test_token_claims_contain_no_phi():
    """Verify that generated JWT tokens contain NO clinical or sensitive patient data."""
    token, _ = create_access_token(user_id="user-12345", role="clinician")
    payload = decode_access_token(token)

    # Allowed identity claims
    assert payload["sub"] == "user-12345"
    assert payload["role"] == "clinician"
    assert payload["type"] == "access"
    assert "iat" in payload
    assert "exp" in payload
    assert "jti" in payload

    # Explicitly verify NO clinical keys exist in payload
    forbidden_keys = {
        "diagnosis", "prescription", "patient_name", "mrn", "notes",
        "ssn", "dob", "medical_history", "allergies", "medications",
    }
    assert forbidden_keys.isdisjoint(payload.keys())


def test_expired_token_rejected():
    """Verify that an expired token raises UnauthorizedException."""
    token, _ = create_access_token(
        user_id="user-123",
        role="doctor",
        expires_delta=timedelta(seconds=-10),  # expired 10 seconds ago
    )
    with pytest.raises(UnauthorizedException, match="expired"):
        decode_access_token(token)


def test_tampered_token_rejected():
    """Verify that a tampered JWT payload/signature raises UnauthorizedException."""
    token, _ = create_access_token(user_id="user-123", role="doctor")
    # Alter the last character of the signature
    tampered = token[:-2] + ("x" if token[-2] != "x" else "y") + token[-1]

    with pytest.raises(UnauthorizedException):
        decode_access_token(tampered)


def test_mismatched_token_type_rejected():
    """Verify that a token with non-access type is rejected."""
    settings = get_settings()
    import time
    now = int(time.time())
    payload = {
        "sub": "user-123",
        "role": "doctor",
        "type": "refresh",  # not 'access'
        "iat": now,
        "exp": now + 3600,
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    with pytest.raises(UnauthorizedException, match="Invalid token type"):
        decode_access_token(token)


def test_secure_random_token_and_sha256_hash():
    """Verify token generation entropy and SHA-256 hashing."""
    token1 = generate_secure_token(32)
    token2 = generate_secure_token(32)
    assert token1 != token2
    assert len(token1) >= 32

    hash1 = hash_token(token1)
    assert len(hash1) == 64  # Hex SHA-256 length
    assert hash_token(token1) == hash1
