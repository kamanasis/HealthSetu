"""Phase 6 tests: Longitudinal patient medications, corrections, and duplicate detection."""

from datetime import datetime, timezone
import pytest
from httpx import AsyncClient

from app.api.deps import _global_authz_service, _global_consent_repo, _global_patient_medication_repo
from app.repositories.consent_repository import ConsentRecord, ConsentStatus
from app.repositories.patient_repository import PatientRecord


@pytest.fixture
def doctor_consent(seeded_patients):
    """Seed active consent and relationship for doctor covering medications and prescriptions."""
    now = datetime.now(timezone.utc)
    c1 = ConsentRecord(
        id="cst-med-001",
        patient_id="usr-patient-001",
        grantee_id="usr-doctor-001",
        purpose="care_delivery",
        scope="prescriptions",
        status=ConsentStatus.ACTIVE,
        granted_at=now,
        effective_from=now,
        expires_at=None,
        version=1,
    )
    c2 = ConsentRecord(
        id="cst-med-002",
        patient_id="usr-patient-001",
        grantee_id="usr-doctor-001",
        purpose="care_delivery",
        scope="medications",
        status=ConsentStatus.ACTIVE,
        granted_at=now,
        effective_from=now,
        expires_at=None,
        version=1,
    )
    _global_consent_repo._consents[c1.id] = c1
    _global_consent_repo._consents[c2.id] = c2
    _global_authz_service.add_relationship("usr-doctor-001", "usr-patient-001")
    return c1


async def test_patient_medication_synchronized_from_prescription(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    doctor_consent,
    make_token,
):
    """Creating a prescription automatically records patient medication in PRESCRIBED state."""
    doc_token = make_token("usr-doctor-001", "DOCTOR")
    payload = {
        "items": [
            {"drug_name_raw": "Amoxicillin", "strength_raw": "500 mg", "frequency_raw": "twice daily"}
        ]
    }
    await async_client.post(
        "/api/v1/patients/pat-001/prescriptions",
        json=payload,
        headers={"Authorization": f"Bearer {doc_token}"},
    )

    # Check patient medication records
    pat_token = make_token("usr-patient-001", "PATIENT")
    res = await async_client.get(
        "/api/v1/patients/pat-001/medications",
        headers={"Authorization": f"Bearer {pat_token}"},
    )
    assert res.status_code == 200
    meds = res.json()["data"]["items"]
    assert len(meds) == 1
    med = meds[0]
    assert med["drug_name_raw"] == "Amoxicillin"
    assert med["status"] == "PRESCRIBED"
    assert med["source"] == "PRESCRIPTION"
    assert med["normalized_info"]["canonical_name"] == "Amoxicillin"
    assert med["normalized_info"]["terminology_code"] == "8640"


async def test_update_patient_medication_status(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    doctor_consent,
    make_token,
):
    """Update patient medication status from PRESCRIBED to ACTIVE or INACTIVE."""
    doc_token = make_token("usr-doctor-001", "DOCTOR")
    payload = {
        "items": [{"drug_name_raw": "Metformin", "strength_raw": "500 mg"}]
    }
    await async_client.post(
        "/api/v1/patients/pat-001/prescriptions",
        json=payload,
        headers={"Authorization": f"Bearer {doc_token}"},
    )

    pat_token = make_token("usr-patient-001", "PATIENT")
    list_res = await async_client.get(
        "/api/v1/patients/pat-001/medications",
        headers={"Authorization": f"Bearer {pat_token}"},
    )
    med_id = list_res.json()["data"]["items"][0]["id"]

    # Transition to ACTIVE
    update_res = await async_client.patch(
        f"/api/v1/patients/pat-001/medications/{med_id}/status",
        json={"status": "ACTIVE", "reason": "Patient started medication therapy"},
        headers={"Authorization": f"Bearer {pat_token}"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["data"]["status"] == "ACTIVE"


async def test_correct_extracted_medication_preserves_original_values(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    doctor_consent,
    make_token,
):
    """Correcting raw extraction updates data, keeps original raw value, and re-normalizes."""
    doc_token = make_token("usr-doctor-001", "DOCTOR")
    # Simulate a typo in prescription extraction
    payload = {
        "items": [{"drug_name_raw": "AmoxcillinTypo", "strength_raw": "500 mg"}]
    }
    await async_client.post(
        "/api/v1/patients/pat-001/prescriptions",
        json=payload,
        headers={"Authorization": f"Bearer {doc_token}"},
    )

    pat_token = make_token("usr-patient-001", "PATIENT")
    list_res = await async_client.get(
        "/api/v1/patients/pat-001/medications",
        headers={"Authorization": f"Bearer {pat_token}"},
    )
    med_id = list_res.json()["data"]["items"][0]["id"]

    # Perform correction to valid drug name
    correct_res = await async_client.patch(
        f"/api/v1/patients/pat-001/medications/{med_id}/correct",
        json={"drug_name": "Amoxicillin", "strength": "500 mg"},
        headers={"Authorization": f"Bearer {pat_token}"},
    )
    assert correct_res.status_code == 200
    data = correct_res.json()["data"]
    assert data["drug_name_raw"] == "Amoxicillin"
    assert data["original_raw_value"] == "AmoxcillinTypo"
    assert data["is_corrected"] is True
    assert data["verification_status"] == "CORRECTED"
    assert data["normalized_info"]["canonical_name"] == "Amoxicillin"
    assert data["normalized_info"]["terminology_code"] == "8640"


async def test_duplicate_medication_flagging_without_clinical_claim(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    doctor_consent,
    make_token,
):
    """Second prescription with same drug flags potential_duplicate=True at data level."""
    doc_token = make_token("usr-doctor-001", "DOCTOR")
    payload1 = {
        "items": [{"drug_name_raw": "Amoxicillin", "strength_raw": "500 mg"}]
    }
    await async_client.post(
        "/api/v1/patients/pat-001/prescriptions",
        json=payload1,
        headers={"Authorization": f"Bearer {doc_token}"},
    )

    payload2 = {
        "items": [{"drug_name_raw": "Amoxicillin", "strength_raw": "500 mg"}]
    }
    await async_client.post(
        "/api/v1/patients/pat-001/prescriptions",
        json=payload2,
        headers={"Authorization": f"Bearer {doc_token}"},
    )

    pat_token = make_token("usr-patient-001", "PATIENT")
    res = await async_client.get(
        "/api/v1/patients/pat-001/medications",
        headers={"Authorization": f"Bearer {pat_token}"},
    )
    meds = res.json()["data"]["items"]
    assert len(meds) == 2
    # The second record created should have potential_duplicate == True
    assert any(m["potential_duplicate"] is True for m in meds)
