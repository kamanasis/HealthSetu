"""Structured Symptom Intake Service (Phase 8).

Manages structured symptom recording, provenance preservation,
terminology normalization (raw vs normalized), and intake sessions.
Clinical boundary: Normalization is NOT a diagnosis.
"""

from datetime import datetime, timezone
import uuid
from typing import Any

from app.core.exceptions import AppException, ErrorCode
from app.repositories.symptom_repository import SymptomRepository
from app.schemas.symptom import (
    SymptomItemCreate,
    SymptomIntakeCreate,
    SymptomIntakeResponse,
    SymptomListResponse,
    SymptomRecord,
    SymptomSource,
)
from app.services.audit_service import AuditService


# Terminology normalization map (raw colloquial phrases -> standardized symptom terminology)
# NOTE: Standardizing terminology does NOT constitute a disease diagnosis.
SYMPTOM_NORMALIZATION_MAP: dict[str, str] = {
    "breathing problem": "shortness of breath",
    "hard to breathe": "shortness of breath",
    "short of breath": "shortness of breath",
    "cant breathe": "dyspnea",
    "breathless": "shortness of breath",
    "chest tightness": "chest discomfort",
    "heavy chest": "chest pressure",
    "racing heart": "palpitations",
    "fluttering heart": "palpitations",
    "heart pounding": "palpitations",
    "high temp": "fever",
    "feeling hot": "fever",
    "chills and fever": "pyrexia",
    "throw up": "vomiting",
    "throwing up": "vomiting",
    "upset stomach": "nausea",
    "lightheaded": "dizziness",
    "head spinning": "vertigo",
    "belly ache": "abdominal pain",
    "stomach cramps": "abdominal pain",
}


class SymptomService:
    """Service orchestrating symptom intake and session lifecycle."""

    def __init__(
        self,
        symptom_repo: SymptomRepository,
        audit_service: AuditService,
    ) -> None:
        self.symptom_repo = symptom_repo
        self.audit_service = audit_service

    def _normalize_symptom(self, raw: str) -> str:
        """Map colloquial description to standard clinical symptom terminology."""
        cleaned = raw.lower().strip()
        for colloquial, standard in SYMPTOM_NORMALIZATION_MAP.items():
            if colloquial in cleaned:
                return standard
        return cleaned

    async def record_symptom_intake(
        self,
        patient_id: str,
        payload: SymptomIntakeCreate,
        actor_id: str,
    ) -> SymptomIntakeResponse:
        """Record a structured symptom intake batch/session."""
        if not payload.symptoms:
            raise AppException(
                code=ErrorCode.TRIAGE_INVALID_INPUT,
                message="At least one symptom must be provided in intake session.",
                status_code=400,
            )

        intake_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        stored_symptoms: list[SymptomRecord] = []

        for item in payload.symptoms:
            normalized = self._normalize_symptom(item.symptom)
            record = SymptomRecord(
                id=str(uuid.uuid4()),
                patient_id=patient_id,
                intake_id=intake_id,
                encounter_id=payload.encounter_id,
                symptom_raw=item.symptom,
                symptom_normalized=normalized,
                severity=item.severity,
                onset=item.onset,
                duration=item.duration,
                location=item.location,
                character=item.character,
                frequency=item.frequency,
                progression=item.progression,
                associated_symptoms=item.associated_symptoms,
                aggravating_factors=item.aggravating_factors,
                relieving_factors=item.relieving_factors,
                patient_reported_context=item.patient_reported_context,
                source=payload.source,
                recorded_by=actor_id,
                created_at=now,
                updated_at=now,
            )
            stored_symptoms.append(record)

        session_dict = await self.symptom_repo.create_intake_session(
            intake_id=intake_id,
            patient_id=patient_id,
            encounter_id=payload.encounter_id,
            source=payload.source,
            symptoms=stored_symptoms,
            notes=payload.notes,
        )

        # Audit event: IDs and counts only, NO narrative PHI
        await self.audit_service.record_symptom_intake_created(
            actor_id=actor_id,
            patient_id=patient_id,
            intake_id=intake_id,
            symptom_count=len(stored_symptoms),
            source=payload.source.value,
        )

        return SymptomIntakeResponse(
            intake_id=intake_id,
            patient_id=patient_id,
            encounter_id=payload.encounter_id,
            source=payload.source,
            symptoms=stored_symptoms,
            notes=payload.notes,
            created_at=session_dict["created_at"],
        )

    async def list_patient_symptoms(
        self,
        patient_id: str,
        actor_id: str,
        limit: int = 50,
        offset: int = 0,
        source: SymptomSource | None = None,
        encounter_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> SymptomListResponse:
        """Retrieve paginated symptoms recorded for a patient."""
        items, total = await self.symptom_repo.list_by_patient(
            patient_id=patient_id,
            limit=limit,
            offset=offset,
            source=source,
            encounter_id=encounter_id,
            start_date=start_date,
            end_date=end_date,
        )

        await self.audit_service.record_symptom_intake_viewed(
            actor_id=actor_id,
            patient_id=patient_id,
            resource_id=patient_id,
        )

        return SymptomListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_symptom_by_id(
        self,
        patient_id: str,
        symptom_id: str,
        actor_id: str,
    ) -> SymptomRecord:
        """Get a specific symptom record by ID with patient boundary check."""
        record = await self.symptom_repo.get_by_id(symptom_id)
        if not record or record.patient_id != patient_id:
            raise AppException(
                code=ErrorCode.SYMPTOM_NOT_FOUND,
                message=f"Symptom record '{symptom_id}' not found for patient.",
                status_code=404,
            )

        await self.audit_service.record_symptom_intake_viewed(
            actor_id=actor_id,
            patient_id=patient_id,
            resource_id=symptom_id,
        )
        return record
