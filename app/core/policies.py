"""Centralized policy registry for HealthSetu authorization.

DATABASE TEAM DEPENDENCY — PHASE 3
===================================
The policy definitions here are the backend's source of truth for
what actions are CONCEPTUALLY supported. When the Database Team delivers
a dynamic permission/role-permission table, this registry can be replaced
or supplemented by database-driven policy lookup via PermissionRepository.

DESIGN PRINCIPLES
=================
- Do NOT scatter permission strings across route handlers.
- All permission identifiers live here; routes reference them by constant.
- Deny by default: any action NOT in a role's policy set is DENIED.
- Admin permissions ≠ clinical access (admin:user_manage ≠ clinical_record:read).
- Role → Permission mapping is additive, not hierarchical by default.
"""

from enum import Enum
from typing import FrozenSet


# ---------------------------------------------------------------------------
# Permission Constants
# ---------------------------------------------------------------------------

class Permission(str, Enum):
    """Canonical permission identifiers.

    Format: "<resource>:<action>"

    New permissions must be added here and assigned to at least one role
    before routes can use them. Never create permission strings inline.
    """

    # ---- Patient self-access ----
    PATIENT_READ_SELF = "patient:read_self"
    PATIENT_UPDATE_SELF = "patient:update_self"

    # ---- Clinical records (requires relationship + consent checks) ----
    CLINICAL_RECORD_READ = "clinical_record:read"
    CLINICAL_RECORD_CREATE = "clinical_record:create"
    CLINICAL_RECORD_UPDATE = "clinical_record:update"

    # ---- Prescriptions ----
    PRESCRIPTION_READ = "prescription:read"
    PRESCRIPTION_CREATE = "prescription:create"

    # ---- Medications ----
    MEDICATION_READ = "medication:read"
    MEDICATION_UPDATE = "medication:update"

    # ---- Care plans ----
    CARE_PLAN_READ = "care_plan:read"
    CARE_PLAN_UPDATE = "care_plan:update"

    # ---- Consent lifecycle ----
    CONSENT_CREATE = "consent:create"
    CONSENT_READ = "consent:read"
    CONSENT_REVOKE = "consent:revoke"

    # ---- Admin user management (does NOT imply clinical access) ----
    ADMIN_USER_MANAGE = "admin:user_manage"
    ADMIN_AUDIT_READ = "admin:audit_read"


# ---------------------------------------------------------------------------
# Role-to-Permission Mapping
# ---------------------------------------------------------------------------
# IMPORTANT:
# - This is the STATIC default policy. Database-driven overrides are
#   a future Phase 3+ enhancement.
# - Permissions are additive; a role only has what is explicitly listed.
# - ADMIN role has administrative capabilities; it does NOT automatically
#   receive clinical_record:read or prescription:create etc.
# - DOCTOR permissions for clinical data are gated behind relationship +
#   consent checks at the service layer — having the permission here is a
#   necessary but NOT sufficient condition for access.

ROLE_PERMISSIONS: dict[str, FrozenSet[Permission]] = {
    "PATIENT": frozenset({
        Permission.PATIENT_READ_SELF,
        Permission.PATIENT_UPDATE_SELF,
        Permission.CLINICAL_RECORD_READ,   # own records only — ownership enforced in service
        Permission.PRESCRIPTION_READ,      # own prescriptions only
        Permission.MEDICATION_READ,
        Permission.CARE_PLAN_READ,
        Permission.CONSENT_CREATE,
        Permission.CONSENT_READ,
        Permission.CONSENT_REVOKE,
    }),
    "DOCTOR": frozenset({
        Permission.CLINICAL_RECORD_READ,   # gated by relationship + consent
        Permission.CLINICAL_RECORD_CREATE,
        Permission.CLINICAL_RECORD_UPDATE,
        Permission.PRESCRIPTION_READ,
        Permission.PRESCRIPTION_CREATE,
        Permission.MEDICATION_READ,
        Permission.MEDICATION_UPDATE,
        Permission.CARE_PLAN_READ,
        Permission.CARE_PLAN_UPDATE,
        Permission.CONSENT_READ,           # can view consent that applies to their access
    }),
    "ADMIN": frozenset({
        # Administrative capabilities ONLY — no automatic clinical data access
        Permission.ADMIN_USER_MANAGE,
        Permission.ADMIN_AUDIT_READ,
        Permission.CONSENT_READ,           # for compliance/audit purposes
    }),
}


# ---------------------------------------------------------------------------
# Resource Action → Required Permission Mapping
# ---------------------------------------------------------------------------
# Routes look up the permission required for an (resource_type, action) pair.
# Centralizes policy intent without embedding strings in handlers.

ACTION_PERMISSION_MAP: dict[tuple[str, str], Permission] = {
    ("patient_profile", "read"):          Permission.PATIENT_READ_SELF,
    ("patient_profile", "update"):        Permission.PATIENT_UPDATE_SELF,
    ("clinical_record", "read"):          Permission.CLINICAL_RECORD_READ,
    ("clinical_record", "create"):        Permission.CLINICAL_RECORD_CREATE,
    ("clinical_record", "update"):        Permission.CLINICAL_RECORD_UPDATE,
    ("prescription", "read"):             Permission.PRESCRIPTION_READ,
    ("prescription", "create"):           Permission.PRESCRIPTION_CREATE,
    ("medication", "read"):               Permission.MEDICATION_READ,
    ("medication", "update"):             Permission.MEDICATION_UPDATE,
    ("care_plan", "read"):                Permission.CARE_PLAN_READ,
    ("care_plan", "update"):              Permission.CARE_PLAN_UPDATE,
    ("consent", "create"):                Permission.CONSENT_CREATE,
    ("consent", "read"):                  Permission.CONSENT_READ,
    ("consent", "revoke"):                Permission.CONSENT_REVOKE,
    ("user_management", "manage"):        Permission.ADMIN_USER_MANAGE,
    ("audit_log", "read"):                Permission.ADMIN_AUDIT_READ,
}


# ---------------------------------------------------------------------------
# Consent Purpose Registry
# ---------------------------------------------------------------------------
# Supported consent purposes. Prevents arbitrary client-submitted purposes.
# Database team should eventually own this as a reference table.

class ConsentPurpose(str, Enum):
    """Supported consent purposes in HealthSetu.

    DATABASE TEAM DEPENDENCY:
    When a consent_purpose reference table is available, this enum should
    be validated against live database values. Until then this is the
    authoritative set of supported purposes.
    """

    CARE_DELIVERY = "care_delivery"
    EMERGENCY_ACCESS = "emergency_access"
    RESEARCH = "research"          # requires explicit separate consent grant
    ADMINISTRATIVE = "administrative"
    SECOND_OPINION = "second_opinion"


# ---------------------------------------------------------------------------
# Consent Scope Registry
# ---------------------------------------------------------------------------
# What resource scopes a consent can cover.

class ConsentScope(str, Enum):
    """Resource scopes that consent can cover.

    A consent for 'care_delivery' with scope 'clinical_records' does NOT
    automatically authorize access to 'prescriptions' or 'documents'.
    """

    CLINICAL_RECORDS = "clinical_records"
    PRESCRIPTIONS = "prescriptions"
    MEDICATIONS = "medications"
    CARE_PLAN = "care_plan"
    DOCUMENTS = "documents"
    DISCHARGE_SUMMARY = "discharge_summary"
    ALL_RECORDS = "all_records"   # broad scope — must require explicit grant


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

def get_role_permissions(role: str) -> FrozenSet[Permission]:
    """Return the set of permissions for the given role string.

    Unknown roles receive an empty frozenset (deny by default).
    """
    return ROLE_PERMISSIONS.get(role.upper(), frozenset())


def role_has_permission(role: str, permission: Permission) -> bool:
    """Check whether the given role includes the specified permission."""
    return permission in get_role_permissions(role)


def get_required_permission(resource_type: str, action: str) -> Permission | None:
    """Resolve the required Permission for a (resource_type, action) pair.

    Returns None if the combination is not registered (unknown = deny).
    """
    return ACTION_PERMISSION_MAP.get((resource_type.lower(), action.lower()))


def is_valid_consent_purpose(purpose: str) -> bool:
    """Check whether a purpose string is a recognized consent purpose."""
    return purpose in {p.value for p in ConsentPurpose}


def is_valid_consent_scope(scope: str) -> bool:
    """Check whether a scope string is a recognized consent scope."""
    return scope in {s.value for s in ConsentScope}
