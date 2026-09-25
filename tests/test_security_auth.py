"""Dedicated security assertions and vulnerability mitigation tests for Phase 2."""

from datetime import datetime, timedelta, timezone
from httpx import AsyncClient
import pytest

from app.api.deps import _global_session_repo, _global_user_repo
from app.core.config import get_settings
from app.core.security import create_access_token, decode_access_token, hash_token
from tests.conftest import TEST_PASSWORD


@pytest.mark.asyncio
async def test_plaintext_password_never_stored_in_repository(seeded_users):
    """Verify that stored user credentials contain only Argon2id hashes, never plaintext."""
    user = await _global_user_repo.get_by_identifier("patient@healthsetu.org")
    assert user is not None
    assert user.password_hash != TEST_PASSWORD
    assert user.password_hash.startswith("$argon2id$")


@pytest.mark.asyncio
async def test_token_reuse_attack_revokes_all_user_sessions(
    async_client: AsyncClient, seeded_users
):
    """When a revoked/rotated refresh token is presented again (indicating token theft),

    all active sessions for that user must be terminated immediately.
    """
    # 1. Login
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "patient@healthsetu.org", "password": TEST_PASSWORD},
    )
    initial_refresh = login_res.json()["data"]["refresh_token"]

    # 2. Legitimate rotation (creates second refresh token)
    rotate_res = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": initial_refresh},
    )
    assert rotate_res.status_code == 200
    active_refresh = rotate_res.json()["data"]["refresh_token"]

    # 3. Attacker tries to use the old (compromised) refresh token
    attack_res = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": initial_refresh},
    )
    assert attack_res.status_code == 401

    # 4. As a result of token reuse detection, even the legitimate active session must now be revoked
    check_active_res = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": active_refresh},
    )
    assert check_active_res.status_code == 401
    assert check_active_res.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_authorization_header_and_tokens_not_in_access_logs(
    async_client: AsyncClient, seeded_users, caplog
):
    """Verify that neither access tokens nor Bearer Authorization headers appear in logs."""
    import logging

    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "doctor@healthsetu.org", "password": TEST_PASSWORD},
    )
    token = login_res.json()["data"]["access_token"]
    refresh = login_res.json()["data"]["refresh_token"]

    with caplog.at_level(logging.INFO):
        await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    log_content = caplog.text
    assert token not in log_content
    assert refresh not in log_content
    assert "Bearer " not in log_content


@pytest.mark.asyncio
async def test_signing_secret_not_exposed_in_error_or_debug(async_client: AsyncClient):
    """Ensure JWT_SECRET_KEY is never exposed in responses or error messages."""
    settings = get_settings()
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.signature.token"},
    )
    assert settings.JWT_SECRET_KEY not in response.text
