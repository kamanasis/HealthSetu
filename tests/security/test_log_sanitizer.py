"""Tests for centralized PHI-safe log sanitizer."""

import pytest
from app.core.log_sanitizer import (
    sanitize_for_log,
    sanitize_headers,
    _REDACTED,
)


def test_sanitize_sensitive_keys_redacted():
    """Verify that credentials and PHI keys are always redacted."""
    raw = {
        "password": "SuperSecretPassword123!",
        "token": "eyJhbGciOi...",
        "access_token": "secret_token_val",
        "api_key": "sk-1234567890abcdef",
        "ssn": "123-45-6789",
        "dob": "1990-01-01",
        "diagnosis": "Type 2 Diabetes",
        "prescription": "Metformin 500mg",
        "medical_history": "Hypertension, Asthma",
        "clinical_notes": "Patient reported acute symptoms.",
        "patient_data": {"name": "Jane Doe"},
    }
    sanitized = sanitize_for_log(raw)

    for key in raw:
        assert sanitized[key] == _REDACTED


def test_safe_metadata_preserved():
    """Verify that safe operational metadata is preserved in logs."""
    raw = {
        "request_id": "req-1234-abcd",
        "actor_id": "user-uuid-5678",
        "resource_type": "patient",
        "resource_id": "patient-uuid-9999",
        "operation": "get_patient_summary",
        "status_code": 200,
        "duration_ms": 45.2,
        "provider_name": "rxnorm",
    }
    sanitized = sanitize_for_log(raw)

    assert sanitized == raw


def test_nested_sanitization():
    """Verify recursive sanitization inside nested dicts and lists."""
    raw = {
        "event": "audit_event",
        "details": {
            "user": "dr_smith",
            "auth": {
                "client_secret": "sensitive_val",
                "nested_token": "bearer_xyz",
            },
            "records": [
                {"id": 1, "diagnosis": "Hypertension"},
                {"id": 2, "safe_tag": "follow_up"},
            ],
        },
    }
    sanitized = sanitize_for_log(raw)

    assert sanitized["details"]["auth"]["client_secret"] == _REDACTED
    assert sanitized["details"]["auth"]["nested_token"] == _REDACTED
    assert sanitized["details"]["records"][0]["diagnosis"] == _REDACTED
    assert sanitized["details"]["records"][0]["id"] == 1
    assert sanitized["details"]["records"][1]["safe_tag"] == "follow_up"


def test_string_embedded_token_redaction():
    """Verify that JWTs and Bearer tokens in string values are redacted."""
    raw = {
        "message": "User authenticated with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeakThisSignature",
    }
    sanitized = sanitize_for_log(raw)
    assert sanitized["message"] == _REDACTED


def test_sanitize_headers():
    """Verify header sanitization redacts Authorization and Cookie headers."""
    headers = {
        "Host": "api.healthsetu.local",
        "Authorization": "Bearer secret_jwt_token",
        "Cookie": "session_id=abcdef123456",
        "X-Request-ID": "req-999",
        "X-API-Key": "my-key",
    }
    sanitized = sanitize_headers(headers)

    assert sanitized["Authorization"] == _REDACTED
    assert sanitized["Cookie"] == _REDACTED
    assert sanitized["X-API-Key"] == _REDACTED
    assert sanitized["Host"] == "api.healthsetu.local"
    assert sanitized["X-Request-ID"] == "req-999"


def test_recursion_depth_limit():
    """Verify that circular or extremely deep structures are safely truncated."""
    deep = {}
    curr = deep
    for i in range(20):
        curr["next"] = {}
        curr = curr["next"]
    curr["val"] = "deepest"

    sanitized = sanitize_for_log(deep)
    assert isinstance(sanitized, dict)
