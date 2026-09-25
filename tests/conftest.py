"""Pytest configuration, fixtures, and test testbed."""

from collections.abc import AsyncGenerator
import os
import pytest
from httpx import ASGITransport, AsyncClient

# Set testing environment variable before importing app
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = ""

from app.api.deps import (
    _global_audit_repo,
    _global_consent_repo,
    _global_permission_repo,
    _global_session_repo,
    _global_user_repo,
)
from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.main import create_app
from app.repositories.user_repository import UserRecord
from app.schemas.auth import AccountStatus, UserRole

TEST_PASSWORD = "StrongP@ssw0rd123!"


@pytest.fixture(autouse=True)
def clean_state():
    """Ensure settings cache and all repositories are fresh for each test."""
    get_settings.cache_clear()
    # Phase 1/2
    _global_user_repo._local_users.clear()
    _global_session_repo._sessions_by_id.clear()
    _global_session_repo._sessions_by_hash.clear()
    # Phase 3
    _global_consent_repo._consents.clear()
    _global_audit_repo._events.clear()
    yield
    get_settings.cache_clear()
    _global_user_repo._local_users.clear()
    _global_session_repo._sessions_by_id.clear()
    _global_session_repo._sessions_by_hash.clear()
    _global_consent_repo._consents.clear()
    _global_audit_repo._events.clear()


@pytest.fixture
def seeded_users() -> dict[str, UserRecord]:
    """Seed test users into the user repository with different roles and statuses."""
    hashed_pwd = hash_password(TEST_PASSWORD)

    users = {
        "patient": UserRecord(
            id="usr-patient-001",
            identifier="patient@healthsetu.org",
            password_hash=hashed_pwd,
            role=UserRole.PATIENT,
            status=AccountStatus.ACTIVE,
        ),
        "patient2": UserRecord(
            id="usr-patient-002",
            identifier="patient2@healthsetu.org",
            password_hash=hashed_pwd,
            role=UserRole.PATIENT,
            status=AccountStatus.ACTIVE,
        ),
        "doctor": UserRecord(
            id="usr-doctor-001",
            identifier="doctor@healthsetu.org",
            password_hash=hashed_pwd,
            role=UserRole.DOCTOR,
            status=AccountStatus.ACTIVE,
        ),
        "admin": UserRecord(
            id="usr-admin-001",
            identifier="admin@healthsetu.org",
            password_hash=hashed_pwd,
            role=UserRole.ADMIN,
            status=AccountStatus.ACTIVE,
        ),
        "disabled": UserRecord(
            id="usr-disabled-001",
            identifier="disabled@healthsetu.org",
            password_hash=hashed_pwd,
            role=UserRole.PATIENT,
            status=AccountStatus.DISABLED,
        ),
        "locked": UserRecord(
            id="usr-locked-001",
            identifier="locked@healthsetu.org",
            password_hash=hashed_pwd,
            role=UserRole.PATIENT,
            status=AccountStatus.LOCKED,
        ),
        "pending": UserRecord(
            id="usr-pending-001",
            identifier="pending@healthsetu.org",
            password_hash=hashed_pwd,
            role=UserRole.PATIENT,
            status=AccountStatus.PENDING,
        ),
    }

    for user in users.values():
        _global_user_repo.register_in_memory_user(user)

    return users


@pytest.fixture
def make_token():
    """Factory fixture: create a valid access token for a given user."""
    def _make(user_id: str, role: str) -> str:
        token, _ = create_access_token(user_id, role)
        return token
    return _make


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
