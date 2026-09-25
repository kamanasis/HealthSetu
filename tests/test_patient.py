"""Phase 4 tests: Patient profile and clinical summary endpoints."""

import pytest
from httpx import AsyncClient

from app.api.deps import _global_patient_repo
from app.repositories.patient_repository import PatientRecord
from app.schemas.patient import PatientStatus


# ---------------------------------------------------------------------------
# Patient Profile Tests
# ---------------------------------------------------------------------------

async def test_get_patient_profile_self_success(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Patient can successfully view their own demographic profile."""
    token = make_token("usr-patient-001", "PATIENT")
    response = await async_client.get(
        "/api/v1/patients/pat-001",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["id"] == "pat-001"
    assert body["data"]["first_name"] == "Aarav"
    assert body["data"]["last_name"] == "Sharma"
    assert body["data"]["sex"] == "MALE"
    assert body["data"]["phone"] == "+919876543210"


async def test_get_patient_profile_other_returns_404(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Patient requesting another patient's profile receives 404 (preventing enumeration)."""
    token = make_token("usr-patient-001", "PATIENT")
    response = await async_client.get(
        "/api/v1/patients/pat-002",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert "not found" in body["error"]["message"].lower()


async def test_get_patient_profile_unauthenticated_returns_401(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
):
    """Unauthenticated request is rejected with 401."""
    response = await async_client.get("/api/v1/patients/pat-001")
    assert response.status_code == 401


async def test_get_patient_profile_nonexistent_returns_404(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Non-existent patient returns 404."""
    token = make_token("usr-patient-001", "PATIENT")
    response = await async_client.get(
        "/api/v1/patients/nonexistent-id",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


async def test_get_patient_profile_inactive_returns_404(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Inactive patient record returns 404 to avoid leaking existence."""
    # Mark pat-001 as INACTIVE
    record = _global_patient_repo._patients["pat-001"]
    _global_patient_repo._patients["pat-001"] = PatientRecord(
        id=record.id,
        user_id=record.user_id,
        first_name=record.first_name,
        last_name=record.last_name,
        date_of_birth=record.date_of_birth,
        sex=record.sex,
        status=PatientStatus.INACTIVE,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
    token = make_token("usr-patient-001", "PATIENT")
    response = await async_client.get(
        "/api/v1/patients/pat-001",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


async def test_doctor_access_patient_profile_without_relationship_returns_403(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Doctor without active provider-patient relationship receives 403."""
    token = make_token("usr-doctor-001", "DOCTOR")
    response = await async_client.get(
        "/api/v1/patients/pat-001",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_admin_access_patient_profile_returns_403(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Admin role has no clinical access and receives 403."""
    token = make_token("usr-admin-001", "ADMIN")
    response = await async_client.get(
        "/api/v1/patients/pat-001",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_update_patient_profile_self_success(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Patient can update permitted demographic fields."""
    token = make_token("usr-patient-001", "PATIENT")
    update_payload = {
        "preferred_language": "hi",
        "phone": "+919999999999",
    }
    response = await async_client.patch(
        "/api/v1/patients/pat-001",
        json=update_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["preferred_language"] == "hi"
    assert body["data"]["phone"] == "+919999999999"
    # Unchanged fields remain preserved
    assert body["data"]["first_name"] == "Aarav"
    assert body["data"]["last_name"] == "Sharma"


async def test_update_patient_profile_other_returns_404(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Patient attempting to update another patient's profile gets 404."""
    token = make_token("usr-patient-001", "PATIENT")
    response = await async_client.patch(
        "/api/v1/patients/pat-002",
        json={"preferred_language": "fr"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


async def test_update_patient_profile_doctor_returns_403(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Doctor attempting to update patient profile is forbidden."""
    token = make_token("usr-doctor-001", "DOCTOR")
    response = await async_client.patch(
        "/api/v1/patients/pat-001",
        json={"preferred_language": "fr"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_update_patient_profile_validation_error(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Invalid update payload (e.g. empty first_name) fails validation."""
    token = make_token("usr-patient-001", "PATIENT")
    response = await async_client.patch(
        "/api/v1/patients/pat-001",
        json={"first_name": ""},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Clinical Summary Tests
# ---------------------------------------------------------------------------

async def test_get_clinical_summary_self_success(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Patient can retrieve their clinical summary."""
    token = make_token("usr-patient-001", "PATIENT")
    response = await async_client.get(
        "/api/v1/patients/pat-001/clinical-summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["patient"]["id"] == "pat-001"
    assert data["patient"]["first_name"] == "Aarav"
    assert "active_conditions" in data
    assert "known_allergies" in data
    assert "recent_vitals" in data
    assert "active_encounters" in data
    assert "summary_generated_at" in data


async def test_get_clinical_summary_other_patient_returns_404(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Patient requesting another's clinical summary gets 404."""
    token = make_token("usr-patient-001", "PATIENT")
    response = await async_client.get(
        "/api/v1/patients/pat-002/clinical-summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


async def test_get_clinical_summary_admin_returns_403(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Admin requesting clinical summary gets 403."""
    token = make_token("usr-admin-001", "ADMIN")
    response = await async_client.get(
        "/api/v1/patients/pat-001/clinical-summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
