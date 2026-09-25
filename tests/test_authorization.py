"""Phase 3 tests: Authorization service — permission, ownership, relationship, and consent checks."""

import pytest
from unittest.mock import AsyncMock

from app.api.deps import _global_audit_repo, _global_consent_repo, _global_permission_repo
from app.core.policies import Permission
from app.repositories.audit_repository import AuditRepository
from app.repositories.consent_repository import ConsentRepository
from app.repositories.permission_repository import PermissionRepository
from app.schemas.auth import AccountStatus, UserRole
from app.schemas.authorization import AuthorizationContext, DenialReason
from app.schemas.user import AuthenticatedUserContext
from app.services.audit_service import AuditService
from app.services.authorization_service import AuthorizationService
from app.services.consent_service import ConsentService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def patient_user() -> AuthenticatedUserContext:
    return AuthenticatedUserContext(
        user_id="usr-patient-001",
        role=UserRole.PATIENT,
        account_status=AccountStatus.ACTIVE,
    )


@pytest.fixture
def doctor_user() -> AuthenticatedUserContext:
    return AuthenticatedUserContext(
        user_id="usr-doctor-001",
        role=UserRole.DOCTOR,
        account_status=AccountStatus.ACTIVE,
    )


@pytest.fixture
def admin_user() -> AuthenticatedUserContext:
    return AuthenticatedUserContext(
        user_id="usr-admin-001",
        role=UserRole.ADMIN,
        account_status=AccountStatus.ACTIVE,
    )


@pytest.fixture
def permission_repo() -> PermissionRepository:
    return _global_permission_repo


@pytest.fixture
def consent_repo() -> ConsentRepository:
    return _global_consent_repo


@pytest.fixture
def audit_repo() -> AuditRepository:
    return _global_audit_repo


@pytest.fixture
def audit_service(audit_repo: AuditRepository) -> AuditService:
    return AuditService(audit_repository=audit_repo)


@pytest.fixture
def consent_service(consent_repo: ConsentRepository) -> ConsentService:
    return ConsentService(consent_repository=consent_repo)


@pytest.fixture
def authz_service(
    permission_repo: PermissionRepository,
    consent_service: ConsentService,
    audit_service: AuditService,
) -> AuthorizationService:
    return AuthorizationService(
        permission_repository=permission_repo,
        consent_service=consent_service,
        audit_service=audit_service,
    )


def _ctx(user: AuthenticatedUserContext, owner_id: str | None = None, resource_type: str = "clinical_record") -> AuthorizationContext:
    return AuthorizationContext(
        user_id=user.user_id,
        role=user.role.value,
        resource_type=resource_type,
        resource_owner_id=owner_id,
    )


# ===========================================================================
# 1. Permission Check Tests
# ===========================================================================

class TestPermissionCheck:
    """Test 1: Permission check — role → permission evaluation."""

    @pytest.mark.asyncio
    async def test_patient_has_consent_create_permission(self, authz_service, patient_user):
        """PATIENT role must have consent:create permission."""
        decision = await authz_service.check_permission(patient_user, Permission.CONSENT_CREATE)
        assert decision.allowed is True

    @pytest.mark.asyncio
    async def test_patient_lacks_admin_permission(self, authz_service, patient_user):
        """PATIENT must NOT have admin:user_manage permission."""
        decision = await authz_service.check_permission(patient_user, Permission.ADMIN_USER_MANAGE)
        assert decision.allowed is False
        assert decision.reason == DenialReason.NO_PERMISSION

    @pytest.mark.asyncio
    async def test_doctor_has_clinical_record_read(self, authz_service, doctor_user):
        """DOCTOR must have clinical_record:read permission."""
        decision = await authz_service.check_permission(doctor_user, Permission.CLINICAL_RECORD_READ)
        assert decision.allowed is True

    @pytest.mark.asyncio
    async def test_doctor_lacks_admin_permission(self, authz_service, doctor_user):
        """DOCTOR must NOT have admin:user_manage permission."""
        decision = await authz_service.check_permission(doctor_user, Permission.ADMIN_USER_MANAGE)
        assert decision.allowed is False

    @pytest.mark.asyncio
    async def test_admin_has_user_manage(self, authz_service, admin_user):
        """ADMIN must have admin:user_manage permission."""
        decision = await authz_service.check_permission(admin_user, Permission.ADMIN_USER_MANAGE)
        assert decision.allowed is True

    @pytest.mark.asyncio
    async def test_admin_lacks_clinical_record_write(self, authz_service, admin_user):
        """ADMIN must NOT have clinical_record:create permission (no auto clinical access)."""
        decision = await authz_service.check_permission(admin_user, Permission.CLINICAL_RECORD_CREATE)
        assert decision.allowed is False

    @pytest.mark.asyncio
    async def test_unknown_role_denied(self, authz_service):
        """An unknown role must be denied all permissions (deny by default)."""
        unknown_user = AuthenticatedUserContext(
            user_id="x", role=UserRole.PATIENT, account_status=AccountStatus.ACTIVE
        )
        # Manually override role for this test
        import app.core.policies as pol
        perms = pol.get_role_permissions("UNKNOWN_ROLE")
        assert len(perms) == 0


# ===========================================================================
# 2. Resource Ownership Tests
# ===========================================================================

class TestResourceOwnership:
    """Test 2: Ownership check — patient self-access vs cross-patient access."""

    @pytest.mark.asyncio
    async def test_patient_accessing_own_resource_allowed(self, authz_service, patient_user):
        """Patient accessing their own resource → ALLOW."""
        decision = authz_service.check_resource_ownership(patient_user, patient_user.user_id)
        assert decision.allowed is True

    @pytest.mark.asyncio
    async def test_patient_accessing_other_patient_resource_denied(self, authz_service, patient_user):
        """Patient accessing another patient's resource → DENY."""
        decision = authz_service.check_resource_ownership(patient_user, "usr-patient-002")
        assert decision.allowed is False
        assert decision.reason == DenialReason.NOT_RESOURCE_OWNER

    @pytest.mark.asyncio
    async def test_doctor_not_owner_of_patient_resource(self, authz_service, doctor_user):
        """Doctor is not the owner of a patient's resource → DENY (ownership check only)."""
        decision = authz_service.check_resource_ownership(doctor_user, "usr-patient-001")
        assert decision.allowed is False


# ===========================================================================
# 3. Relationship Check Tests (DB DEPENDENCY — expect DENY until delivered)
# ===========================================================================

class TestRelationshipCheck:
    """Test 3: Relationship check — provider–patient relationship evaluation."""

    @pytest.mark.asyncio
    async def test_self_access_always_has_relationship(self, authz_service, patient_user):
        """A patient accessing their own data always passes relationship check."""
        decision = await authz_service.check_relationship(
            requester_id=patient_user.user_id,
            patient_id=patient_user.user_id,
        )
        assert decision.allowed is True

    @pytest.mark.asyncio
    async def test_doctor_without_relationship_denied(self, authz_service, doctor_user):
        """Doctor without a stored relationship → DENY (DB dependency pending)."""
        decision = await authz_service.check_relationship(
            requester_id=doctor_user.user_id,
            patient_id="usr-patient-001",
        )
        assert decision.allowed is False
        assert decision.reason == DenialReason.NO_RELATIONSHIP

    @pytest.mark.asyncio
    async def test_admin_without_relationship_denied(self, authz_service, admin_user):
        """ADMIN without explicit relationship → DENY (no auto clinical access)."""
        decision = await authz_service.check_relationship(
            requester_id=admin_user.user_id,
            patient_id="usr-patient-001",
        )
        assert decision.allowed is False


# ===========================================================================
# 4. Full Authorization Pipeline Tests
# ===========================================================================

class TestAuthorizePipeline:
    """Test 4: Full authorize() pipeline — end-to-end evaluation."""

    @pytest.mark.asyncio
    async def test_patient_reads_own_profile_allowed(self, authz_service, patient_user):
        """Patient reading their own profile → ALLOW (permission + no ownership block)."""
        ctx = _ctx(patient_user, owner_id=patient_user.user_id, resource_type="patient_profile")
        decision = await authz_service.authorize(
            user=patient_user,
            action="patient:read_self",
            context=ctx,
        )
        assert decision.allowed is True

    @pytest.mark.asyncio
    async def test_patient_reads_other_patient_resource_denied_by_ownership(self, authz_service, patient_user):
        """Patient trying to access another patient's resource → DENY at ownership step."""
        ctx = _ctx(patient_user, owner_id="usr-patient-002", resource_type="clinical_record")
        decision = await authz_service.authorize(
            user=patient_user,
            action="clinical_record:read",
            context=ctx,
            require_ownership=True,
        )
        assert decision.allowed is False
        assert decision.reason == DenialReason.NOT_RESOURCE_OWNER

    @pytest.mark.asyncio
    async def test_admin_clinical_record_read_denied_no_permission(self, authz_service, admin_user):
        """ADMIN attempting clinical_record:read → DENY (no clinical read permission)."""
        ctx = _ctx(admin_user, owner_id="usr-patient-001", resource_type="clinical_record")
        decision = await authz_service.authorize(
            user=admin_user,
            action="clinical_record:read",
            context=ctx,
        )
        assert decision.allowed is False
        assert decision.reason == DenialReason.NO_PERMISSION

    @pytest.mark.asyncio
    async def test_doctor_no_relationship_denied(self, authz_service, doctor_user):
        """Doctor with permission but no relationship → DENY at relationship step."""
        ctx = _ctx(doctor_user, owner_id="usr-patient-001", resource_type="clinical_record")
        decision = await authz_service.authorize(
            user=doctor_user,
            action="clinical_record:read",
            context=ctx,
            require_relationship=True,
        )
        assert decision.allowed is False
        assert decision.reason == DenialReason.NO_RELATIONSHIP

    @pytest.mark.asyncio
    async def test_unknown_action_denied(self, authz_service, patient_user):
        """Unknown action that cannot be resolved → DENY (deny by default)."""
        ctx = _ctx(patient_user, resource_type="unknown_resource")
        decision = await authz_service.authorize(
            user=patient_user,
            action="unknown_resource:unknown_action",
            context=ctx,
        )
        assert decision.allowed is False
        assert decision.reason == DenialReason.UNKNOWN_POLICY

    @pytest.mark.asyncio
    async def test_audit_event_emitted_on_allow(self, authz_service, patient_user, audit_repo):
        """An ALLOW decision must emit an audit event."""
        ctx = _ctx(patient_user, owner_id=patient_user.user_id, resource_type="patient_profile")
        await authz_service.authorize(
            user=patient_user,
            action="patient:read_self",
            context=ctx,
        )
        assert len(audit_repo._events) > 0
        outcomes = [e.outcome for e in audit_repo._events]
        assert "ALLOW" in outcomes

    @pytest.mark.asyncio
    async def test_audit_event_emitted_on_deny(self, authz_service, admin_user, audit_repo):
        """A DENY decision must emit an audit event."""
        ctx = _ctx(admin_user, owner_id="usr-patient-001", resource_type="clinical_record")
        await authz_service.authorize(
            user=admin_user,
            action="clinical_record:read",
            context=ctx,
        )
        assert len(audit_repo._events) > 0
        outcomes = [e.outcome for e in audit_repo._events]
        assert "DENY" in outcomes

    @pytest.mark.asyncio
    async def test_audit_events_contain_no_phi(self, authz_service, patient_user, audit_repo):
        """Audit events must not contain PHI keys."""
        ctx = _ctx(patient_user, owner_id=patient_user.user_id, resource_type="patient_profile")
        await authz_service.authorize(
            user=patient_user, action="patient:read_self", context=ctx
        )
        phi_keys = {"diagnosis", "prescription", "medication", "history", "symptoms"}
        for event in audit_repo._events:
            if event.metadata:
                assert not phi_keys.intersection(event.metadata.keys())
