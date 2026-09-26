"""Tests for authorization policies, IDOR protection, and role separation."""

import pytest
from app.core.policies import (
    Permission,
    get_required_permission,
    get_role_permissions,
    role_has_permission,
)


def test_deny_by_default_for_unknown_role():
    """Verify that an unknown or invalid role has zero permissions."""
    perms = get_role_permissions("ATTACKER_ROLE")
    assert perms == frozenset()
    assert role_has_permission("ATTACKER_ROLE", Permission.PATIENT_READ_SELF) is False
    assert role_has_permission("ATTACKER_ROLE", Permission.CLINICAL_RECORD_READ) is False


def test_admin_cannot_access_clinical_records():
    """Verify separation of duty: ADMIN role does NOT have clinical read/create access."""
    assert role_has_permission("ADMIN", Permission.CLINICAL_RECORD_READ) is False
    assert role_has_permission("ADMIN", Permission.PRESCRIPTION_CREATE) is False
    assert role_has_permission("ADMIN", Permission.CLINICAL_NOTE_READ) is False

    # But ADMIN does have administrative permissions
    assert role_has_permission("ADMIN", Permission.ADMIN_USER_MANAGE) is True
    assert role_has_permission("ADMIN", Permission.ADMIN_AUDIT_READ) is True


def test_patient_cannot_perform_admin_tasks():
    """Verify that PATIENT role cannot manage users or inspect audit logs."""
    assert role_has_permission("PATIENT", Permission.ADMIN_USER_MANAGE) is False
    assert role_has_permission("PATIENT", Permission.ADMIN_AUDIT_READ) is False
    assert role_has_permission("PATIENT", Permission.PATIENT_READ_SELF) is True


def test_doctor_cannot_perform_admin_tasks():
    """Verify that DOCTOR role cannot manage users or inspect audit logs."""
    assert role_has_permission("DOCTOR", Permission.ADMIN_USER_MANAGE) is False
    assert role_has_permission("DOCTOR", Permission.ADMIN_AUDIT_READ) is False
    assert role_has_permission("DOCTOR", Permission.CLINICAL_RECORD_READ) is True


def test_unregistered_action_denied():
    """Verify that unregistered (resource, action) mappings return None (fail closed)."""
    assert get_required_permission("unknown_resource", "delete") is None
    assert get_required_permission("patient", "drop_table") is None
