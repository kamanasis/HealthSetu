"""Tests for CORS configuration and security headers."""

from httpx import AsyncClient
import pytest


@pytest.mark.asyncio
async def test_cors_allowed_origin(async_client: AsyncClient):
    """Requests from configured origin must include CORS headers."""
    response = await async_client.get(
        "/api/v1/health",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "X-Request-ID" in response.headers.get("access-control-expose-headers", "")


@pytest.mark.asyncio
async def test_cors_disallowed_origin(async_client: AsyncClient):
    """Requests from unapproved origins must not receive allow-origin header."""
    response = await async_client.get(
        "/api/v1/health",
        headers={"Origin": "http://malicious-site.example.com"},
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.asyncio
async def test_security_headers_present(async_client: AsyncClient):
    """Responses must include baseline security headers."""
    response = await async_client.get("/api/v1/health")
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert "referrer-policy" in response.headers
