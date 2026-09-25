"""Tests for Request ID / correlation ID middleware."""

import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_request_id_generated_when_missing(async_client: AsyncClient):
    """If no request ID is provided, the middleware generates a valid UUID."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200

    request_id = response.headers.get("X-Request-ID")
    assert request_id is not None
    # Verify it is a valid UUID
    parsed_uuid = uuid.UUID(request_id)
    assert str(parsed_uuid) == request_id


@pytest.mark.asyncio
async def test_request_id_preserved_when_valid(async_client: AsyncClient):
    """If client sends a valid request ID, it must be preserved."""
    client_id = "test-correlation-id-98765"
    response = await async_client.get(
        "/api/v1/health",
        headers={"X-Request-ID": client_id},
    )
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == client_id


@pytest.mark.asyncio
async def test_request_id_regenerated_when_malformed(async_client: AsyncClient):
    """If client sends an invalid request ID (e.g. with illegal characters or too short), generate a fresh one."""
    malformed_id = "bad!id$"
    response = await async_client.get(
        "/api/v1/health",
        headers={"X-Request-ID": malformed_id},
    )
    assert response.status_code == 200
    returned_id = response.headers.get("X-Request-ID")
    assert returned_id != malformed_id
    assert uuid.UUID(returned_id)
