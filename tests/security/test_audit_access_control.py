"""Tests for audit service access control and PHI metadata sanitization."""

import pytest
from app.core.policies import Permission, role_has_permission
from app.services.audit_service import _sanitize_metadata, _FORBIDDEN_METADATA_KEYS


def test_audit_metadata_sanitizes_phi_and_secrets():
    """Verify that forbidden PHI and secret keys are stripped from audit metadata."""
    raw_metadata = {
        "ip_address": "203.0.113.195",
        "user_agent": "Mozilla/5.0",
        "action": "export_pdf",
        "password": "my_password",
        "token": "secret_token",
        "diagnosis": "Cardiomegaly",
        "prescription": "Lisinopril 10mg",
        "symptoms": "Dizziness, blurred vision",
    }
    sanitized = _sanitize_metadata(raw_metadata)
    assert sanitized is not None

    # Safe technical metadata preserved
    assert sanitized["ip_address"] == "203.0.113.195"
    assert sanitized["user_agent"] == "Mozilla/5.0"
    assert sanitized["action"] == "export_pdf"

    # Forbidden fields completely excluded
    for forbidden in _FORBIDDEN_METADATA_KEYS:
        assert forbidden not in sanitized


def test_only_admin_can_read_audit_logs():
    """Verify that only the ADMIN role possesses Permission.ADMIN_AUDIT_READ."""
    assert role_has_permission("ADMIN", Permission.ADMIN_AUDIT_READ) is True
    assert role_has_permission("DOCTOR", Permission.ADMIN_AUDIT_READ) is False
    assert role_has_permission("PATIENT", Permission.ADMIN_AUDIT_READ) is False
    assert role_has_permission("CLINICIAN", Permission.ADMIN_AUDIT_READ) is False
