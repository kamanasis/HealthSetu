"""Phase 4 tests: Clinical records (history, allergies, vitals, encounters)."""

from datetime import datetime, timezone
import pytest
from httpx import AsyncClient

from app.api.deps import _global_encounter_repo, _global_history_repo
from app.repositories.encounter_repository import EncounterRecord
from app.repositories.patient_repository import PatientRecord
from app.schemas.clinical_history import ClinicalDataSource
from app.schemas.encounter import EncounterStatus, EncounterType


# ---------------------------------------------------------------------------
# Clinical History Tests
# ---------------------------------------------------------------------------

async def test_create_clinical_history_success(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Patient can report a past clinical condition."""
    token = make_token("usr-patient-001", "PATIENT")
    payload = {
        "description": "Hypertension diagnosed 2021",
        "condition_status": "ACTIVE",
        "onset_date": "2021-03-01",
        "source": "PATIENT_ENTERED",
        "notes": "Managed by lifestyle modifications",
    }
    response = await async_client.post(
        "/api/v1/patients/pat-001/history",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["patient_id"] == "pat-001"
    assert data["description"] == payload["description"]
    assert data["condition_status"] == "ACTIVE"
    assert data["is_archived"] is False


async def test_create_clinical_history_invalid_dates(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Resolved date before onset date fails validation."""
    token = make_token("usr-patient-001", "PATIENT")
    payload = {
        "description": "Acute Bronchitis",
        "condition_status": "RESOLVED",
        "onset_date": "2023-05-10",
        "resolved_date": "2023-05-01",  # Invalid: before onset
        "source": "PATIENT_REPORTED",
    }
    response = await async_client.post(
        "/api/v1/patients/pat-001/history",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


async def test_list_clinical_history(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Patient can view their clinical history list."""
    token = make_token("usr-patient-001", "PATIENT")
    # First create an entry
    await async_client.post(
        "/api/v1/patients/pat-001/history",
        json={"description": "Asthma", "condition_status": "ACTIVE"},
        headers={"Authorization": f"Bearer {token}"},
    )
    response = await async_client.get(
        "/api/v1/patients/pat-001/history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["total"] >= 1
    assert any(item["description"] == "Asthma" for item in body["data"]["items"])


async def test_patient_cannot_update_clinical_history(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Patient role cannot update clinical history entries (requires doctor role)."""
    token = make_token("usr-patient-001", "PATIENT")
    create_res = await async_client.post(
        "/api/v1/patients/pat-001/history",
        json={"description": "Type 2 Diabetes", "condition_status": "ACTIVE"},
        headers={"Authorization": f"Bearer {token}"},
    )
    entry_id = create_res.json()["data"]["id"]

    update_res = await async_client.patch(
        f"/api/v1/patients/pat-001/history/{entry_id}",
        json={"condition_status": "RESOLVED"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert update_res.status_code == 403


# ---------------------------------------------------------------------------
# Allergies Tests
# ---------------------------------------------------------------------------

async def test_create_and_list_allergies(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Patient can report an allergy and view their allergy list."""
    token = make_token("usr-patient-001", "PATIENT")
    payload = {
        "allergen": "Penicillin",
        "reaction": "Hives and facial swelling",
        "severity": "SEVERE",
        "status": "ACTIVE",
        "source": "PATIENT_ENTERED",
    }
    create_res = await async_client.post(
        "/api/v1/patients/pat-001/allergies",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_res.status_code == 201
    allergy_id = create_res.json()["data"]["id"]

    # Get single allergy
    get_res = await async_client.get(
        f"/api/v1/patients/pat-001/allergies/{allergy_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_res.status_code == 200
    assert get_res.json()["data"]["allergen"] == "Penicillin"

    # List allergies
    list_res = await async_client.get(
        "/api/v1/patients/pat-001/allergies",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_res.status_code == 200
    assert list_res.json()["data"]["total"] >= 1


async def test_patient_cannot_update_allergy(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Patient role cannot update allergy records."""
    token = make_token("usr-patient-001", "PATIENT")
    create_res = await async_client.post(
        "/api/v1/patients/pat-001/allergies",
        json={"allergen": "Peanuts", "severity": "MODERATE"},
        headers={"Authorization": f"Bearer {token}"},
    )
    allergy_id = create_res.json()["data"]["id"]

    update_res = await async_client.patch(
        f"/api/v1/patients/pat-001/allergies/{allergy_id}",
        json={"status": "INACTIVE"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert update_res.status_code == 403


# ---------------------------------------------------------------------------
# Vitals Tests (append-only)
# ---------------------------------------------------------------------------

async def test_record_vital_success(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Patient can record a valid vital measurement."""
    token = make_token("usr-patient-001", "PATIENT")
    payload = {
        "vital_type": "HEART_RATE",
        "value": 72.0,
        "unit": "bpm",
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "source": "PATIENT_REPORTED",
    }
    response = await async_client.post(
        "/api/v1/patients/pat-001/vitals",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["vital_type"] == "HEART_RATE"
    assert body["data"]["value"] == 72.0
    assert body["data"]["unit"] == "bpm"


async def test_record_vital_invalid_unit_fails_validation(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Mismatched unit for vital type fails validation."""
    token = make_token("usr-patient-001", "PATIENT")
    payload = {
        "vital_type": "HEART_RATE",
        "value": 72.0,
        "unit": "mmHg",  # Invalid unit for heart rate
        "measured_at": datetime.now(timezone.utc).isoformat(),
    }
    response = await async_client.post(
        "/api/v1/patients/pat-001/vitals",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


async def test_list_vitals_with_filter(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Vitals list supports type filtering."""
    token = make_token("usr-patient-001", "PATIENT")
    now_iso = datetime.now(timezone.utc).isoformat()
    # Record HR and Temp
    await async_client.post(
        "/api/v1/patients/pat-001/vitals",
        json={"vital_type": "HEART_RATE", "value": 75.0, "unit": "bpm", "measured_at": now_iso},
        headers={"Authorization": f"Bearer {token}"},
    )
    await async_client.post(
        "/api/v1/patients/pat-001/vitals",
        json={"vital_type": "TEMPERATURE", "value": 37.0, "unit": "celsius", "measured_at": now_iso},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Filter by HEART_RATE
    res = await async_client.get(
        "/api/v1/patients/pat-001/vitals?vital_type=HEART_RATE",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    items = res.json()["data"]["items"]
    assert all(item["vital_type"] == "HEART_RATE" for item in items)


async def test_vitals_no_patch_endpoint(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Vitals are append-only: PATCH method is not allowed."""
    token = make_token("usr-patient-001", "PATIENT")
    response = await async_client.patch(
        "/api/v1/patients/pat-001/vitals/v-123",
        json={"value": 80.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in (404, 405)


# ---------------------------------------------------------------------------
# Encounters Tests
# ---------------------------------------------------------------------------

async def test_patient_cannot_create_encounter(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Patient role cannot create encounters (requires doctor role)."""
    token = make_token("usr-patient-001", "PATIENT")
    now_iso = datetime.now(timezone.utc).isoformat()
    payload = {
        "encounter_type": "OUTPATIENT",
        "status": "PLANNED",
        "start_time": now_iso,
    }
    response = await async_client.post(
        "/api/v1/patients/pat-001/encounters",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_list_encounters_patient_self(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Patient can view their encounters list."""
    token = make_token("usr-patient-001", "PATIENT")
    # Seed an encounter record directly
    now = datetime.now(timezone.utc)
    _global_encounter_repo._records["enc-001"] = EncounterRecord(
        id="enc-001",
        patient_id="pat-001",
        encounter_type=EncounterType.OUTPATIENT,
        status=EncounterStatus.COMPLETED,
        start_time=now,
        source=ClinicalDataSource.SYSTEM_GENERATED,
        created_at=now,
        updated_at=now,
    )

    response = await async_client.get(
        "/api/v1/patients/pat-001/encounters",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["total"] >= 1
    assert body["data"]["items"][0]["id"] == "enc-001"
