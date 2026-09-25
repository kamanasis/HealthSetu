"""Tests for centralized global error handling."""

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
import pytest

from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ServiceUnavailableException,
    UnauthorizedException,
)
from app.main import create_app


@pytest.fixture
def error_test_app() -> FastAPI:
    """App configured with mock routes to trigger each category of exception."""
    test_app = create_app()

    @test_app.get("/test-not-found")
    async def trigger_not_found():
        raise NotFoundException("Custom resource not found.")

    @test_app.get("/test-unauthorized")
    async def trigger_unauthorized():
        raise UnauthorizedException("Authentication token expired.")

    @test_app.get("/test-forbidden")
    async def trigger_forbidden():
        raise ForbiddenException("Action not permitted.")

    @test_app.get("/test-conflict")
    async def trigger_conflict():
        raise ConflictException("Resource conflict exists.")

    @test_app.get("/test-service-unavailable")
    async def trigger_service_unavailable():
        raise ServiceUnavailableException("External service down.")

    @test_app.get("/test-unhandled-exception")
    async def trigger_unhandled():
        raise RuntimeError("Unexpected internal crash!")

    from pydantic import BaseModel, Field

    class SamplePayload(BaseModel):
        name: str = Field(min_length=3)
        count: int

    @test_app.post("/test-validation")
    async def trigger_validation(payload: SamplePayload):
        return {"received": payload.name}

    return test_app


@pytest.mark.asyncio
async def test_route_not_found(async_client: AsyncClient):
    """Test 404 for non-existent route uses standardized error structure."""
    response = await async_client.get("/non-existent-endpoint")
    assert response.status_code == 404

    data = response.json()
    assert data["success"] is False
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert "request_id" in data["error"]
    assert response.headers.get("X-Request-ID") == data["error"]["request_id"]


@pytest.mark.asyncio
async def test_custom_not_found_exception(error_test_app: FastAPI):
    """Test NotFoundException returns standardized 404 envelope."""
    async with AsyncClient(
        transport=ASGITransport(app=error_test_app), base_url="http://test"
    ) as client:
        response = await client.get("/test-not-found")
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "NOT_FOUND"
        assert data["error"]["message"] == "Custom resource not found."


@pytest.mark.asyncio
async def test_unauthorized_exception(error_test_app: FastAPI):
    """Test UnauthorizedException returns standardized 401 envelope."""
    async with AsyncClient(
        transport=ASGITransport(app=error_test_app), base_url="http://test"
    ) as client:
        response = await client.get("/test-unauthorized")
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "UNAUTHORIZED"
        assert data["error"]["message"] == "Authentication token expired."


@pytest.mark.asyncio
async def test_forbidden_exception(error_test_app: FastAPI):
    """Test ForbiddenException returns standardized 403 envelope."""
    async with AsyncClient(
        transport=ASGITransport(app=error_test_app), base_url="http://test"
    ) as client:
        response = await client.get("/test-forbidden")
        assert response.status_code == 403
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_conflict_exception(error_test_app: FastAPI):
    """Test ConflictException returns standardized 409 envelope."""
    async with AsyncClient(
        transport=ASGITransport(app=error_test_app), base_url="http://test"
    ) as client:
        response = await client.get("/test-conflict")
        assert response.status_code == 409
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "CONFLICT"


@pytest.mark.asyncio
async def test_service_unavailable_exception(error_test_app: FastAPI):
    """Test ServiceUnavailableException returns standardized 503 envelope."""
    async with AsyncClient(
        transport=ASGITransport(app=error_test_app), base_url="http://test"
    ) as client:
        response = await client.get("/test-service-unavailable")
        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "SERVICE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_unhandled_exception_does_not_leak_stack_trace(error_test_app: FastAPI):
    """Unhandled exceptions must return 500 without leaking stack traces or internal details."""
    async with AsyncClient(
        transport=ASGITransport(app=error_test_app), base_url="http://test"
    ) as client:
        response = await client.get("/test-unhandled-exception")
        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "INTERNAL_ERROR"
        assert data["error"]["message"] == "An unexpected error occurred."
        # Confirm stack trace is not in response
        assert "Traceback" not in response.text
        assert "Unexpected internal crash!" not in response.text


@pytest.mark.asyncio
async def test_validation_error_format(error_test_app: FastAPI):
    """Test 422 validation error produces standard error envelope with field details."""
    async with AsyncClient(
        transport=ASGITransport(app=error_test_app), base_url="http://test"
    ) as client:
        # Send bad payload (name too short, count not an int)
        response = await client.post("/test-validation", json={"name": "a", "count": "not-a-number"})
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "details" in data["error"]
        assert len(data["error"]["details"]) > 0


@pytest.mark.asyncio
async def test_payload_size_limit(error_test_app: FastAPI):
    """Test payload exceeding MAX_REQUEST_SIZE_BYTES returns 413."""
    async with AsyncClient(
        transport=ASGITransport(app=error_test_app), base_url="http://test"
    ) as client:
        # Send headers with oversized Content-Length
        response = await client.post(
            "/test-validation",
            content=b"test",
            headers={"Content-Length": "20000000"},  # 20MB > 10MB limit
        )
        assert response.status_code == 413
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "exceeds limit" in data["error"]["message"]

