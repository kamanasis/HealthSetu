"""Pytest configuration, fixtures, and test testbed."""

import os
from collections.abc import AsyncGenerator
import pytest
from httpx import ASGITransport, AsyncClient

# Set testing environment variable before importing app
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = ""

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture(autouse=True)
def clean_settings():
    """Ensure settings cache is fresh for tests."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def app():
    """Create test application instance."""
    return create_app()


@pytest.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP test client using ASGITransport."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client
