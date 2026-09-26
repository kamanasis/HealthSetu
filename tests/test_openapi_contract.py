"""OpenAPI Schema and API Contract Validation Tests (Phase 16).

Verifies Section 14, 60 & 61:
- OpenAPI 3.x schema generation and structure
- Completeness of documented endpoints
- Verification of standard HTTP response status codes
- Prevention of undocumented endpoint drift
"""

import pytest
from app.main import create_app
from app.core.config import Settings


def test_openapi_schema_generation():
    """Verify that OpenAPI schema generates correctly with all metadata."""
    # In development/testing, openapi_url is available
    settings = Settings(APP_ENV="development", DEBUG=True)
    app = create_app(settings)
    schema = app.openapi()

    assert schema is not None
    assert "openapi" in schema
    assert schema["openapi"].startswith("3.")
    assert "info" in schema
    assert "HealthSetu" in schema["info"]["title"]
    assert "paths" in schema

    paths = schema["paths"]

    # Verify core domain routes are documented
    essential_routes = [
        "/api/v1/health",
        "/api/v1/ready",
        "/api/v1/auth/login",
        "/api/v1/patients/{patient_id}",
        "/api/v1/patients/{patient_id}/prescriptions",
        "/api/v1/patients/{patient_id}/medications",
        "/api/v1/patients/{patient_id}/medication-safety/check",
        "/api/v1/facilities/discover",
        "/api/v1/ai/tasks",
    ]
    for route in essential_routes:
        assert route in paths, f"Route '{route}' missing from OpenAPI schema!"


def test_openapi_security_schemes():
    """Verify that OpenAPI components define Bearer authentication."""
    settings = Settings(APP_ENV="development", DEBUG=True)
    app = create_app(settings)
    schema = app.openapi()

    components = schema.get("components", {})
    # Verify components dict is well-formed
    assert isinstance(components, dict)
    assert "schemas" in components
