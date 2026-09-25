"""Clinical Triage Assessment Service (Phase 8).

Orchestrates deterministic rule-based triage evaluations, clinical context
aggregation (vitals, history, allergies, medications), explanation generation,
and provenance tracking.

STRICT CLINICAL BOUNDARY:
- Triage categorizes clinical urgency based on validated protocol rules.
- Triage is NOT a diagnosis and does NOT replace physician judgment.
- Large language models do NOT evaluate or decide urgency.
"""

import asyncio
from datetime import date, datetime, timezone
import time
from typing import Any
import uuid

from app.core.config import Settings, get_settings
from app.core.exceptions import AppException, ErrorCode
from app.integrations.triage.base import (
    TriageEvaluationContext,
    TriageRuleEngine,
)
from app.integrations.triage.rule_engine import HealthSetuDeterministicTriageEngine
from app.repositories.allergy_repository import AllergyRepository
from app.repositories.clinical_history_repository import ClinicalHistoryRepository
from app.repositories.patient_medication_repository import PatientMedicationRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.symptom_repository import SymptomRepository
from app.repositories.triage_repository import TriageRepository
from app.repositories.vitals_repository import VitalsRepository
from app.schemas.allergy import AllergyStatus
from app.schemas.clinical_history import ConditionStatus
from app.schemas.medication import PatientMedicationStatus
from app.schemas.symptom import SymptomItemCreate
from app.schemas.triage import (
    TRIAGE_CLINICAL_DISCLAIMER,
    MissingInformationItem,
    TriageAssessmentCreate,
    TriageAssessmentRecord,
    TriageAssessmentResponse,
    TriageExplanation,
    TriageListResponse,
    TriageReason,
    TriageStatus,
    TriageUrgency,
)
from app.schemas.vital import VitalType
from app.services.audit_service import AuditService


class TriageService:
    """Service orchestrating clinical triage assessment lifecycle."""

    def __init__(
        self,
        triage_repo: TriageRepository,
        symptom_repo: SymptomRepository,
        audit_service: AuditService,
        rule_engine: TriageRuleEngine | None = None,
        vitals_repo: VitalsRepository | None = None,
        patient_repo: PatientRepository | None = None,
        clinical_history_repo: ClinicalHistoryRepository | None = None,
        allergy_repo: AllergyRepository | None = None,
        patient_medication_repo: PatientMedicationRepository | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.triage_repo = triage_repo
        self.symptom_repo = symptom_repo
        self.audit_service = audit_service
        self.settings = settings or get_settings()
        self.rule_engine = rule_engine or HealthSetuDeterministicTriageEngine(
            rule_set_name=self.settings.TRIAGE_RULE_SET,
            rule_set_version=self.settings.TRIAGE_RULE_SET_VERSION,
        )
        self.vitals_repo = vitals_repo
        self.patient_repo = patient_repo
        self.clinical_history_repo = clinical_history_repo
        self.allergy_repo = allergy_repo
        self.patient_medication_repo = patient_medication_repo

    async def assess_patient(
        self,
        patient_id: str,
        payload: TriageAssessmentCreate,
        actor_id: str,
    ) -> TriageAssessmentResponse:
        """Execute a deterministic clinical triage assessment."""
        start_time = time.perf_counter()

        # 1. Idempotency verification
        if payload.idempotency_key:
            existing = await self.triage_repo.get_by_idempotency_key(patient_id, payload.idempotency_key)
            if existing:
                return self._to_response(existing)

        # 2. Symptom aggregation
        symptoms_to_evaluate: list[SymptomItemCreate] = list(payload.symptoms)

        # Retrieve referenced symptoms
        if payload.symptom_ids:
            for sid in payload.symptom_ids:
                s_rec = await self.symptom_repo.get_by_id(sid)
                if s_rec and s_rec.patient_id == patient_id:
                    symptoms_to_evaluate.append(
                        SymptomItemCreate(
                            symptom=s_rec.symptom_normalized or s_rec.symptom_raw,
                            severity=s_rec.severity,
                            onset=s_rec.onset,
                            duration=s_rec.duration,
                            location=s_rec.location,
                            character=s_rec.character,
                            frequency=s_rec.frequency,
                            progression=s_rec.progression,
                            associated_symptoms=s_rec.associated_symptoms,
                            aggravating_factors=s_rec.aggravating_factors,
                            relieving_factors=s_rec.relieving_factors,
                            patient_reported_context=s_rec.patient_reported_context,
                        )
                    )

        # Retrieve symptoms from intake session
        if payload.intake_id:
            session = await self.symptom_repo.get_intake_session(payload.intake_id)
            if session and session["patient_id"] == patient_id:
                for s_rec in session.get("symptoms", []):
                    symptoms_to_evaluate.append(
                        SymptomItemCreate(
                            symptom=s_rec.symptom_normalized or s_rec.symptom_raw,
                            severity=s_rec.severity,
                            onset=s_rec.onset,
                            duration=s_rec.duration,
                            location=s_rec.location,
                            character=s_rec.character,
                            frequency=s_rec.frequency,
                            progression=s_rec.progression,
                            associated_symptoms=s_rec.associated_symptoms,
                            aggravating_factors=s_rec.aggravating_factors,
                            relieving_factors=s_rec.relieving_factors,
                            patient_reported_context=s_rec.patient_reported_context,
                        )
                    )

        if not symptoms_to_evaluate:
            raise AppException(
                code=ErrorCode.TRIAGE_INVALID_INPUT,
                message="At least one symptom must be provided or referenced for triage assessment.",
                status_code=400,
            )

        # 3. Context aggregation (minimized, Phase 4/6/7 data)
        age = None
        sex = None
        if self.patient_repo:
            patient_rec = await self.patient_repo.get_by_id(patient_id)
            if patient_rec:
                if patient_rec.date_of_birth:
                    today = date.today()
                    dob = patient_rec.date_of_birth
                    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                if patient_rec.sex:
                    sex = patient_rec.sex.value if hasattr(patient_rec.sex, "value") else str(patient_rec.sex)

        conditions: list[str] = []
        if self.clinical_history_repo:
            cond_recs = await self.clinical_history_repo.list_by_patient(patient_id, include_archived=False)
            conditions = [
                c.description for c in cond_recs
                if getattr(c, "condition_status", None) == ConditionStatus.ACTIVE
            ]

        allergies: list[str] = []
        if self.allergy_repo:
            allergy_recs = await self.allergy_repo.list_by_patient(patient_id, include_archived=False)
            allergies = [
                a.allergen for a in allergy_recs
                if getattr(a, "status", None) == AllergyStatus.ACTIVE
            ]

        current_medications: list[str] = []
        if self.patient_medication_repo:
            med_recs = await self.patient_medication_repo.list_by_patient(
                patient_id=patient_id,
                status_filter=PatientMedicationStatus.ACTIVE,
                limit=50,
            )
            current_medications = [m.drug_name_raw for m in med_recs]

        # 4. Vitals aggregation (Phase 4 integration)
        vitals_dict: dict[str, Any] = {}
        vitals_timestamps: dict[str, str] = {}
        if self.vitals_repo:
            vital_records = []
            if payload.vital_ids:
                for vid in payload.vital_ids:
                    vr = await self.vitals_repo.get_by_id(vid)
                    if vr and getattr(vr, "patient_id", None) == patient_id:
                        vital_records.append(vr)
            else:
                vital_records = await self.vitals_repo.list_by_patient(patient_id, limit=20)

            # Map latest measurements
            for v in vital_records:
                vtype = getattr(v, "vital_type", None)
                val = getattr(v, "value", None)
                measured_at = getattr(v, "measured_at", None)
                ts_str = measured_at.isoformat() if measured_at else ""

                if vtype == VitalType.OXYGEN_SATURATION and "oxygen_saturation" not in vitals_dict:
                    vitals_dict["oxygen_saturation"] = float(val)
                    vitals_timestamps["oxygen_saturation"] = ts_str
                elif vtype == VitalType.HEART_RATE and "heart_rate" not in vitals_dict:
                    vitals_dict["heart_rate"] = float(val)
                    vitals_timestamps["heart_rate"] = ts_str
                elif vtype == VitalType.BLOOD_PRESSURE_SYSTOLIC and "systolic_bp" not in vitals_dict:
                    vitals_dict["systolic_bp"] = float(val)
                    vitals_timestamps["systolic_bp"] = ts_str
                elif vtype == VitalType.BLOOD_PRESSURE_DIASTOLIC and "diastolic_bp" not in vitals_dict:
                    vitals_dict["diastolic_bp"] = float(val)
                    vitals_timestamps["diastolic_bp"] = ts_str
                elif vtype == VitalType.RESPIRATORY_RATE and "respiratory_rate" not in vitals_dict:
                    vitals_dict["respiratory_rate"] = float(val)
                    vitals_timestamps["respiratory_rate"] = ts_str
                elif vtype == VitalType.TEMPERATURE and "temperature_c" not in vitals_dict:
                    vitals_dict["temperature_c"] = float(val)
                    vitals_timestamps["temperature_c"] = ts_str

        assessment_id = str(uuid.uuid4())

        # Audit assessment started
        await self.audit_service.record_triage_assessment_started(
            actor_id=actor_id,
            patient_id=patient_id,
            assessment_id=assessment_id,
            rule_set=self.rule_engine.rule_set_name,
            rule_set_version=self.rule_engine.rule_set_version,
        )

        # 5. Execute rule engine with timeout protection
        eval_context = TriageEvaluationContext(
            patient_id=patient_id,
            age=age,
            biological_sex=sex,
            symptoms=symptoms_to_evaluate,
            vitals=vitals_dict,
            vitals_recorded_at=vitals_timestamps,
            known_conditions=conditions,
            allergies=allergies,
            current_medications=current_medications,
        )

        try:
            timeout_sec = self.settings.TRIAGE_RULE_ENGINE_TIMEOUT_SECONDS
            engine_result = await asyncio.wait_for(
                self.rule_engine.evaluate(eval_context),
                timeout=float(timeout_sec),
            )
        except asyncio.TimeoutError:
            await self.audit_service.record_triage_assessment_failed(
                actor_id=actor_id,
                patient_id=patient_id,
                assessment_id=assessment_id,
                error_code="TRIAGE_RULE_ENGINE_TIMEOUT",
            )
            raise AppException(
                code=ErrorCode.TRIAGE_RULE_ENGINE_UNAVAILABLE,
                message=f"Triage rule engine evaluation timed out after {timeout_sec}s.",
                status_code=504,
            )
        except Exception as e:
            await self.audit_service.record_triage_assessment_failed(
                actor_id=actor_id,
                patient_id=patient_id,
                assessment_id=assessment_id,
                error_code="TRIAGE_RULE_EVALUATION_FAILED",
            )
            raise AppException(
                code=ErrorCode.TRIAGE_RULE_EVALUATION_FAILED,
                message=f"Triage rule evaluation failed: {str(e)}",
                status_code=500,
            )

        # 6. Assemble Explanation and Record
        now = datetime.now(timezone.utc)
        missing_summaries = [f"{m.field}: {m.description}" for m in engine_result.missing_information]

        explanation = TriageExplanation(
            summary=(
                f"Triage evaluation completed using {self.rule_engine.rule_set_name} (v{self.rule_engine.rule_set_version}). "
                f"Urgency classification: {engine_result.urgency.value}."
            ),
            factors_considered=engine_result.factors_considered,
            urgency_rationale=engine_result.urgency_rationale,
            missing_data_summary=missing_summaries,
            recommended_level_of_care=engine_result.recommended_level_of_care,
            disclaimer=TRIAGE_CLINICAL_DISCLAIMER,
        )

        record = TriageAssessmentRecord(
            id=assessment_id,
            patient_id=patient_id,
            encounter_id=payload.encounter_id,
            intake_id=payload.intake_id,
            urgency=engine_result.urgency,
            status=engine_result.status,
            reasons=engine_result.reasons,
            missing_information=engine_result.missing_information,
            rule_set=engine_result.rule_set,
            rule_set_version=engine_result.rule_set_version,
            explanation=explanation,
            immediate_instruction=engine_result.immediate_instruction,
            previous_assessment_id=payload.previous_assessment_id,
            idempotency_key=payload.idempotency_key,
            assessed_by=actor_id,
            assessed_at=now,
            created_at=now,
        )

        await self.triage_repo.create(record)

        # 7. Audit completion or reassessment
        duration_ms = (time.perf_counter() - start_time) * 1000
        if payload.assessment_type == "REASSESSMENT" and payload.previous_assessment_id:
            await self.audit_service.record_triage_reassessment_created(
                actor_id=actor_id,
                patient_id=patient_id,
                new_assessment_id=assessment_id,
                previous_assessment_id=payload.previous_assessment_id,
                urgency=record.urgency.value,
            )
        else:
            await self.audit_service.record_triage_assessment_completed(
                actor_id=actor_id,
                patient_id=patient_id,
                assessment_id=assessment_id,
                urgency=record.urgency.value,
                status=record.status.value,
                duration_ms=duration_ms,
            )

        return self._to_response(record)

    async def get_assessment(
        self,
        patient_id: str,
        assessment_id: str,
        actor_id: str,
    ) -> TriageAssessmentResponse:
        """Retrieve a specific triage assessment by ID."""
        record = await self.triage_repo.get_by_id(assessment_id)
        if not record or record.patient_id != patient_id:
            raise AppException(
                code=ErrorCode.TRIAGE_ASSESSMENT_NOT_FOUND,
                message=f"Triage assessment '{assessment_id}' not found for patient.",
                status_code=404,
            )
        return self._to_response(record)

    async def list_assessments(
        self,
        patient_id: str,
        actor_id: str,
        limit: int = 50,
        offset: int = 0,
        urgency: TriageUrgency | None = None,
        encounter_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> TriageListResponse:
        """List paginated triage assessments for a patient."""
        items, total = await self.triage_repo.list_by_patient(
            patient_id=patient_id,
            limit=limit,
            offset=offset,
            urgency=urgency,
            encounter_id=encounter_id,
            start_date=start_date,
            end_date=end_date,
        )
        return TriageListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    def _to_response(self, record: TriageAssessmentRecord) -> TriageAssessmentResponse:
        """Map internal assessment record to API response schema."""
        return TriageAssessmentResponse(
            assessment_id=record.id,
            patient_id=record.patient_id,
            urgency=record.urgency,
            status=record.status,
            reasons=record.reasons,
            missing_information=record.missing_information,
            explanation=record.explanation,
            immediate_instruction=record.immediate_instruction,
            rule_set=record.rule_set,
            rule_set_version=record.rule_set_version,
            previous_assessment_id=record.previous_assessment_id,
            sbar_id=record.sbar_id,
            assessed_at=record.assessed_at,
        )
