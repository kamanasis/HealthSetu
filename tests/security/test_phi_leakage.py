"""Tests verifying zero PHI leakage across error responses, logs, and security events."""

from app.core.exceptions import build_error_response
from app.core.log_sanitizer import sanitize_for_log, _REDACTED
from app.services.security_event_service import SecurityEventService, SecurityEventType


def test_error_response_contains_no_phi():
    """Verify that build_error_response produces clean responses with standard error envelope."""
    resp = build_error_response(
        status_code=400,
        code="INVALID_INPUT",
        message="Invalid request parameter.",
        request_id="req-12345",
    )
    import json
    data = json.loads(resp.body)

    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_INPUT"
    assert data["error"]["message"] == "Invalid request parameter."
    assert data["error"]["request_id"] == "req-12345"
    assert "diagnosis" not in data["error"]
    assert "prescription" not in data["error"]


def test_security_event_contains_no_phi():
    """Verify that security events do not include clinical notes or diagnoses."""
    service = SecurityEventService()
    event = service.emit(
        SecurityEventType.AUTHZ_PATIENT_ACCESS_DENIED,
        actor_id="user-123",
        resource_type="patient",
        resource_id="patient-999",
        reason="Actor does not have an active encounter with this patient.",
    )
    event_dict = event

    assert event_dict["event_type"] == "AUTHZ_PATIENT_ACCESS_DENIED"
    assert event_dict["resource_id"] == "patient-999"
    # Ensure no PHI fields exist
    for forbidden in ("diagnosis", "prescription", "notes", "medical_history", "ssn"):
        assert forbidden not in event_dict


def test_phi_in_nested_error_payload_sanitized():
    """Verify that log sanitizer redacts PHI when logging request/response payloads."""
    payload = {
        "patient_id": "p-123",
        "diagnosis": "Severe acute respiratory syndrome",
        "prescription": "Amoxicillin 500mg PO TID",
        "notes": "Patient reports severe chest pain.",
    }
    sanitized = sanitize_for_log(payload)

    assert sanitized["diagnosis"] == _REDACTED
    assert sanitized["prescription"] == _REDACTED
    assert sanitized["notes"] == _REDACTED
    assert sanitized["patient_id"] == "p-123"
