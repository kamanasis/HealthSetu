"""SBAR Clinical Summary Generation Service (Phase 8).

Orchestrates SBAR clinical communication document synthesis:
- Situation, Background, Assessment, Recommendation structure.
- Deterministic template generation fallback.
- Optional AI text generation with strict factual validation.
- Immutable provenance and audit logging.
"""

from datetime import datetime, timezone
import time
from typing import Any
import uuid

from app.core.config import Settings, get_settings
from app.core.exceptions import AppException, ErrorCode
from app.integrations.ai.base import (
    ClinicalTextGenerator,
    SBARInputFacts,
    SBARGeneratedOutput,
)
from app.integrations.ai.providers.mock_llm import MockLLMClinicalTextGenerator
from app.integrations.ai.providers.template_generator import TemplateClinicalTextGenerator
from app.integrations.ai.validator import SBARFactValidator
from app.repositories.allergy_repository import AllergyRepository
from app.repositories.clinical_history_repository import ClinicalHistoryRepository
from app.repositories.encounter_repository import EncounterRepository
from app.repositories.patient_medication_repository import PatientMedicationRepository
from app.repositories.sbar_repository import SBARRepository
from app.repositories.symptom_repository import SymptomRepository
from app.repositories.triage_repository import TriageRepository
from app.repositories.vitals_repository import VitalsRepository
from app.schemas.allergy import AllergyStatus
from app.schemas.clinical_history import ConditionStatus
from app.schemas.medication import PatientMedicationStatus
from app.schemas.sbar import (
    SBARCreate,
    SBARFactValidationResult,
    SBARGenerationMode,
    SBARRecord,
    SBARResponse,
)
from app.schemas.vital import VitalType
from app.services.audit_service import AuditService


class SBARService:
    """Service orchestrating SBAR clinical summary synthesis and validation."""

    def __init__(
        self,
        sbar_repo: SBARRepository,
        triage_repo: TriageRepository,
        audit_service: AuditService,
        template_generator: ClinicalTextGenerator | None = None,
        ai_generator: ClinicalTextGenerator | None = None,
        validator: SBARFactValidator | None = None,
        symptom_repo: SymptomRepository | None = None,
        vitals_repo: VitalsRepository | None = None,
        clinical_history_repo: ClinicalHistoryRepository | None = None,
        allergy_repo: AllergyRepository | None = None,
        patient_medication_repo: PatientMedicationRepository | None = None,
        encounter_repo: EncounterRepository | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.sbar_repo = sbar_repo
        self.triage_repo = triage_repo
        self.audit_service = audit_service
        self.template_generator = template_generator or TemplateClinicalTextGenerator()
        self.ai_generator = ai_generator or MockLLMClinicalTextGenerator()
        self.validator = validator or SBARFactValidator()
        self.symptom_repo = symptom_repo
        self.vitals_repo = vitals_repo
        self.clinical_history_repo = clinical_history_repo
        self.allergy_repo = allergy_repo
        self.patient_medication_repo = patient_medication_repo
        self.encounter_repo = encounter_repo
        self.settings = settings or get_settings()

    async def generate_sbar(
        self,
        patient_id: str,
        payload: SBARCreate,
        actor_id: str,
    ) -> SBARResponse:
        """Generate structured SBAR clinical summary from authoritative triage facts."""
        # 1. Fetch triage assessment
        assessment = await self.triage_repo.get_by_id(payload.assessment_id)
        if not assessment or assessment.patient_id != patient_id:
            raise AppException(
                code=ErrorCode.TRIAGE_ASSESSMENT_NOT_FOUND,
                message=f"Triage assessment '{payload.assessment_id}' not found for patient.",
                status_code=404,
            )

        previous_sbar_id = assessment.sbar_id

        # 2. Gather verified clinical facts
        conditions: list[str] = []
        if self.clinical_history_repo:
            crecs = await self.clinical_history_repo.list_by_patient(patient_id, include_archived=False)
            conditions = [c.description for c in crecs if getattr(c, "condition_status", None) == ConditionStatus.ACTIVE]

        allergies: list[str] = []
        if self.allergy_repo:
            arecs = await self.allergy_repo.list_by_patient(patient_id, include_archived=False)
            allergies = [a.allergen for a in arecs if getattr(a, "status", None) == AllergyStatus.ACTIVE]

        meds: list[str] = []
        if self.patient_medication_repo:
            mrecs = await self.patient_medication_repo.list_by_patient(
                patient_id=patient_id,
                status_filter=PatientMedicationStatus.ACTIVE,
                limit=50,
            )
            meds = [m.drug_name_raw for m in mrecs]

        encounters: list[str] = []
        if self.encounter_repo:
            erecs = await self.encounter_repo.list_by_patient(patient_id)
            encounters = [f"Encounter ({getattr(e, 'encounter_type', 'Clinical')})" for e in erecs[:3]]

        vitals_dict: dict[str, str] = {}
        if self.vitals_repo:
            vrecs = await self.vitals_repo.list_by_patient(patient_id, limit=10)
            for v in vrecs:
                vtype = getattr(v, "vital_type", None)
                val = getattr(v, "value", None)
                unit = getattr(v, "unit", "")
                if vtype == VitalType.OXYGEN_SATURATION and "SpO2" not in vitals_dict:
                    vitals_dict["SpO2"] = f"{val}{unit}"
                elif vtype == VitalType.HEART_RATE and "Pulse" not in vitals_dict:
                    vitals_dict["Pulse"] = f"{val} {unit}"
                elif vtype == VitalType.BLOOD_PRESSURE_SYSTOLIC and "Systolic BP" not in vitals_dict:
                    vitals_dict["Systolic BP"] = f"{val} {unit}"
                elif vtype == VitalType.TEMPERATURE and "Temp" not in vitals_dict:
                    vitals_dict["Temp"] = f"{val} {unit}"

        # Presenting symptoms extracted from explanation or factors
        presenting_symptoms: list[str] = []
        for factor in assessment.explanation.factors_considered:
            if factor.startswith("Symptom:"):
                # Clean up "Symptom: chest pain (Severity: SEVERE)"
                sym_part = factor.replace("Symptom:", "").split("(")[0].strip()
                if sym_part and sym_part not in presenting_symptoms:
                    presenting_symptoms.append(sym_part)

        triggered_rule_texts = [r.description for r in assessment.reasons]
        missing_texts = [m.field for m in assessment.missing_information]

        facts = SBARInputFacts(
            patient_id=patient_id,
            urgency=assessment.urgency,
            reason_for_attention=f"Clinical Triage Evaluation - Urgency: {assessment.urgency.value}",
            presenting_symptoms=presenting_symptoms,
            known_conditions=conditions,
            active_medications=meds,
            allergies=allergies,
            recent_encounters=encounters,
            triggered_rules=triggered_rule_texts,
            vitals=vitals_dict,
            recommended_level_of_care=assessment.explanation.recommended_level_of_care,
            immediate_instruction=assessment.immediate_instruction,
            missing_information=missing_texts,
            follow_up_recommendation="Conduct in-person clinical assessment and verify patient hemodynamic status.",
        )

        # 3. Determine generation mode
        requested_mode = payload.generation_mode or SBARGenerationMode(self.settings.SBAR_GENERATION_MODE)
        validation_result: SBARFactValidationResult | None = None
        effective_mode = requested_mode

        if requested_mode == SBARGenerationMode.AI:
            # AI Generation path
            ai_output = await self.ai_generator.generate_sbar(facts)
            validation_result = self.validator.validate(facts, ai_output)

            if validation_result.is_valid:
                generated = ai_output
            else:
                # Fall back safely to deterministic template if validation fails
                generated = await self.template_generator.generate_sbar(facts)
                effective_mode = SBARGenerationMode.TEMPLATE
                generated.model_metadata["fallback_reason"] = "AI fact validation failed"
                generated.model_metadata["validation_errors"] = validation_result.validation_errors
        else:
            # Deterministic Template path
            generated = await self.template_generator.generate_sbar(facts)
            validation_result = SBARFactValidationResult(
                is_valid=True,
                validation_errors=[],
                verified_symptoms=facts.presenting_symptoms,
                verified_medications=facts.active_medications,
                verified_allergies=facts.allergies,
                verified_conditions=facts.known_conditions,
                verified_urgency=facts.urgency.value,
            )

        # 4. Create and persist SBAR Record
        sbar_id = str(uuid.uuid4())
        record = SBARRecord(
            id=sbar_id,
            patient_id=patient_id,
            assessment_id=payload.assessment_id,
            encounter_id=payload.encounter_id or assessment.encounter_id,
            intake_id=payload.intake_id or assessment.intake_id,
            generation_mode=effective_mode,
            situation=generated.situation,
            background=generated.background,
            assessment=generated.assessment,
            recommendation=generated.recommendation,
            plain_text=generated.plain_text,
            validation_result=validation_result,
            generator_version="1.0.0",
            model_metadata=generated.model_metadata,
            created_by=actor_id,
            created_at=datetime.now(timezone.utc),
        )

        await self.sbar_repo.create(record)

        # Update assessment reference
        assessment_update = assessment.model_copy(update={"sbar_id": sbar_id})
        await self.triage_repo.update(assessment.id, assessment_update)

        # 5. Audit event
        if previous_sbar_id:
            await self.audit_service.record_sbar_regenerated(
                actor_id=actor_id,
                patient_id=patient_id,
                new_sbar_id=sbar_id,
                previous_sbar_id=previous_sbar_id,
            )
        else:
            await self.audit_service.record_sbar_created(
                actor_id=actor_id,
                patient_id=patient_id,
                sbar_id=sbar_id,
                assessment_id=payload.assessment_id,
                generator_mode=effective_mode.value,
            )

        return self._to_response(record)

    async def get_sbar(
        self,
        patient_id: str,
        sbar_id: str,
        actor_id: str,
    ) -> SBARResponse:
        """Retrieve an existing SBAR clinical summary by ID."""
        record = await self.sbar_repo.get_by_id(sbar_id)
        if not record or record.patient_id != patient_id:
            raise AppException(
                code=ErrorCode.SBAR_NOT_FOUND,
                message=f"SBAR summary '{sbar_id}' not found for patient.",
                status_code=404,
            )

        await self.audit_service.record_sbar_viewed(
            actor_id=actor_id,
            patient_id=patient_id,
            sbar_id=sbar_id,
        )

        return self._to_response(record)

    def _to_response(self, record: SBARRecord) -> SBARResponse:
        """Convert SBAR record to API response."""
        return SBARResponse(
            sbar_id=record.id,
            patient_id=record.patient_id,
            assessment_id=record.assessment_id,
            encounter_id=record.encounter_id,
            intake_id=record.intake_id,
            generation_mode=record.generation_mode,
            situation=record.situation,
            background=record.background,
            assessment=record.assessment,
            recommendation=record.recommendation,
            plain_text=record.plain_text,
            created_at=record.created_at,
        )
