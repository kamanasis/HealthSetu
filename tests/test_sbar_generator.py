"""Tests for SBAR Clinical Communication Generator (Phase 8).

Validates:
- Deterministic SBAR generation (Situation, Background, Assessment, Recommendation)
- Accurate linkage to authoritative triage assessment
- SBAR plain text formatting
- AI provider adapter integration
- Fact validator rejecting hallucinated diagnoses and medications
- Urgency mismatch detection preventing AI override of triage results
- Safe fallback to deterministic template when AI validation fails
- Audit events for SBAR creation, viewing, and regeneration
"""

from datetime import datetime, timezone
import pytest

from app.integrations.ai.base import SBARInputFacts
from app.integrations.ai.providers.mock_llm import MockLLMClinicalTextGenerator
from app.integrations.ai.providers.template_generator import TemplateClinicalTextGenerator
from app.integrations.ai.validator import SBARFactValidator
from app.repositories.audit_repository import AuditRepository
from app.repositories.clinical_history_repository import (
    ClinicalHistoryRecord,
    ClinicalHistoryRepository,
)
from app.repositories.patient_medication_repository import (
    PatientMedicationRecord,
    PatientMedicationRepository,
)
from app.repositories.sbar_repository import SBARRepository
from app.repositories.triage_repository import TriageRepository
from app.schemas.audit import AuditEventType
from app.schemas.clinical_history import ClinicalDataSource, ConditionStatus
from app.schemas.medication import (
    MedicationSource,
    PatientMedicationStatus,
    VerificationStatus,
)
from app.schemas.sbar import (
    SBARCreate,
    SBARGenerationMode,
)
from app.schemas.triage import (
    MissingInformationItem,
    TRIAGE_CLINICAL_DISCLAIMER,
    TriageAssessmentRecord,
    TriageExplanation,
    TriageReason,
    TriageStatus,
    TriageUrgency,
)
from app.services.audit_service import AuditService
from app.services.sbar_service import SBARService


@pytest.fixture
def sbar_service_fixture():
    sbar_repo = SBARRepository()
    triage_repo = TriageRepository()
    history_repo = ClinicalHistoryRepository()
    med_repo = PatientMedicationRepository()
    audit_repo = AuditRepository()
    audit_service = AuditService(audit_repository=audit_repo)

    template_gen = TemplateClinicalTextGenerator()
    ai_gen = MockLLMClinicalTextGenerator()
    validator = SBARFactValidator()

    service = SBARService(
        sbar_repo=sbar_repo,
        triage_repo=triage_repo,
        audit_service=audit_service,
        template_generator=template_gen,
        ai_generator=ai_gen,
        validator=validator,
        clinical_history_repo=history_repo,
        patient_medication_repo=med_repo,
    )
    return service, sbar_repo, triage_repo, history_repo, med_repo, audit_repo


@pytest.mark.asyncio
async def test_sbar_deterministic_generation(sbar_service_fixture):
    """Test standard deterministic template SBAR generation."""
    service, _, triage_repo, history_repo, med_repo, audit_repo = sbar_service_fixture
    patient_id = "patient-syn-sbar1"
    actor_id = "user-syn-doc1"
    assessment_id = "assess-syn-001"

    # Seed patient clinical history (Hypertension)
    now = datetime.now(timezone.utc)
    cond = ClinicalHistoryRecord(
        id="cond-01",
        patient_id=patient_id,
        description="Hypertension",
        source=ClinicalDataSource.PATIENT_ENTERED,
        condition_status=ConditionStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    await history_repo.create(cond)

    # Seed patient medication (Amlodipine 5mg)
    med = PatientMedicationRecord(
        id="med-01",
        patient_id=patient_id,
        drug_name_raw="Amlodipine 5mg",
        source=MedicationSource.PATIENT_REPORTED,
        status=PatientMedicationStatus.ACTIVE,
        verification_status=VerificationStatus.VERIFIED,
        created_at=now,
        updated_at=now,
    )
    await med_repo.create_record(med)

    # Seed triage assessment
    assessment = TriageAssessmentRecord(
        id=assessment_id,
        patient_id=patient_id,
        urgency=TriageUrgency.URGENT,
        status=TriageStatus.COMPLETED,
        reasons=[
            TriageReason(
                rule_id="RULE_URGENT_SEVERE_HYPERTENSION",
                reason_code="RULE_URGENT_BP_STAGE_3",
                description="Severe blood pressure elevation requires urgent physician evaluation.",
                source="HealthSetu Clinical Protocol",
                urgency_assigned=TriageUrgency.URGENT,
            )
        ],
        missing_information=[
            MissingInformationItem(field="heart_rate", importance="RECOMMENDED", description="Pulse rate")
        ],
        rule_set="HealthSetu Clinical Protocol",
        rule_set_version="1.0.0",
        explanation=TriageExplanation(
            summary="Triage urgent evaluation completed",
            factors_considered=["Symptom: headache (Severity: SEVERE)"],
            urgency_rationale="Markedly elevated blood pressure",
            recommended_level_of_care="Urgent Care Clinic",
            disclaimer=TRIAGE_CLINICAL_DISCLAIMER,
        ),
        immediate_instruction="Seek medical attention within several hours.",
        assessed_at=now,
        created_at=now,
    )
    await triage_repo.create(assessment)

    # Generate SBAR
    payload = SBARCreate(
        assessment_id=assessment_id,
        generation_mode=SBARGenerationMode.TEMPLATE,
    )
    sbar_res = await service.generate_sbar(patient_id, payload, actor_id)

    assert sbar_res.assessment_id == assessment_id
    assert sbar_res.generation_mode == SBARGenerationMode.TEMPLATE
    assert sbar_res.situation.current_urgency == TriageUrgency.URGENT
    assert "headache" in sbar_res.situation.summary_text
    assert "Hypertension" in sbar_res.background.summary_text
    assert "Amlodipine" in sbar_res.background.summary_text
    assert "heart_rate" in sbar_res.recommendation.missing_information
    assert "SBAR CLINICAL SUMMARY" in sbar_res.plain_text

    # Verify audit event
    created_events = [e for e in audit_repo._events if e.event_type == AuditEventType.SBAR_CREATED]
    assert len(created_events) == 1
    assert created_events[0].metadata["assessment_id"] == assessment_id


@pytest.mark.asyncio
async def test_sbar_fact_validator_rejects_hallucinations(sbar_service_fixture):
    """Fact validator flags ungrounded diagnosis or medication hallucinated by LLM."""
    validator = SBARFactValidator()
    facts = SBARInputFacts(
        patient_id="pat-1",
        urgency=TriageUrgency.EMERGENCY,
        reason_for_attention="Severe chest discomfort",
        presenting_symptoms=["chest pain"],
        known_conditions=["Hypertension"],
        active_medications=["Metoprolol 25mg"],
        recommended_level_of_care="Emergency Department",
        follow_up_recommendation="ECG and cardiac troponin",
    )

    # 1. Simulate LLM attempting to assign autonomous diagnosis "has a heart attack"
    flawed_gen = MockLLMClinicalTextGenerator(simulate_hallucination=True)
    flawed_output = await flawed_gen.generate_sbar(facts)

    val_result = validator.validate(facts, flawed_output)
    assert not val_result.is_valid
    assert any("Autonomous diagnosis detected" in err for err in val_result.validation_errors)
    assert any("Hallucinated medication detected" in err for err in val_result.validation_errors)


@pytest.mark.asyncio
async def test_sbar_fact_validator_rejects_urgency_override(sbar_service_fixture):
    """Fact validator rejects LLM attempt to change authoritative urgency."""
    validator = SBARFactValidator()
    facts = SBARInputFacts(
        patient_id="pat-1",
        urgency=TriageUrgency.EMERGENCY,
        reason_for_attention="Severe chest discomfort",
        presenting_symptoms=["chest pain"],
        recommended_level_of_care="Emergency Department",
        follow_up_recommendation="Immediate evaluation",
    )

    # Simulate LLM overriding urgency from EMERGENCY to ROUTINE
    override_gen = MockLLMClinicalTextGenerator(simulate_urgency_override=True)
    override_output = await override_gen.generate_sbar(facts)

    val_result = validator.validate(facts, override_output)
    assert not val_result.is_valid
    assert any("Urgency mismatch" in err for err in val_result.validation_errors)


@pytest.mark.asyncio
async def test_sbar_service_fallback_on_ai_validation_failure(sbar_service_fixture):
    """When AI fails validation, SBARService falls back cleanly to deterministic template."""
    service, _, triage_repo, _, _, _ = sbar_service_fixture
    patient_id = "patient-syn-fall"
    actor_id = "user-syn-doc1"
    assessment_id = "assess-syn-fall"

    now = datetime.now(timezone.utc)
    assessment = TriageAssessmentRecord(
        id=assessment_id,
        patient_id=patient_id,
        urgency=TriageUrgency.EMERGENCY,
        status=TriageStatus.COMPLETED,
        reasons=[
            TriageReason(
                rule_id="RULE_RED_HYPOXIA",
                reason_code="RULE_RED_CRITICAL_SPO2",
                description="Hypoxia detected.",
                source="HealthSetu Protocol",
                urgency_assigned=TriageUrgency.EMERGENCY,
            )
        ],
        rule_set="HealthSetu Protocol",
        rule_set_version="1.0.0",
        explanation=TriageExplanation(
            summary="Emergency evaluation",
            factors_considered=["Symptom: dyspnea"],
            urgency_rationale="Low oxygen saturation",
            recommended_level_of_care="Emergency Department",
            disclaimer=TRIAGE_CLINICAL_DISCLAIMER,
        ),
        assessed_at=now,
        created_at=now,
    )
    await triage_repo.create(assessment)

    # Force AI generator to produce hallucination
    service.ai_generator = MockLLMClinicalTextGenerator(simulate_hallucination=True)

    # Request AI mode
    payload = SBARCreate(
        assessment_id=assessment_id,
        generation_mode=SBARGenerationMode.AI,
    )
    res = await service.generate_sbar(patient_id, payload, actor_id)

    # SBAR service should fall back to TEMPLATE
    assert res.generation_mode == SBARGenerationMode.TEMPLATE
    assert res.situation.current_urgency == TriageUrgency.EMERGENCY


@pytest.mark.asyncio
async def test_sbar_regeneration_audit(sbar_service_fixture):
    """Regenerating SBAR for an assessment triggers SBAR_REGENERATED audit."""
    service, _, triage_repo, _, _, audit_repo = sbar_service_fixture
    patient_id = "patient-syn-regen"
    actor_id = "user-syn-doc1"
    assessment_id = "assess-syn-regen"

    now = datetime.now(timezone.utc)
    assessment = TriageAssessmentRecord(
        id=assessment_id,
        patient_id=patient_id,
        urgency=TriageUrgency.ROUTINE,
        status=TriageStatus.COMPLETED,
        reasons=[],
        rule_set="HealthSetu Protocol",
        rule_set_version="1.0.0",
        explanation=TriageExplanation(
            summary="Routine check",
            factors_considered=["Symptom: mild rash"],
            urgency_rationale="Minor rash",
            recommended_level_of_care="Primary Care",
            disclaimer=TRIAGE_CLINICAL_DISCLAIMER,
        ),
        assessed_at=now,
        created_at=now,
    )
    await triage_repo.create(assessment)

    payload = SBARCreate(assessment_id=assessment_id)

    # First generation
    res1 = await service.generate_sbar(patient_id, payload, actor_id)
    # Second generation (regeneration)
    res2 = await service.generate_sbar(patient_id, payload, actor_id)

    assert res1.sbar_id != res2.sbar_id

    regen_events = [e for e in audit_repo._events if e.event_type == AuditEventType.SBAR_REGENERATED]
    assert len(regen_events) == 1
    assert regen_events[0].metadata["previous_sbar_id"] == res1.sbar_id
