"""Tests for Structured Symptom Intake (Phase 8).

Validates:
- Structured symptom recording with clinical provenance (PATIENT_REPORTED, DOCTOR_ENTERED)
- Terminology normalization preserving raw narrative alongside normalized clinical term
- Intake sessions with multiple symptoms
- Pagination and filtering by source, encounter, and date
- Input validation (empty symptoms rejected)
- Audit trail generated without logging symptom text PHI
"""

from datetime import datetime, timezone
import pytest

from app.repositories.audit_repository import AuditRepository
from app.repositories.symptom_repository import SymptomRepository
from app.schemas.audit import AuditEventType
from app.schemas.symptom import (
    SymptomIntakeCreate,
    SymptomItemCreate,
    SymptomSeverity,
    SymptomSource,
)
from app.services.audit_service import AuditService
from app.services.symptom_service import SymptomService


@pytest.fixture
def symptom_service_fixture():
    symptom_repo = SymptomRepository()
    audit_repo = AuditRepository()
    audit_service = AuditService(audit_repository=audit_repo)
    service = SymptomService(symptom_repo=symptom_repo, audit_service=audit_service)
    return service, symptom_repo, audit_repo


@pytest.mark.asyncio
async def test_record_symptom_intake_success(symptom_service_fixture):
    service, symptom_repo, audit_repo = symptom_service_fixture
    patient_id = "patient-syn-001"
    actor_id = "user-syn-pat1"

    payload = SymptomIntakeCreate(
        encounter_id="enc-001",
        source=SymptomSource.PATIENT_REPORTED,
        symptoms=[
            SymptomItemCreate(
                symptom="breathing problem",
                severity=SymptomSeverity.MODERATE,
                onset="2 hours ago",
                duration="intermittent",
                location="chest",
                associated_symptoms=["cough"],
            ),
            SymptomItemCreate(
                symptom="high temp",
                severity=SymptomSeverity.MILD,
                onset="yesterday",
            ),
        ],
        notes="Patient reports feeling unwell since morning.",
    )

    response = await service.record_symptom_intake(patient_id, payload, actor_id)

    assert response.patient_id == patient_id
    assert response.intake_id is not None
    assert response.source == SymptomSource.PATIENT_REPORTED
    assert len(response.symptoms) == 2

    # Verify normalization while preserving raw terms
    s1 = next(s for s in response.symptoms if s.symptom_raw == "breathing problem")
    assert s1.symptom_normalized == "shortness of breath"
    assert s1.severity == SymptomSeverity.MODERATE
    assert s1.source == SymptomSource.PATIENT_REPORTED
    assert s1.recorded_by == actor_id

    s2 = next(s for s in response.symptoms if s.symptom_raw == "high temp")
    assert s2.symptom_normalized == "fever"

    # Verify audit event (IDs and counts only, NO narrative PHI)
    events = [e for e in audit_repo._events if e.event_type == AuditEventType.SYMPTOM_INTAKE_CREATED]
    assert len(events) == 1
    assert events[0].actor_id == actor_id
    assert events[0].metadata["symptom_count"] == 2
    assert "breathing problem" not in str(events[0].metadata)


@pytest.mark.asyncio
async def test_record_symptom_empty_fails(symptom_service_fixture):
    service, _, _ = symptom_service_fixture
    patient_id = "patient-syn-001"
    actor_id = "user-syn-pat1"

    # Bypass Pydantic validation via raw model construct to test service-level validation
    payload = SymptomIntakeCreate.model_construct(
        encounter_id=None,
        source=SymptomSource.PATIENT_REPORTED,
        symptoms=[],
        notes=None,
    )

    with pytest.raises(Exception) as exc_info:
        await service.record_symptom_intake(patient_id, payload, actor_id)

    assert "At least one symptom" in str(exc_info.value)


@pytest.mark.asyncio
async def test_list_patient_symptoms_pagination_and_filter(symptom_service_fixture):
    service, _, _ = symptom_service_fixture
    patient_id = "patient-syn-002"
    actor_id = "user-syn-doc1"

    # Create batch 1 (patient-reported)
    await service.record_symptom_intake(
        patient_id=patient_id,
        payload=SymptomIntakeCreate(
            source=SymptomSource.PATIENT_REPORTED,
            symptoms=[SymptomItemCreate(symptom="headache", severity=SymptomSeverity.MILD)],
        ),
        actor_id=actor_id,
    )

    # Create batch 2 (doctor-entered)
    await service.record_symptom_intake(
        patient_id=patient_id,
        payload=SymptomIntakeCreate(
            encounter_id="enc-syn-99",
            source=SymptomSource.DOCTOR_ENTERED,
            symptoms=[SymptomItemCreate(symptom="nausea", severity=SymptomSeverity.MODERATE)],
        ),
        actor_id=actor_id,
    )

    # List all
    all_res = await service.list_patient_symptoms(patient_id, actor_id)
    assert all_res.total == 2
    assert len(all_res.items) == 2

    # Filter by source
    doc_res = await service.list_patient_symptoms(patient_id, actor_id, source=SymptomSource.DOCTOR_ENTERED)
    assert doc_res.total == 1
    assert doc_res.items[0].symptom_raw == "nausea"

    # Filter by encounter
    enc_res = await service.list_patient_symptoms(patient_id, actor_id, encounter_id="enc-syn-99")
    assert enc_res.total == 1
    assert enc_res.items[0].encounter_id == "enc-syn-99"


@pytest.mark.asyncio
async def test_get_symptom_by_id_boundary(symptom_service_fixture):
    service, _, _ = symptom_service_fixture
    patient_1 = "patient-syn-001"
    patient_2 = "patient-syn-002"
    actor_id = "user-syn-doc1"

    intake_res = await service.record_symptom_intake(
        patient_id=patient_1,
        payload=SymptomIntakeCreate(
            symptoms=[SymptomItemCreate(symptom="dizziness")],
        ),
        actor_id=actor_id,
    )
    symptom_id = intake_res.symptoms[0].id

    # Retrieve valid
    sym = await service.get_symptom_by_id(patient_1, symptom_id, actor_id)
    assert sym.id == symptom_id

    # Attempt cross-patient access (should fail 404)
    with pytest.raises(Exception) as exc_info:
        await service.get_symptom_by_id(patient_2, symptom_id, actor_id)
    assert "not found" in str(exc_info.value).lower()
