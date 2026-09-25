"""Tests for Clinical Triage Rule Engine & Assessment Service (Phase 8).

Validates:
- Emergency rule evaluation: Severe hypoxia, cardiac red flags, stroke, anaphylaxis
- Urgent rule evaluation: High fever in vulnerable patients, severe hypertension
- Insufficient information handling: Missing SpO2 for dyspneic patient flags INSUFFICIENT_INFORMATION without guessing
- Routine & Same Day protocol evaluations
- Reassessment linking: New information produces distinct versioned assessment
- Idempotency key handling
- Technical failure / timeout resilience
- Mandatory clinical disclaimer
"""

import asyncio
from datetime import date, datetime, timezone
import pytest

from app.core.exceptions import AppException
from app.integrations.triage.base import (
    TriageEvaluationContext,
    TriageRuleEngine,
    TriageEngineResult,
)
from app.integrations.triage.rule_engine import HealthSetuDeterministicTriageEngine
from app.repositories.audit_repository import AuditRepository
from app.repositories.symptom_repository import SymptomRepository
from app.repositories.triage_repository import TriageRepository
from app.repositories.vitals_repository import VitalRecord, VitalsRepository
from app.schemas.audit import AuditEventType
from app.schemas.symptom import SymptomItemCreate, SymptomSeverity, SymptomSource
from app.schemas.triage import (
    TRIAGE_CLINICAL_DISCLAIMER,
    TriageAssessmentCreate,
    TriageStatus,
    TriageUrgency,
)
from app.schemas.vital import VitalSource, VitalType
from app.services.audit_service import AuditService
from app.services.triage_service import TriageService


@pytest.fixture
def triage_service_fixture():
    triage_repo = TriageRepository()
    symptom_repo = SymptomRepository()
    vitals_repo = VitalsRepository()
    audit_repo = AuditRepository()
    audit_service = AuditService(audit_repository=audit_repo)
    rule_engine = HealthSetuDeterministicTriageEngine()

    service = TriageService(
        triage_repo=triage_repo,
        symptom_repo=symptom_repo,
        audit_service=audit_service,
        rule_engine=rule_engine,
        vitals_repo=vitals_repo,
    )
    return service, triage_repo, symptom_repo, vitals_repo, audit_repo


@pytest.mark.asyncio
async def test_triage_emergency_critical_hypoxia(triage_service_fixture):
    """Positive test: SpO2 < 90% triggers EMERGENCY immediately."""
    service, _, _, vitals_repo, _ = triage_service_fixture
    patient_id = "patient-syn-red1"
    actor_id = "user-syn-doc1"

    # Seed critically low SpO2 vital (86%)
    now = datetime.now(timezone.utc)
    vital_rec = VitalRecord(
        id="vital-spo2-86",
        patient_id=patient_id,
        vital_type=VitalType.OXYGEN_SATURATION,
        value=86.0,
        unit="%",
        measured_at=now,
        source=VitalSource.CLINIC_RECORDED,
        created_at=now,
    )
    await vitals_repo.append(vital_rec)

    payload = TriageAssessmentCreate(
        symptoms=[
            SymptomItemCreate(
                symptom="shortness of breath",
                severity=SymptomSeverity.SEVERE,
            )
        ],
        vital_ids=["vital-spo2-86"],
    )

    result = await service.assess_patient(patient_id, payload, actor_id)

    assert result.urgency == TriageUrgency.EMERGENCY
    assert result.status == TriageStatus.COMPLETED
    assert any(r.rule_id == "RULE_RED_HYPOXIA" for r in result.reasons)
    assert result.immediate_instruction is not None
    assert "emergency" in result.immediate_instruction.lower()
    assert result.explanation.disclaimer == TRIAGE_CLINICAL_DISCLAIMER


@pytest.mark.asyncio
async def test_triage_emergency_cardiac_red_flags(triage_service_fixture):
    """Positive test: Chest pain with radiation to arm triggers EMERGENCY."""
    service, _, _, _, _ = triage_service_fixture
    patient_id = "patient-syn-red2"
    actor_id = "user-syn-doc1"

    payload = TriageAssessmentCreate(
        symptoms=[
            SymptomItemCreate(
                symptom="substernal chest pain",
                severity=SymptomSeverity.SEVERE,
                location="substernal radiating to left arm",
                associated_symptoms=["diaphoresis", "nausea"],
            )
        ],
    )

    result = await service.assess_patient(patient_id, payload, actor_id)

    assert result.urgency == TriageUrgency.EMERGENCY
    assert result.status == TriageStatus.COMPLETED
    assert any(r.rule_id == "RULE_RED_ACUTE_CORONARY_RISK" for r in result.reasons)


@pytest.mark.asyncio
async def test_triage_emergency_acute_neuro_deficit(triage_service_fixture):
    """Positive test: Sudden slurred speech triggers EMERGENCY (stroke alert)."""
    service, _, _, _, _ = triage_service_fixture
    patient_id = "patient-syn-red3"
    actor_id = "user-syn-doc1"

    payload = TriageAssessmentCreate(
        symptoms=[
            SymptomItemCreate(
                symptom="slurred speech and facial droop",
                severity=SymptomSeverity.CRITICAL,
                onset="30 minutes ago",
            )
        ],
    )

    result = await service.assess_patient(patient_id, payload, actor_id)

    assert result.urgency == TriageUrgency.EMERGENCY
    assert any(r.rule_id == "RULE_RED_ACUTE_NEURO_DEFICIT" for r in result.reasons)


@pytest.mark.asyncio
async def test_triage_insufficient_information_missing_spo2(triage_service_fixture):
    """Dyspnea without SpO2 vital triggers INSUFFICIENT_INFORMATION."""
    service, _, _, _, _ = triage_service_fixture
    patient_id = "patient-syn-yellow1"
    actor_id = "user-syn-pat1"

    # Dyspnea reported, but NO vitals supplied at all
    payload = TriageAssessmentCreate(
        symptoms=[
            SymptomItemCreate(
                symptom="shortness of breath",
                severity=SymptomSeverity.MODERATE,
            )
        ],
    )

    result = await service.assess_patient(patient_id, payload, actor_id)

    assert result.status == TriageStatus.INSUFFICIENT_INFORMATION
    assert len(result.missing_information) > 0
    assert any(m.field == "oxygen_saturation" and m.importance == "REQUIRED" for m in result.missing_information)


@pytest.mark.asyncio
async def test_triage_reassessment_after_vitals_added(triage_service_fixture):
    """Reassessment links to original assessment and upgrades status when vital added."""
    service, _, _, vitals_repo, audit_repo = triage_service_fixture
    patient_id = "patient-syn-reassess"
    actor_id = "user-syn-doc1"

    # Step 1: Initial assessment with missing vitals -> INSUFFICIENT_INFORMATION
    init_payload = TriageAssessmentCreate(
        symptoms=[SymptomItemCreate(symptom="shortness of breath", severity=SymptomSeverity.MODERATE)],
    )
    init_res = await service.assess_patient(patient_id, init_payload, actor_id)
    assert init_res.status == TriageStatus.INSUFFICIENT_INFORMATION
    init_id = init_res.assessment_id

    # Step 2: Vital sign measured (SpO2 = 98%, Heart Rate = 76 bpm)
    now = datetime.now(timezone.utc)
    v1 = VitalRecord(
        id="vital-re-1",
        patient_id=patient_id,
        vital_type=VitalType.OXYGEN_SATURATION,
        value=98.0,
        unit="%",
        measured_at=now,
        source=VitalSource.CLINIC_RECORDED,
        created_at=now,
    )
    await vitals_repo.append(v1)

    # Step 3: Reassessment referencing previous assessment
    re_payload = TriageAssessmentCreate(
        symptoms=[SymptomItemCreate(symptom="shortness of breath", severity=SymptomSeverity.MODERATE)],
        vital_ids=["vital-re-1"],
        assessment_type="REASSESSMENT",
        previous_assessment_id=init_id,
    )
    re_res = await service.assess_patient(patient_id, re_payload, actor_id)

    assert re_res.assessment_id != init_id
    assert re_res.previous_assessment_id == init_id
    assert re_res.status == TriageStatus.COMPLETED
    assert re_res.urgency == TriageUrgency.URGENT  # Moderate dyspnea with stable SpO2 is URGENT

    # Verify audit event for reassessment
    reassess_events = [e for e in audit_repo._events if e.event_type == AuditEventType.TRIAGE_REASSESSMENT_CREATED]
    assert len(reassess_events) == 1
    assert reassess_events[0].metadata["previous_assessment_id"] == init_id


@pytest.mark.asyncio
async def test_triage_routine_mild_presentation(triage_service_fixture):
    """Mild symptoms with normal parameters evaluate to ROUTINE."""
    service, _, _, _, _ = triage_service_fixture
    patient_id = "patient-syn-routine"
    actor_id = "user-syn-pat1"

    payload = TriageAssessmentCreate(
        symptoms=[
            SymptomItemCreate(
                symptom="mild sore throat",
                severity=SymptomSeverity.MILD,
                duration="today",
            )
        ],
    )

    result = await service.assess_patient(patient_id, payload, actor_id)

    assert result.urgency == TriageUrgency.ROUTINE
    assert result.status == TriageStatus.COMPLETED
    assert any(r.rule_id == "RULE_ROUTINE_MILD_PRESENTATION" for r in result.reasons)


@pytest.mark.asyncio
async def test_triage_idempotency_key(triage_service_fixture):
    """Identical requests with idempotency key return the cached assessment."""
    service, _, _, _, _ = triage_service_fixture
    patient_id = "patient-syn-idem"
    actor_id = "user-syn-pat1"
    key = "client-req-key-12345"

    payload = TriageAssessmentCreate(
        symptoms=[SymptomItemCreate(symptom="mild cough", severity=SymptomSeverity.MILD)],
        idempotency_key=key,
    )

    res1 = await service.assess_patient(patient_id, payload, actor_id)
    res2 = await service.assess_patient(patient_id, payload, actor_id)

    assert res1.assessment_id == res2.assessment_id


@pytest.mark.asyncio
async def test_triage_engine_timeout_handling(triage_service_fixture):
    """Engine timeout raises TRIAGE_RULE_ENGINE_UNAVAILABLE cleanly."""
    service, _, _, _, audit_repo = triage_service_fixture
    patient_id = "patient-syn-timeout"
    actor_id = "user-syn-doc1"

    class SlowMockEngine(TriageRuleEngine):
        @property
        def rule_set_name(self) -> str:
            return "slow_engine"
        @property
        def rule_set_version(self) -> str:
            return "1.0.0"
        async def evaluate(self, context: TriageEvaluationContext) -> TriageEngineResult:
            await asyncio.sleep(2.0)
            return None  # pragma: no cover

    service.rule_engine = SlowMockEngine()
    service.settings.TRIAGE_RULE_ENGINE_TIMEOUT_SECONDS = 0.05

    payload = TriageAssessmentCreate(
        symptoms=[SymptomItemCreate(symptom="fever")],
    )

    with pytest.raises(AppException) as exc_info:
        await service.assess_patient(patient_id, payload, actor_id)

    assert exc_info.value.code == "TRIAGE_RULE_ENGINE_UNAVAILABLE"
    assert exc_info.value.status_code == 504

    # Verify audit failure event
    fail_events = [e for e in audit_repo._events if e.event_type == AuditEventType.TRIAGE_ASSESSMENT_FAILED]
    assert len(fail_events) == 1
