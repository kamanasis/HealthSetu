"""Phase 6 tests: Medication terminology normalization, unit conversions, and disambiguation."""

from datetime import datetime, timezone
import pytest
from httpx import AsyncClient

from app.api.deps import (
    _global_authz_service,
    _global_consent_repo,
    _global_medication_repo,
    _global_prescription_repo,
)
from app.integrations.medication.base import RawMedicationInput
from app.integrations.medication.providers.local import (
    LocalMedicationProvider,
    normalize_dosage_form,
    normalize_route,
    normalize_strength,
)
from app.repositories.consent_repository import ConsentRecord, ConsentStatus
from app.repositories.patient_repository import PatientRecord
from app.schemas.prescription import NormalizationStatus


@pytest.fixture
def doctor_consent(seeded_patients):
    """Seed active consent and relationship for doctor on patient pat-001 covering prescriptions."""
    now = datetime.now(timezone.utc)
    consent = ConsentRecord(
        id="cst-presc-norm-001",
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
    _global_consent_repo._consents[consent.id] = consent
    _global_authz_service.add_relationship("usr-doctor-001", "usr-patient-001")
    return consent


def test_unit_and_strength_normalization():
    """Verify data-level strength normalization without clinical interpretation."""
    assert normalize_strength("0.5 g") == "500 mg"
    assert normalize_strength("0.5g") == "500 mg"
    assert normalize_strength("1 g") == "1000 mg"
    assert normalize_strength("1000 mcg") == "1 mg"
    assert normalize_strength("500mg") == "500 mg"
    assert normalize_strength("10 mg") == "10 mg"
    assert normalize_strength("5ml") == "5 mL"
    assert normalize_strength(None) is None


def test_dosage_form_normalization():
    """Verify dosage form standardization."""
    assert normalize_dosage_form("tab") == "tablet"
    assert normalize_dosage_form("tabs") == "tablet"
    assert normalize_dosage_form("cap") == "capsule"
    assert normalize_dosage_form("syr") == "syrup"
    assert normalize_dosage_form("inj") == "injection"
    assert normalize_dosage_form("cream") == "cream"
    assert normalize_dosage_form(None) is None


def test_route_normalization():
    """Verify route standardization."""
    assert normalize_route("po") == "oral"
    assert normalize_route("oral") == "oral"
    assert normalize_route("by mouth") == "oral"
    assert normalize_route("iv") == "intravenous"
    assert normalize_route("im") == "intramuscular"
    assert normalize_route(None) is None


@pytest.mark.asyncio
async def test_local_provider_matched_concept():
    """Provider returns MATCHED concept with canonical name and RxNorm code."""
    provider = LocalMedicationProvider()
    inp = RawMedicationInput(drug_name_raw="Paracetamol", strength_raw="0.5 g")
    res = await provider.normalize(inp)
    assert res.status == NormalizationStatus.MATCHED
    assert res.concept is not None
    assert res.concept.canonical_name == "Acetaminophen"
    assert res.concept.terminology_code == "161"
    assert res.concept.normalized_strength == "500 mg"


@pytest.mark.asyncio
async def test_local_provider_ambiguous_concept_does_not_guess():
    """Ambiguous medication name returns AMBIGUOUS status with candidate matches."""
    provider = LocalMedicationProvider()
    inp = RawMedicationInput(drug_name_raw="Metro")
    res = await provider.normalize(inp)
    assert res.status == NormalizationStatus.AMBIGUOUS
    assert res.concept is None
    assert "Metronidazole" in res.potential_matches
    assert "Metoprolol" in res.potential_matches


@pytest.mark.asyncio
async def test_local_provider_unmatched_concept():
    """Unrecognized medication name returns UNMATCHED status."""
    provider = LocalMedicationProvider()
    inp = RawMedicationInput(drug_name_raw="NonExistentDrug12345")
    res = await provider.normalize(inp)
    assert res.status == NormalizationStatus.UNMATCHED
    assert res.concept is None


@pytest.mark.asyncio
async def test_local_provider_simulated_failure():
    """Simulated provider failure returns FAILED status with error metadata."""
    provider = LocalMedicationProvider()
    inp = RawMedicationInput(drug_name_raw="SimulateFailure")
    res = await provider.normalize(inp)
    assert res.status == NormalizationStatus.FAILED
    assert res.error_code == "TERMINOLOGY_PROVIDER_UNAVAILABLE"


@pytest.mark.asyncio
async def test_idempotent_normalization_endpoint(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    doctor_consent,
    make_token,
):
    """Calling normalize multiple times produces identical results without duplicating concepts."""
    token = make_token("usr-doctor-001", "DOCTOR")
    payload = {
        "items": [
            {"drug_name_raw": "Amoxicillin", "strength_raw": "500 mg"},
            {"drug_name_raw": "Metro", "strength_raw": "250 mg"},
        ]
    }
    create_res = await async_client.post(
        "/api/v1/patients/pat-001/prescriptions",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    presc_id = create_res.json()["data"]["id"]

    # First manual normalize call
    norm_res1 = await async_client.post(
        f"/api/v1/patients/pat-001/prescriptions/{presc_id}/normalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert norm_res1.status_code == 200
    data1 = norm_res1.json()["data"]
    assert data1["matched_count"] == 1
    assert data1["ambiguous_count"] == 1

    # Second manual normalize call (idempotent)
    norm_res2 = await async_client.post(
        f"/api/v1/patients/pat-001/prescriptions/{presc_id}/normalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert norm_res2.status_code == 200
    data2 = norm_res2.json()["data"]
    assert data2["matched_count"] == 1
    assert data2["ambiguous_count"] == 1
    assert data1["items"][0]["normalized_medication_id"] == data2["items"][0]["normalized_medication_id"]
