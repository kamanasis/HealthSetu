"""Comprehensive test suite for Phase 2 Identity and Authentication."""

from datetime import datetime, timedelta, timezone
from httpx import AsyncClient
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
from app.schemas.auth import UserRole
from tests.conftest import TEST_PASSWORD


# 1. Successful Login
@pytest.mark.asyncio
async def test_successful_login(async_client: AsyncClient, seeded_users):
    """Test successful login returns access_token, refresh_token, and user summary."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "patient@healthsetu.org", "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]
    assert data["data"]["token_type"] == "bearer"
    assert data["data"]["expires_in"] == 900
    assert data["data"]["user"]["id"] == "usr-patient-001"
    assert data["data"]["user"]["role"] == "PATIENT"
    assert "request_id" in data


# 2. Invalid Password
@pytest.mark.asyncio
async def test_login_invalid_password(async_client: AsyncClient, seeded_users):
    """Test login with incorrect password returns 401 generic error."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "patient@healthsetu.org", "password": "WrongPassword123!"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert data["error"]["message"] == "Invalid credentials."


# 3. Unknown Identifier
@pytest.mark.asyncio
async def test_login_unknown_identifier(async_client: AsyncClient, seeded_users):
    """Test login with non-existent user returns identical 401 generic error."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "nonexistent@healthsetu.org", "password": TEST_PASSWORD},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert data["error"]["message"] == "Invalid credentials."


# 4. Disabled Account
@pytest.mark.asyncio
async def test_login_disabled_account(async_client: AsyncClient, seeded_users):
    """Test login with disabled account is rejected with generic error."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "disabled@healthsetu.org", "password": TEST_PASSWORD},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert data["error"]["message"] == "Invalid credentials."


# 5. Locked Account
@pytest.mark.asyncio
async def test_login_locked_account(async_client: AsyncClient, seeded_users):
    """Test login with locked account is rejected with generic error."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "locked@healthsetu.org", "password": TEST_PASSWORD},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert data["error"]["message"] == "Invalid credentials."


# 6. Expired Access Token
@pytest.mark.asyncio
async def test_expired_access_token_rejected(async_client: AsyncClient, seeded_users):
    """Test that an expired JWT access token is rejected on protected endpoints."""
    # Create token expired 1 hour ago
    expired_token, _ = create_access_token(
        user_id="usr-patient-001",
        role="PATIENT",
        expires_delta=timedelta(hours=-1),
    )
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert "expired" in data["error"]["message"].lower()


# 7. Malformed Access Token
@pytest.mark.asyncio
async def test_malformed_access_token_rejected(async_client: AsyncClient):
    """Test that a malformed JWT token string is rejected."""
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer this-is-not-a-valid-jwt-token"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHORIZED"


# 8. Missing Authorization Header
@pytest.mark.asyncio
async def test_missing_auth_header(async_client: AsyncClient):
    """Test accessing protected /auth/me without header returns 401."""
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHORIZED"


# 9. Wrong Authorization Scheme
@pytest.mark.asyncio
async def test_wrong_auth_scheme(async_client: AsyncClient):
    """Test using Basic auth scheme instead of Bearer returns 401."""
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Basic dXNlcjpwYXNz"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHORIZED"


# 10. Successful /auth/me
@pytest.mark.asyncio
async def test_successful_get_me(async_client: AsyncClient, seeded_users):
    """Test authenticated caller can retrieve their identity context."""
    # First login to obtain token
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "doctor@healthsetu.org", "password": TEST_PASSWORD},
    )
    token = login_res.json()["data"]["access_token"]

    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] == "usr-doctor-001"
    assert data["data"]["role"] == "DOCTOR"
    assert data["data"]["status"] == "ACTIVE"


# 11. Unauthenticated /auth/me
@pytest.mark.asyncio
async def test_unauthenticated_get_me(async_client: AsyncClient):
    """Test unauthenticated call to /auth/me returns 401."""
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401


# 12. Valid Refresh Token
@pytest.mark.asyncio
async def test_valid_refresh_token(async_client: AsyncClient, seeded_users):
    """Test exchanging a valid refresh token yields new tokens."""
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "patient@healthsetu.org", "password": TEST_PASSWORD},
    )
    refresh_token = login_res.json()["data"]["refresh_token"]

    refresh_res = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    data = refresh_res.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]


# 13. Expired Refresh Token
@pytest.mark.asyncio
async def test_expired_refresh_token(async_client: AsyncClient, seeded_users):
    """Test that an expired refresh token session is rejected."""
    from app.api.deps import _global_session_repo

    raw_token = generate_secure_token(32)
    # Persist session with expired timestamp
    await _global_session_repo.create_session(
        user_id="usr-patient-001",
        token_hash=hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )

    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": raw_token},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHORIZED"


# 14. Revoked Refresh Token
@pytest.mark.asyncio
async def test_revoked_refresh_token(async_client: AsyncClient, seeded_users):
    """Test that a revoked refresh token is rejected."""
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "patient@healthsetu.org", "password": TEST_PASSWORD},
    )
    refresh_token = login_res.json()["data"]["refresh_token"]

    # Explicitly logout to revoke the token
    await async_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )

    # Attempt to refresh with now-revoked token
    refresh_res = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 401
    assert refresh_res.json()["error"]["code"] == "UNAUTHORIZED"


# 15. Refresh Token Rotation
@pytest.mark.asyncio
async def test_refresh_token_rotation(async_client: AsyncClient, seeded_users):
    """Test that refreshing rotates the token and invalidates the old one."""
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "patient@healthsetu.org", "password": TEST_PASSWORD},
    )
    old_refresh = login_res.json()["data"]["refresh_token"]

    # First refresh
    res1 = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert res1.status_code == 200
    new_refresh = res1.json()["data"]["refresh_token"]
    assert new_refresh != old_refresh

    # Attempting to use the OLD refresh token must fail (it is now revoked/rotated)
    res2 = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert res2.status_code == 401


# 16. Logout
@pytest.mark.asyncio
async def test_logout(async_client: AsyncClient, seeded_users):
    """Test logout revokes the refresh session."""
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "patient@healthsetu.org", "password": TEST_PASSWORD},
    )
    refresh_token = login_res.json()["data"]["refresh_token"]

    logout_res = await async_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout_res.status_code == 200
    assert logout_res.json()["data"]["message"] == "Logged out successfully."


# 17. Repeated Logout (Idempotence)
@pytest.mark.asyncio
async def test_repeated_logout_is_idempotent(async_client: AsyncClient, seeded_users):
    """Logging out multiple times with the same token must remain successful and idempotent."""
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "patient@healthsetu.org", "password": TEST_PASSWORD},
    )
    refresh_token = login_res.json()["data"]["refresh_token"]

    res1 = await async_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert res1.status_code == 200

    # Repeat logout with same token
    res2 = await async_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert res2.status_code == 200


# 18. Password Hashing
def test_password_hashing_uses_argon2id():
    """Verify password hashing produces a valid Argon2id hash."""
    pwd = "UniqueTestPassword!123"
    hashed = hash_password(pwd)
    assert hashed.startswith("$argon2id$")
    assert len(hashed) > 50


# 19. Password Verification
def test_password_verification():
    """Verify password check works accurately and rejects wrong passwords."""
    pwd = "MySecretPassword#456"
    hashed = hash_password(pwd)
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword#456", hashed) is False


# 20. Token Does Not Contain PHI
def test_jwt_claims_do_not_contain_phi():
    """Ensure access tokens contain zero protected healthcare or clinical attributes."""
    token, _ = create_access_token(user_id="usr-123", role="PATIENT")
    decoded = decode_access_token(token)

    phi_keywords = [
        "diagnosis",
        "prescription",
        "medication",
        "symptoms",
        "clinical",
        "phi",
        "medical_record",
        "allergies",
    ]
    for key in phi_keywords:
        assert key not in decoded


# 21. Secrets Are Not Returned
@pytest.mark.asyncio
async def test_secrets_and_password_hashes_not_returned(
    async_client: AsyncClient, seeded_users
):
    """Verify password hash, secrets, and raw refresh hashes are never in HTTP response."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "patient@healthsetu.org", "password": TEST_PASSWORD},
    )
    text = response.text.lower()
    assert "argon2" not in text
    assert "secret" not in text
    assert "password_hash" not in text


# 22. Authentication Errors Use Correct Format
@pytest.mark.asyncio
async def test_auth_error_format_consistency(async_client: AsyncClient):
    """Verify authentication errors follow standard HealthSetu envelope."""
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert "error" in data
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert "message" in data["error"]
    assert "request_id" in data["error"]


# 23. Authentication Failures Do Not Leak Account Existence
@pytest.mark.asyncio
async def test_auth_failures_do_not_leak_account_existence(
    async_client: AsyncClient, seeded_users
):
    """Verify nonexistent user, wrong password, and locked account produce identical responses."""
    res_unknown = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "unknown@healthsetu.org", "password": TEST_PASSWORD},
    )
    res_wrong_pwd = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "patient@healthsetu.org", "password": "WrongPassword!123"},
    )
    res_locked = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "locked@healthsetu.org", "password": TEST_PASSWORD},
    )

    assert res_unknown.status_code == res_wrong_pwd.status_code == res_locked.status_code == 401
    assert (
        res_unknown.json()["error"]["message"]
        == res_wrong_pwd.json()["error"]["message"]
        == res_locked.json()["error"]["message"]
        == "Invalid credentials."
    )


# 24. Request ID Continues Working
@pytest.mark.asyncio
async def test_request_id_in_auth_endpoints(async_client: AsyncClient, seeded_users):
    """Verify correlation ID is maintained across authentication endpoints."""
    custom_id = "test-auth-corr-id-12345"
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "patient@healthsetu.org", "password": TEST_PASSWORD},
        headers={"X-Request-ID": custom_id},
    )
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id
    assert response.json()["request_id"] == custom_id


# 25. Authentication Events Do Not Leak Credentials Into Logs
@pytest.mark.asyncio
async def test_logs_do_not_leak_credentials(
    async_client: AsyncClient, seeded_users, caplog
):
    """Verify security event logging does not leak passwords or raw tokens."""
    import logging

    with caplog.at_level(logging.INFO):
        await async_client.post(
            "/api/v1/auth/login",
            json={"identifier": "patient@healthsetu.org", "password": TEST_PASSWORD},
        )
    log_text = caplog.text
    assert TEST_PASSWORD not in log_text
    assert "Bearer " not in log_text
