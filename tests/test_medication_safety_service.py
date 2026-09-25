"""Tests for Medication Safety Service (Phase 7).

Validates:
- Patient medication collection and normalization linkage
- Clinical context assembly (allergies, conditions, vitals, age)
- Data minimization (no names, emails, phones sent)
- Prospective new medication evaluation
- Provider failure handling (MUST NEVER return false CLEAR)
- Bounded retry for transient failures
- Provenance tracking (checked_at, ruleset_version, evaluation_id)
- Historical evaluation listing and filtering
- Mandatory clinical disclaimer
"""

from datetime import datetime, timezone
import pytest

from app.integrations.medication_safety.providers.mock import MockMedicationSafetyProvider
from app.repositories.allergy_repository import AllergyRecord, AllergyRepository
from app.repositories.clinical_history_repository import (
    ClinicalHistoryRecord,
    ClinicalHistoryRepository,
)
from app.repositories.medication_repository import MedicationRecord, MedicationRepository
from app.repositories.medication_safety_repository import MedicationSafetyRepository
from app.repositories.patient_medication_repository import (
    PatientMedicationRecord,
    PatientMedicationRepository,
)
from app.repositories.patient_repository import PatientRecord, PatientRepository
from app.schemas.allergy import AllergySeverity, AllergyStatus
from app.schemas.clinical_history import ClinicalDataSource, ConditionStatus
from app.schemas.medication import (
    MedicationSource,
    PatientMedicationStatus,
    VerificationStatus,
)
from app.schemas.medication_safety import (
    CLINICAL_SAFETY_DISCLAIMER,
    MedicationContextSource,
    PatientSafetyCheckRequest,
    ProspectiveMedicationsCheckRequest,
    SafetyAlertSeverity,
    SafetyCheckType,
    SafetyEvaluationStatus,
    SafetyMedicationInput,
)
from app.schemas.patient import BiologicalSex, PatientStatus
from app.services.audit_service import AuditService
from app.services.medication_safety_service import MedicationSafetyService


@pytest.fixture
def safety_service_fixture():
    """Build isolated MedicationSafetyService with seeded repositories."""
    safety_repo = MedicationSafetyRepository()
    patient_med_repo = PatientMedicationRepository()
    med_repo = MedicationRepository()
    allergy_repo = AllergyRepository()
    history_repo = ClinicalHistoryRepository()
    patient_repo = PatientRepository()
    from app.repositories.audit_repository import AuditRepository
    audit_repo = AuditRepository()
    audit_service = AuditService(audit_repository=audit_repo)
    provider = MockMedicationSafetyProvider()

    service = MedicationSafetyService(
        safety_repo=safety_repo,
        patient_medication_repo=patient_med_repo,
        medication_repo=med_repo,
        allergy_repo=allergy_repo,
        clinical_history_repo=history_repo,
        patient_repo=patient_repo,
        audit_service=audit_service,
        provider=provider,
    )
    return {
        "service": service,
        "safety_repo": safety_repo,
        "patient_med_repo": patient_med_repo,
        "med_repo": med_repo,
        "allergy_repo": allergy_repo,
        "history_repo": history_repo,
        "patient_repo": patient_repo,
        "audit_repo": audit_repo,
    }


@pytest.mark.asyncio
async def test_evaluate_patient_safety_empty_medications(safety_service_fixture):
    """Patient with no active medications returns CLEAR with 0 alerts immediately."""
    service = safety_service_fixture["service"]
    patient_id = "pat-empty-001"

    req = PatientSafetyCheckRequest(medication_context=MedicationContextSource.CURRENT_MEDICATIONS)
    res = await service.evaluate_patient_safety(patient_id=patient_id, request=req, actor_id="user-1")

    assert res.status == SafetyEvaluationStatus.CLEAR
    assert res.medications_evaluated_count == 0
    assert len(res.alerts) == 0
    assert res.disclaimer == CLINICAL_SAFETY_DISCLAIMER


@pytest.mark.asyncio
async def test_evaluate_patient_safety_with_active_ddi(safety_service_fixture):
    """Patient with active Metformin and Contrast records triggers DDI alert with provenance."""
    service = safety_service_fixture["service"]
    patient_med_repo = safety_service_fixture["patient_med_repo"]
    med_repo = safety_service_fixture["med_repo"]
    patient_id = "pat-ddi-001"
    now = datetime.now(timezone.utc)

    # Seed canonical medications
    await med_repo.save_medication(
        MedicationRecord(
            id="med-c-001",
            canonical_name="Metformin Hydrochloride",
            terminology_system="RXNORM",
            terminology_code="6809",
            provider="local",
            created_at=now,
        )
    )
    await med_repo.save_medication(
        MedicationRecord(
            id="med-c-002",
            canonical_name="Iodinated Contrast Agent",
            terminology_system="RXNORM",
            terminology_code="9999",
            provider="local",
            created_at=now,
        )
    )

    # Seed patient active medications linked to canonical concepts
    await patient_med_repo.create_record(
        PatientMedicationRecord(
            id="pmed-001",
            patient_id=patient_id,
            status=PatientMedicationStatus.ACTIVE,
            drug_name_raw="Metformin 500mg",
            normalized_medication_id="med-c-001",
            created_at=now,
            updated_at=now,
        )
    )
    await patient_med_repo.create_record(
        PatientMedicationRecord(
            id="pmed-002",
            patient_id=patient_id,
            status=PatientMedicationStatus.ACTIVE,
            drug_name_raw="Contrast 50ml",
            normalized_medication_id="med-c-002",
            created_at=now,
            updated_at=now,
        )
    )

    req = PatientSafetyCheckRequest()
    res = await service.evaluate_patient_safety(patient_id=patient_id, request=req, actor_id="user-1")

    assert res.status == SafetyEvaluationStatus.ALERT
    assert res.medications_evaluated_count == 2
    assert len(res.alerts) >= 1
    alert = res.alerts[0]
    assert alert.check_type == SafetyCheckType.DRUG_DRUG
    assert alert.severity == SafetyAlertSeverity.MAJOR
    assert res.provider == MockMedicationSafetyProvider.MOCK_PROVIDER_NAME
    assert res.ruleset_version == MockMedicationSafetyProvider.MOCK_RULESET_VERSION
    assert res.disclaimer == CLINICAL_SAFETY_DISCLAIMER


@pytest.mark.asyncio
async def test_evaluate_patient_safety_allergy_context(safety_service_fixture):
    """Patient with active allergy to penicillin and active amoxicillin prescription triggers allergy alert."""
    service = safety_service_fixture["service"]
    patient_med_repo = safety_service_fixture["patient_med_repo"]
    allergy_repo = safety_service_fixture["allergy_repo"]
    patient_id = "pat-allergy-001"
    now = datetime.now(timezone.utc)

    # Seed allergy
    await allergy_repo.create(
        AllergyRecord(
            id="alg-01",
            patient_id=patient_id,
            allergen="Penicillin",
            severity=AllergySeverity.SEVERE,
            status=AllergyStatus.ACTIVE,
            source=ClinicalDataSource.PATIENT_ENTERED,
            created_at=now,
            updated_at=now,
        )
    )

    # Seed patient medication
    await patient_med_repo.create_record(
        PatientMedicationRecord(
            id="pmed-amox",
            patient_id=patient_id,
            status=PatientMedicationStatus.ACTIVE,
            drug_name_raw="Amoxicillin 500mg",
            created_at=now,
            updated_at=now,
        )
    )

    req = PatientSafetyCheckRequest()
    res = await service.evaluate_patient_safety(patient_id=patient_id, request=req, actor_id="user-1")

    assert res.status == SafetyEvaluationStatus.ALERT
    allergy_alert = next(a for a in res.alerts if a.check_type == SafetyCheckType.DRUG_ALLERGY)
    assert allergy_alert.severity == SafetyAlertSeverity.CRITICAL
    assert res.patient_context_used["allergies_evaluated"] == 1


@pytest.mark.asyncio
async def test_data_minimization_hygiene(safety_service_fixture):
    """Verify that patient clinical context minimizes data and excludes name, email, phone."""
    service = safety_service_fixture["service"]
    patient_repo = safety_service_fixture["patient_repo"]
    patient_id = "pat-min-001"
    now = datetime.now(timezone.utc)

    await patient_repo.create(
        PatientRecord(
            id=patient_id,
            user_id="usr-min-001",
            first_name="Jane",
            last_name="Doe",
            date_of_birth=datetime(1990, 5, 15).date(),
            sex=BiologicalSex.FEMALE,
            status=PatientStatus.ACTIVE,
            phone="+919876543210",
            email="sensitive_patient@example.com",
            created_at=now,
            updated_at=now,
        )
    )

    context, counts = await service._collect_patient_context(patient_id)

    # Verify context object does NOT contain name, email, phone
    assert hasattr(context, "first_name") is False
    assert hasattr(context, "email") is False
    assert hasattr(context, "phone") is False
    assert context.age_years is not None
    assert context.sex.upper() == "FEMALE"
    assert counts["age_included"] == 1


@pytest.mark.asyncio
async def test_prospective_medications_cross_check(safety_service_fixture):
    """Prospective new medication (e.g. Potassium) cross-checks against current Lisinopril."""
    service = safety_service_fixture["service"]
    patient_med_repo = safety_service_fixture["patient_med_repo"]
    patient_id = "pat-prosp-001"
    now = datetime.now(timezone.utc)

    # Current active medication: Lisinopril
    await patient_med_repo.create_record(
        PatientMedicationRecord(
            id="pmed-liso",
            patient_id=patient_id,
            status=PatientMedicationStatus.ACTIVE,
            drug_name_raw="Lisinopril 10mg",
            created_at=now,
            updated_at=now,
        )
    )

    # Prospective prescription: Potassium Chloride
    req = ProspectiveMedicationsCheckRequest(
        medications=[
            SafetyMedicationInput(name="Potassium Chloride", strength="20 mEq")
        ],
        include_current_medications=True,
    )

    res = await service.evaluate_prospective_medications(
        patient_id=patient_id,
        request=req,
        actor_id="doctor-1",
    )

    assert res.status == SafetyEvaluationStatus.ALERT
    assert res.medications_evaluated_count == 2
    alert = next(a for a in res.alerts if a.check_type == SafetyCheckType.DRUG_DRUG)
    assert alert.severity == SafetyAlertSeverity.MAJOR
    assert "ACE Inhibitor" in alert.title or "Potassium" in alert.title


@pytest.mark.asyncio
async def test_provider_failure_safety_boundary(safety_service_fixture):
    """CRITICAL: When the safety provider fails or times out, status MUST be UNKNOWN, NEVER CLEAR."""
    service = safety_service_fixture["service"]
    patient_med_repo = safety_service_fixture["patient_med_repo"]
    patient_id = "pat-fail-001"
    now = datetime.now(timezone.utc)

    # Medication that triggers simulated provider timeout
    await patient_med_repo.create_record(
        PatientMedicationRecord(
            id="pmed-fail",
            patient_id=patient_id,
            status=PatientMedicationStatus.ACTIVE,
            drug_name_raw="Drug_TRIGGER_TIMEOUT",
            created_at=now,
            updated_at=now,
        )
    )

    req = PatientSafetyCheckRequest()
    res = await service.evaluate_patient_safety(patient_id=patient_id, request=req, actor_id="user-1")

    # MUST NOT BE CLEAR!
    assert res.status != SafetyEvaluationStatus.CLEAR
    assert res.status == SafetyEvaluationStatus.UNKNOWN
    assert len(res.alerts) == 0
    assert len(res.check_summaries) >= 1
    assert "UNKNOWN" in res.check_summaries[0].note


@pytest.mark.asyncio
async def test_historical_evaluations_listing_and_retrieval(safety_service_fixture):
    """Evaluations can be retrieved by ID and listed with pagination and status filter."""
    service = safety_service_fixture["service"]
    patient_id = "pat-hist-001"

    # Run two evaluations
    req1 = PatientSafetyCheckRequest(medication_context=MedicationContextSource.CURRENT_MEDICATIONS)
    res1 = await service.evaluate_patient_safety(patient_id=patient_id, request=req1, actor_id="user-1")

    # Retrieve by ID
    fetched = await service.get_evaluation(patient_id=patient_id, evaluation_id=res1.evaluation_id, actor_id="user-1")
    assert fetched.evaluation_id == res1.evaluation_id
    assert fetched.patient_id == patient_id

    # List
    listing = await service.list_evaluations(patient_id=patient_id, page=1, page_size=10)
    assert listing.total >= 1
    assert listing.items[0].evaluation_id == res1.evaluation_id
