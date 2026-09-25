"""Phase 3 security tests: HTTP authorization semantics, policy isolation, and audit PHI exclusion."""

import pytest

from app.api.deps import _global_audit_repo
from app.core.policies import Permission, ROLE_PERMISSIONS
from app.services.audit_service import AuditService


class TestHttpAuthorizationSemantics:
    """Test correct HTTP status codes: 401 vs 403 vs 404."""

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_jwt_returns_401(self, async_client):
        """Consent endpoint without JWT → 401 (not 403, not 200)."""
        response = await async_client.post(
            "/api/v1/consents",
            json={"grantee_id": "dr-1", "purpose": "care_delivery", "scope": "clinical_records"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_malformed_jwt_returns_401(self, async_client):
        """Malformed/invalid JWT token → 401."""
        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer not.a.real.jwt.token"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_jwt_insufficient_permission_returns_403(self, async_client, seeded_users, make_token):
        """Valid JWT but role lacks permission → 403."""
        # Doctor trying to create consent (only PATIENT can do this)
        token = make_token("usr-doctor-001", "DOCTOR")
        response = await async_client.post(
            "/api/v1/consents",
            json={"grantee_id": "usr-patient-001", "purpose": "care_delivery", "scope": "clinical_records"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
        body = response.json()
        assert body["success"] is False

    @pytest.mark.asyncio
    async def test_401_response_never_says_forbidden(self, async_client):
        """401 response must not use 403 language, and vice versa."""
        response = await async_client.post(
            "/api/v1/consents",
            json={"grantee_id": "dr-1", "purpose": "care_delivery", "scope": "clinical_records"},
        )
        assert response.status_code == 401
        body = response.json()
        assert "error" in body
        # Error code should be UNAUTHORIZED, not FORBIDDEN
        assert body["error"]["code"] == "UNAUTHORIZED"

    @pytest.mark.asyncio
    async def test_wrong_scheme_returns_401(self, async_client):
        """Using Basic instead of Bearer → 401."""
        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert response.status_code == 401


class TestPolicyIsolation:
    """Test that role policies are properly isolated (no cross-role bleed)."""

    def test_admin_has_no_clinical_write_permission(self):
        """ADMIN role must NOT have clinical_record:create permission."""
        admin_perms = ROLE_PERMISSIONS.get("ADMIN", frozenset())
        assert Permission.CLINICAL_RECORD_CREATE not in admin_perms

    def test_admin_has_no_clinical_read_permission(self):
        """ADMIN role must NOT have clinical_record:read permission."""
        admin_perms = ROLE_PERMISSIONS.get("ADMIN", frozenset())
        assert Permission.CLINICAL_RECORD_READ not in admin_perms

    def test_patient_has_no_admin_permission(self):
        """PATIENT role must NOT have admin:user_manage permission."""
        patient_perms = ROLE_PERMISSIONS.get("PATIENT", frozenset())
        assert Permission.ADMIN_USER_MANAGE not in patient_perms

    def test_patient_has_no_prescription_create_permission(self):
        """PATIENT must NOT be able to create prescriptions."""
        patient_perms = ROLE_PERMISSIONS.get("PATIENT", frozenset())
        assert Permission.PRESCRIPTION_CREATE not in patient_perms

    def test_doctor_has_no_admin_permission(self):
        """DOCTOR must NOT have admin:user_manage permission."""
        doctor_perms = ROLE_PERMISSIONS.get("DOCTOR", frozenset())
        assert Permission.ADMIN_USER_MANAGE not in doctor_perms

    def test_doctor_has_no_consent_create(self):
        """DOCTOR must NOT be able to create patient consent directly."""
        doctor_perms = ROLE_PERMISSIONS.get("DOCTOR", frozenset())
        assert Permission.CONSENT_CREATE not in doctor_perms

    def test_unknown_role_has_no_permissions(self):
        """Any unknown role string must have zero permissions (deny by default)."""
        from app.core.policies import get_role_permissions
        perms = get_role_permissions("FUTURE_UNKNOWN_ROLE")
        assert len(perms) == 0


class TestAuditPHIExclusion:
    """Test that audit events never contain PHI."""

    @pytest.mark.asyncio
    async def test_audit_service_strips_phi_keys_from_metadata(self):
        """AuditService must strip known PHI keys from metadata before persisting."""
        from app.repositories.audit_repository import AuditRepository
        from app.schemas.audit import AuditEventType

        repo = AuditRepository()
        svc = AuditService(audit_repository=repo)

        # Attempt to record event with PHI metadata (should be stripped)
        await svc.record(
            event_type=AuditEventType.AUTHZ_ACCESS_DENIED,
            outcome="DENY",
            actor_id="usr-1",
            action="clinical_record:read",
            metadata={
                "diagnosis": "secret diagnosis",     # PHI — must be stripped
                "resource_type": "clinical_record",  # safe — should remain
                "prescription": "secret Rx",         # PHI — must be stripped
            },
        )

        assert len(repo._events) == 1
        event = repo._events[0]
        if event.metadata:
            assert "diagnosis" not in event.metadata
            assert "prescription" not in event.metadata
            # Safe key should survive
            assert "resource_type" in event.metadata

    @pytest.mark.asyncio
    async def test_audit_event_does_not_contain_token_fields(self):
        """Audit events must never contain token or secret fields."""
        from app.repositories.audit_repository import AuditRepository
        from app.schemas.audit import AuditEventType

        repo = AuditRepository()
        svc = AuditService(audit_repository=repo)

        await svc.record(
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
            outcome="ALLOW",
            actor_id="usr-1",
            metadata={
                "access_token": "eyJhbGci...",  # must be stripped
                "secret": "topsecret",          # must be stripped
                "user_agent": "Mozilla/5.0",    # safe
            },
        )

        event = repo._events[0]
        if event.metadata:
            assert "access_token" not in event.metadata
            assert "secret" not in event.metadata

    @pytest.mark.asyncio
    async def test_consent_audit_does_not_expose_medical_data(self, async_client, seeded_users, make_token):
        """Creating a consent via API must not put PHI in audit events."""
        token = make_token("usr-patient-001", "PATIENT")
        await async_client.post(
            "/api/v1/consents",
            json={"grantee_id": "usr-doctor-001", "purpose": "care_delivery", "scope": "clinical_records"},
            headers={"Authorization": f"Bearer {token}"},
        )
        phi_keys = {"diagnosis", "prescription", "medication", "symptoms", "history"}
        for event in _global_audit_repo._events:
            if event.metadata:
                assert not phi_keys.intersection(event.metadata.keys())


class TestAuthorizationErrorOpacity:
    """Test that authorization errors do not leak internal policy details."""

    @pytest.mark.asyncio
    async def test_403_response_does_not_leak_policy_details(self, async_client, seeded_users, make_token):
        """403 response must not contain internal denial reason codes or policy details."""
        token = make_token("usr-doctor-001", "DOCTOR")
        response = await async_client.post(
            "/api/v1/consents",
            json={"grantee_id": "usr-patient-001", "purpose": "care_delivery", "scope": "clinical_records"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
        body = response.json()
        response_text = str(body)
        # Internal enum values must not be exposed
        assert "NO_PERMISSION" not in response_text
        assert "DenialReason" not in response_text
        assert "ROLE_PERMISSIONS" not in response_text

    @pytest.mark.asyncio
    async def test_404_for_inaccessible_consent_not_403(self, async_client, seeded_users, make_token):
        """Unauthorized consent access should return 404, not 403 (no existence leak)."""
        patient1_token = make_token("usr-patient-001", "PATIENT")
        patient2_token = make_token("usr-patient-002", "PATIENT")

        create_resp = await async_client.post(
            "/api/v1/consents",
            json={"grantee_id": "usr-doctor-001", "purpose": "care_delivery", "scope": "clinical_records"},
            headers={"Authorization": f"Bearer {patient1_token}"},
        )
        consent_id = create_resp.json()["data"]["id"]

        read_resp = await async_client.get(
            f"/api/v1/consents/{consent_id}",
            headers={"Authorization": f"Bearer {patient2_token}"},
        )
        assert read_resp.status_code == 404  # not 403

    @pytest.mark.asyncio
    async def test_tokens_not_logged(self, async_client, seeded_users, make_token):
        """Tokens must not appear in audit events after consent creation."""
        token = make_token("usr-patient-001", "PATIENT")
        await async_client.post(
            "/api/v1/consents",
            json={"grantee_id": "usr-doctor-001", "purpose": "care_delivery", "scope": "clinical_records"},
            headers={"Authorization": f"Bearer {token}"},
        )
        for event in _global_audit_repo._events:
            event_str = str(event)
            assert "eyJ" not in event_str   # JWT prefix never in audit records
