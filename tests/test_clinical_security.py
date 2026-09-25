"""Phase 4 tests: Security, PHI confidentiality, and access isolation."""

from datetime import datetime, timezone
import pytest
from httpx import AsyncClient

from app.api.deps import _global_audit_repo, _global_history_repo
from app.repositories.clinical_history_repository import ClinicalHistoryRecord
from app.repositories.patient_repository import PatientRecord
from app.schemas.clinical_history import ClinicalDataSource, ConditionStatus


# ---------------------------------------------------------------------------
# Cross-Patient Isolation Tests (generic 404 to prevent ID enumeration)
# ---------------------------------------------------------------------------

async def test_patient_cannot_access_other_patient_history(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Patient 1 requesting Patient 2's history receives generic 404."""
    token = make_token("usr-patient-001", "PATIENT")
    response = await async_client.get(
        "/api/v1/patients/pat-002/history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["error"]["message"].lower()


async def test_patient_cannot_access_other_patient_allergies(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Patient 1 requesting Patient 2's allergies receives generic 404."""
    token = make_token("usr-patient-001", "PATIENT")
    response = await async_client.get(
        "/api/v1/patients/pat-002/allergies",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["error"]["message"].lower()


async def test_patient_cannot_access_other_patient_vitals(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Patient 1 requesting Patient 2's vitals receives generic 404."""
    token = make_token("usr-patient-001", "PATIENT")
    response = await async_client.get(
        "/api/v1/patients/pat-002/vitals",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["error"]["message"].lower()


async def test_patient_cannot_access_other_patient_encounters(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Patient 1 requesting Patient 2's encounters receives generic 404."""
    token = make_token("usr-patient-001", "PATIENT")
    response = await async_client.get(
        "/api/v1/patients/pat-002/encounters",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["error"]["message"].lower()


# ---------------------------------------------------------------------------
# Least Privilege: Admin Role Isolation
# ---------------------------------------------------------------------------

async def test_admin_cannot_access_patient_history(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Admin role has NO clinical permissions and receives 403."""
    token = make_token("usr-admin-001", "ADMIN")
    response = await async_client.get(
        "/api/v1/patients/pat-001/history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_admin_cannot_access_patient_allergies(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Admin role receives 403 for allergies endpoint."""
    token = make_token("usr-admin-001", "ADMIN")
    response = await async_client.get(
        "/api/v1/patients/pat-001/allergies",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_admin_cannot_access_patient_vitals(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Admin role receives 403 for vitals endpoint."""
    token = make_token("usr-admin-001", "ADMIN")
    response = await async_client.get(
        "/api/v1/patients/pat-001/vitals",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Provider Without Relationship Isolation
# ---------------------------------------------------------------------------

async def test_doctor_cannot_read_history_without_relationship(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Doctor without established relationship receives 403."""
    token = make_token("usr-doctor-001", "DOCTOR")
    response = await async_client.get(
        "/api/v1/patients/pat-001/history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Soft Delete & Immutability Enforcement
# ---------------------------------------------------------------------------

async def test_cannot_update_archived_history_entry(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
):
    """Archived clinical record entries cannot be updated."""
    now = datetime.now(timezone.utc)
    entry = ClinicalHistoryRecord(
        id="hist-archived-001",
        patient_id="pat-001",
        description="Old condition",
        condition_status=ConditionStatus.HISTORICAL,
        source=ClinicalDataSource.PATIENT_ENTERED,
        created_at=now,
        updated_at=now,
        is_archived=True,
    )
    await _global_history_repo.create(entry)

    # Calling clinical record service directly to verify business constraint
    from app.core.exceptions import ValidationException
    from app.schemas.clinical_history import ClinicalHistoryUpdateRequest
    from app.services.clinical_record_service import ClinicalRecordService
    from app.api.deps import _global_allergy_repo, _global_encounter_repo, _global_vitals_repo

    svc = ClinicalRecordService(
        history_repo=_global_history_repo,
        allergy_repo=_global_allergy_repo,
        vitals_repo=_global_vitals_repo,
        encounter_repo=_global_encounter_repo,
    )
    with pytest.raises(ValidationException, match="archived"):
        await svc.update_history_entry(
            patient_id="pat-001",
            entry_id="hist-archived-001",
            actor_id="usr-doctor-001",
            request=ClinicalHistoryUpdateRequest(condition_status=ConditionStatus.RESOLVED),
        )


# ---------------------------------------------------------------------------
# PHI Audit Confidentiality
# ---------------------------------------------------------------------------

async def test_audit_logs_contain_no_phi(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Audit events record action, actor, and patient ID, but NEVER demographic PHI."""
    token = make_token("usr-patient-001", "PATIENT")
    await async_client.patch(
        "/api/v1/patients/pat-001",
        json={"phone": "+919999988888", "preferred_language": "hi"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Inspect all emitted audit events
    for event in _global_audit_repo._events:
        metadata = event.metadata or {}
        # Patient name, phone number, DOB must never appear in audit metadata or event
        assert "+919999988888" not in str(metadata)
        assert "Aarav" not in str(metadata)
        assert "Sharma" not in str(metadata)
        if "updated_fields" in metadata:
            # Only field names (keys), not values
            assert set(metadata["updated_fields"]) == {"phone", "preferred_language"}
