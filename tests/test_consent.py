"""Phase 3 tests: Consent service and consent API endpoints."""

from datetime import datetime, timedelta, timezone

import pytest

from app.api.deps import _global_audit_repo, _global_consent_repo
from app.repositories.consent_repository import ConsentRecord, ConsentRepository
from app.schemas.authorization import ConsentCreateRequest, ConsentStatus, DenialReason
from app.services.audit_service import AuditService
from app.services.consent_service import ConsentService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def consent_repo() -> ConsentRepository:
    return _global_consent_repo


@pytest.fixture
def audit_service() -> AuditService:
    return AuditService(audit_repository=_global_audit_repo)


@pytest.fixture
def consent_service(consent_repo) -> ConsentService:
    return ConsentService(consent_repository=consent_repo)


PATIENT_ID = "usr-patient-001"
DOCTOR_ID = "usr-doctor-001"
ADMIN_ID = "usr-admin-001"
OTHER_PATIENT_ID = "usr-patient-002"


def _create_request(
    grantee_id: str = DOCTOR_ID,
    purpose: str = "care_delivery",
    scope: str = "clinical_records",
    expires_at: datetime | None = None,
) -> ConsentCreateRequest:
    return ConsentCreateRequest(
        grantee_id=grantee_id,
        purpose=purpose,
        scope=scope,
        expires_at=expires_at,
    )


# ===========================================================================
# Consent Service Tests
# ===========================================================================

class TestConsentCreation:
    """Tests for ConsentService.create_consent()."""

    @pytest.mark.asyncio
    async def test_patient_can_create_consent(self, consent_service):
        """A PATIENT may create consent on their own behalf."""
        consent = await consent_service.create_consent(
            requester_id=PATIENT_ID,
            requester_role="PATIENT",
            request=_create_request(),
        )
        assert consent.patient_id == PATIENT_ID
        assert consent.grantee_id == DOCTOR_ID
        assert consent.status == ConsentStatus.ACTIVE
        assert consent.purpose == "care_delivery"
        assert consent.scope == "clinical_records"

    @pytest.mark.asyncio
    async def test_doctor_cannot_create_consent_on_behalf_of_patient(self, consent_service):
        """A DOCTOR may NOT create consent on behalf of a patient."""
        from app.core.exceptions import ForbiddenException
        with pytest.raises(ForbiddenException):
            await consent_service.create_consent(
                requester_id=DOCTOR_ID,
                requester_role="DOCTOR",
                request=_create_request(),
            )

    @pytest.mark.asyncio
    async def test_admin_cannot_create_consent_on_behalf_of_patient(self, consent_service):
        """An ADMIN may NOT create consent on behalf of a patient."""
        from app.core.exceptions import ForbiddenException
        with pytest.raises(ForbiddenException):
            await consent_service.create_consent(
                requester_id=ADMIN_ID,
                requester_role="ADMIN",
                request=_create_request(),
            )

    @pytest.mark.asyncio
    async def test_invalid_purpose_rejected(self, consent_service):
        """Unsupported consent purpose must be rejected."""
        from app.core.exceptions import ValidationException
        req = ConsentCreateRequest(grantee_id=DOCTOR_ID, purpose="marketing", scope="clinical_records")
        with pytest.raises(ValidationException, match="Unsupported consent purpose"):
            await consent_service.create_consent(
                requester_id=PATIENT_ID, requester_role="PATIENT", request=req
            )

    @pytest.mark.asyncio
    async def test_invalid_scope_rejected(self, consent_service):
        """Unsupported consent scope must be rejected."""
        from app.core.exceptions import ValidationException
        req = ConsentCreateRequest(grantee_id=DOCTOR_ID, purpose="care_delivery", scope="everything")
        with pytest.raises(ValidationException, match="Unsupported consent scope"):
            await consent_service.create_consent(
                requester_id=PATIENT_ID, requester_role="PATIENT", request=req
            )

    @pytest.mark.asyncio
    async def test_past_expiry_rejected(self, consent_service):
        """Consent with past expiry must be rejected."""
        from app.core.exceptions import ValidationException
        past = datetime.now(timezone.utc) - timedelta(days=1)
        req = _create_request(expires_at=past)
        with pytest.raises(ValidationException, match="future"):
            await consent_service.create_consent(
                requester_id=PATIENT_ID, requester_role="PATIENT", request=req
            )

    @pytest.mark.asyncio
    async def test_self_grant_rejected(self, consent_service):
        """A patient cannot grant consent to themselves."""
        from app.core.exceptions import ValidationException
        req = ConsentCreateRequest(grantee_id=PATIENT_ID, purpose="care_delivery", scope="clinical_records")
        with pytest.raises(ValidationException, match="yourself"):
            await consent_service.create_consent(
                requester_id=PATIENT_ID, requester_role="PATIENT", request=req
            )


class TestConsentRevocation:
    """Tests for ConsentService.revoke_consent()."""

    @pytest.mark.asyncio
    async def test_patient_can_revoke_own_consent(self, consent_service):
        """Patient can revoke their own consent."""
        consent = await consent_service.create_consent(
            requester_id=PATIENT_ID,
            requester_role="PATIENT",
            request=_create_request(),
        )
        revoked = await consent_service.revoke_consent(
            requester_id=PATIENT_ID,
            requester_role="PATIENT",
            consent_id=consent.id,
        )
        assert revoked.status == ConsentStatus.REVOKED
        assert revoked.revoked_at is not None

    @pytest.mark.asyncio
    async def test_other_patient_cannot_revoke_consent(self, consent_service):
        """Another patient cannot revoke someone else's consent."""
        from app.core.exceptions import ForbiddenException
        consent = await consent_service.create_consent(
            requester_id=PATIENT_ID,
            requester_role="PATIENT",
            request=_create_request(),
        )
        with pytest.raises(ForbiddenException):
            await consent_service.revoke_consent(
                requester_id=OTHER_PATIENT_ID,
                requester_role="PATIENT",
                consent_id=consent.id,
            )

    @pytest.mark.asyncio
    async def test_doctor_cannot_revoke_patient_consent(self, consent_service):
        """A doctor cannot revoke a patient's consent."""
        from app.core.exceptions import ForbiddenException
        consent = await consent_service.create_consent(
            requester_id=PATIENT_ID,
            requester_role="PATIENT",
            request=_create_request(),
        )
        with pytest.raises(ForbiddenException):
            await consent_service.revoke_consent(
                requester_id=DOCTOR_ID,
                requester_role="DOCTOR",
                consent_id=consent.id,
            )

    @pytest.mark.asyncio
    async def test_revoking_nonexistent_consent_raises_404(self, consent_service):
        """Revoking a non-existent consent should raise NotFoundException."""
        from app.core.exceptions import NotFoundException
        with pytest.raises(NotFoundException):
            await consent_service.revoke_consent(
                requester_id=PATIENT_ID,
                requester_role="PATIENT",
                consent_id="nonexistent-id",
            )

    @pytest.mark.asyncio
    async def test_double_revocation_raises_validation_error(self, consent_service):
        """Revoking an already-revoked consent raises ValidationException."""
        from app.core.exceptions import ValidationException
        consent = await consent_service.create_consent(
            requester_id=PATIENT_ID,
            requester_role="PATIENT",
            request=_create_request(),
        )
        await consent_service.revoke_consent(
            requester_id=PATIENT_ID, requester_role="PATIENT", consent_id=consent.id
        )
        with pytest.raises(ValidationException, match="already been revoked"):
            await consent_service.revoke_consent(
                requester_id=PATIENT_ID, requester_role="PATIENT", consent_id=consent.id
            )


class TestConsentCheck:
    """Tests for ConsentService.check_consent() — core consent evaluation."""

    @pytest.mark.asyncio
    async def test_active_consent_passes_check(self, consent_service):
        """Active consent matching all dimensions → allowed."""
        await consent_service.create_consent(
            requester_id=PATIENT_ID,
            requester_role="PATIENT",
            request=_create_request(purpose="care_delivery", scope="clinical_records"),
        )
        result = await consent_service.check_consent(
            patient_id=PATIENT_ID,
            requester_id=DOCTOR_ID,
            purpose="care_delivery",
            scope="clinical_records",
        )
        assert result.allowed is True
        assert result.consent_id is not None

    @pytest.mark.asyncio
    async def test_revoked_consent_fails_check(self, consent_service):
        """Revoked consent must fail the consent check."""
        consent = await consent_service.create_consent(
            requester_id=PATIENT_ID,
            requester_role="PATIENT",
            request=_create_request(),
        )
        await consent_service.revoke_consent(
            requester_id=PATIENT_ID, requester_role="PATIENT", consent_id=consent.id
        )
        result = await consent_service.check_consent(
            patient_id=PATIENT_ID,
            requester_id=DOCTOR_ID,
            purpose="care_delivery",
            scope="clinical_records",
        )
        assert result.allowed is False
        assert result.reason in (DenialReason.CONSENT_NOT_FOUND, DenialReason.CONSENT_REVOKED)

    @pytest.mark.asyncio
    async def test_expired_consent_fails_check(self, consent_service, consent_repo):
        """Expired consent must fail the consent check."""
        # Manually inject an expired record
        past = datetime.now(timezone.utc) - timedelta(days=1)
        record = ConsentRecord(
            id="expired-consent",
            patient_id=PATIENT_ID,
            grantee_id=DOCTOR_ID,
            purpose="care_delivery",
            scope="clinical_records",
            status=ConsentStatus.ACTIVE,
            granted_at=datetime.now(timezone.utc) - timedelta(days=2),
            effective_from=datetime.now(timezone.utc) - timedelta(days=2),
            expires_at=past,
        )
        await consent_repo.create_consent(record)
        result = await consent_service.check_consent(
            patient_id=PATIENT_ID,
            requester_id=DOCTOR_ID,
            purpose="care_delivery",
            scope="clinical_records",
        )
        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_wrong_purpose_fails_check(self, consent_service):
        """Consent for care_delivery does NOT satisfy a research check (purpose mismatch)."""
        await consent_service.create_consent(
            requester_id=PATIENT_ID,
            requester_role="PATIENT",
            request=_create_request(purpose="care_delivery", scope="clinical_records"),
        )
        result = await consent_service.check_consent(
            patient_id=PATIENT_ID,
            requester_id=DOCTOR_ID,
            purpose="research",  # different purpose
            scope="clinical_records",
        )
        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_wrong_scope_fails_check(self, consent_service):
        """Consent for clinical_records does NOT satisfy a prescriptions check (scope mismatch)."""
        await consent_service.create_consent(
            requester_id=PATIENT_ID,
            requester_role="PATIENT",
            request=_create_request(purpose="care_delivery", scope="clinical_records"),
        )
        result = await consent_service.check_consent(
            patient_id=PATIENT_ID,
            requester_id=DOCTOR_ID,
            purpose="care_delivery",
            scope="prescriptions",  # different scope
        )
        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_no_consent_fails_check(self, consent_service):
        """No consent record at all → denied."""
        result = await consent_service.check_consent(
            patient_id=PATIENT_ID,
            requester_id=DOCTOR_ID,
            purpose="care_delivery",
            scope="clinical_records",
        )
        assert result.allowed is False
        assert result.reason == DenialReason.CONSENT_NOT_FOUND


class TestConsentRetrieval:
    """Tests for ConsentService.get_consent() and list_my_consents()."""

    @pytest.mark.asyncio
    async def test_patient_can_read_own_consent(self, consent_service):
        """Patient can retrieve their own consent by ID."""
        consent = await consent_service.create_consent(
            requester_id=PATIENT_ID,
            requester_role="PATIENT",
            request=_create_request(),
        )
        retrieved = await consent_service.get_consent(
            requester_id=PATIENT_ID,
            requester_role="PATIENT",
            consent_id=consent.id,
        )
        assert retrieved.id == consent.id

    @pytest.mark.asyncio
    async def test_grantee_can_read_consent(self, consent_service):
        """The grantee (doctor) can also read the consent record."""
        consent = await consent_service.create_consent(
            requester_id=PATIENT_ID,
            requester_role="PATIENT",
            request=_create_request(grantee_id=DOCTOR_ID),
        )
        retrieved = await consent_service.get_consent(
            requester_id=DOCTOR_ID,
            requester_role="DOCTOR",
            consent_id=consent.id,
        )
        assert retrieved.id == consent.id

    @pytest.mark.asyncio
    async def test_admin_can_read_any_consent(self, consent_service):
        """ADMIN can read any consent record."""
        consent = await consent_service.create_consent(
            requester_id=PATIENT_ID,
            requester_role="PATIENT",
            request=_create_request(),
        )
        retrieved = await consent_service.get_consent(
            requester_id=ADMIN_ID,
            requester_role="ADMIN",
            consent_id=consent.id,
        )
        assert retrieved.id == consent.id

    @pytest.mark.asyncio
    async def test_other_patient_cannot_read_consent(self, consent_service):
        """Another patient cannot read someone else's consent (generic 404)."""
        from app.core.exceptions import NotFoundException
        consent = await consent_service.create_consent(
            requester_id=PATIENT_ID,
            requester_role="PATIENT",
            request=_create_request(),
        )
        with pytest.raises(NotFoundException):
            await consent_service.get_consent(
                requester_id=OTHER_PATIENT_ID,
                requester_role="PATIENT",
                consent_id=consent.id,
            )

    @pytest.mark.asyncio
    async def test_list_my_consents_returns_own_only(self, consent_service):
        """list_my_consents returns only the patient's own consents."""
        await consent_service.create_consent(
            requester_id=PATIENT_ID, requester_role="PATIENT", request=_create_request()
        )
        result = await consent_service.list_my_consents(requester_id=PATIENT_ID)
        assert len(result) == 1
        assert all(c.patient_id == PATIENT_ID for c in result)

        # Other patient's list should be empty
        result2 = await consent_service.list_my_consents(requester_id=OTHER_PATIENT_ID)
        assert len(result2) == 0


# ===========================================================================
# Consent API Endpoint Tests (HTTP layer)
# ===========================================================================

class TestConsentEndpoints:
    """Integration tests for consent API endpoints."""

    @pytest.mark.asyncio
    async def test_create_consent_unauthenticated_returns_401(self, async_client):
        """POST /consents without authentication → 401."""
        response = await async_client.post(
            "/api/v1/consents",
            json={"grantee_id": DOCTOR_ID, "purpose": "care_delivery", "scope": "clinical_records"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_consent_as_patient_returns_201(self, async_client, seeded_users, make_token):
        """POST /consents with patient token and valid body → 201."""
        token = make_token("usr-patient-001", "PATIENT")
        response = await async_client.post(
            "/api/v1/consents",
            json={"grantee_id": "usr-doctor-001", "purpose": "care_delivery", "scope": "clinical_records"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True
        assert body["data"]["status"] == "ACTIVE"

    @pytest.mark.asyncio
    async def test_create_consent_as_doctor_returns_403(self, async_client, seeded_users, make_token):
        """POST /consents as a DOCTOR → 403 (only patients may create consent)."""
        token = make_token("usr-doctor-001", "DOCTOR")
        response = await async_client.post(
            "/api/v1/consents",
            json={"grantee_id": "usr-patient-001", "purpose": "care_delivery", "scope": "clinical_records"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_consent_invalid_purpose_returns_422(self, async_client, seeded_users, make_token):
        """POST /consents with unknown purpose → 422."""
        token = make_token("usr-patient-001", "PATIENT")
        response = await async_client.post(
            "/api/v1/consents",
            json={"grantee_id": "usr-doctor-001", "purpose": "spying", "scope": "clinical_records"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_consent_unauthenticated_returns_401(self, async_client):
        """GET /consents/{id} without authentication → 401."""
        response = await async_client.get("/api/v1/consents/some-id")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_nonexistent_consent_returns_404(self, async_client, seeded_users, make_token):
        """GET /consents/{id} for nonexistent consent → 404."""
        token = make_token("usr-patient-001", "PATIENT")
        response = await async_client.get(
            "/api/v1/consents/nonexistent-id",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_revoke_consent_as_patient_returns_200(self, async_client, seeded_users, make_token):
        """POST /consents/{id}/revoke by patient subject → 200."""
        token = make_token("usr-patient-001", "PATIENT")
        # First create
        create_resp = await async_client.post(
            "/api/v1/consents",
            json={"grantee_id": "usr-doctor-001", "purpose": "care_delivery", "scope": "clinical_records"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert create_resp.status_code == 201
        consent_id = create_resp.json()["data"]["id"]

        # Then revoke
        revoke_resp = await async_client.post(
            f"/api/v1/consents/{consent_id}/revoke",
            json={"reason": "No longer needed"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert revoke_resp.status_code == 200
        assert revoke_resp.json()["data"]["status"] == "REVOKED"

    @pytest.mark.asyncio
    async def test_list_consents_unauthenticated_returns_401(self, async_client):
        """GET /consents without authentication → 401."""
        response = await async_client.get("/api/v1/consents")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_consents_as_patient_returns_200(self, async_client, seeded_users, make_token):
        """GET /consents as patient → 200 with empty list initially."""
        token = make_token("usr-patient-001", "PATIENT")
        response = await async_client.get(
            "/api/v1/consents",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["total"] == 0

    @pytest.mark.asyncio
    async def test_consent_not_leaked_to_other_patient(self, async_client, seeded_users, make_token):
        """Another patient cannot see a consent (returns 404, not 403, to avoid existence leak)."""
        patient1_token = make_token("usr-patient-001", "PATIENT")
        patient2_token = make_token("usr-patient-002", "PATIENT")

        create_resp = await async_client.post(
            "/api/v1/consents",
            json={"grantee_id": "usr-doctor-001", "purpose": "care_delivery", "scope": "clinical_records"},
            headers={"Authorization": f"Bearer {patient1_token}"},
        )
        consent_id = create_resp.json()["data"]["id"]

        # Patient 2 tries to access it
        read_resp = await async_client.get(
            f"/api/v1/consents/{consent_id}",
            headers={"Authorization": f"Bearer {patient2_token}"},
        )
        # Must be 404 (not 403) to avoid leaking existence
        assert read_resp.status_code == 404
