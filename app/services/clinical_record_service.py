"""Clinical record service — structured patient clinical context management.

This service manages the four Phase 4 clinical sub-domains:
  1. Clinical History (conditions, past events)
  2. Allergies
  3. Vitals (append-only measurements)
  4. Encounters (clinical interaction contexts)
  5. Clinical Summary (controlled aggregation)

IMPORTANT PRINCIPLES
====================
- No clinical inference or medical interpretation.
- No medication interaction checking.
- No allergy inference from medications.
- No automatic diagnosis or triage.
- Historical vitals are never overwritten.
- Clinical records are soft-deleted only.
- PHI never appears in log messages.
- Authorization is verified at the route layer before calling this service.

DATABASE TEAM DEPENDENCIES
===========================
- clinical_history table
- allergies table
- vitals table
- encounters table
(See respective repository files for full schema contracts.)
"""

import uuid
from datetime import datetime, timezone

from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.logging import get_logger
from app.repositories.allergy_repository import AllergyRecord, AllergyRepository
from app.repositories.clinical_history_repository import (
    ClinicalHistoryRecord,
    ClinicalHistoryRepository,
)
from app.repositories.encounter_repository import EncounterRecord, EncounterRepository
from app.repositories.vitals_repository import VitalRecord, VitalsRepository
from app.schemas.allergy import (
    AllergyCreateRequest,
    AllergyListResponse,
    AllergyResponse,
    AllergyUpdateRequest,
)
from app.schemas.clinical_history import (
    ClinicalHistoryCreateRequest,
    ClinicalHistoryListResponse,
    ClinicalHistoryResponse,
    ClinicalHistoryUpdateRequest,
)
from app.schemas.clinical_summary import ClinicalSummaryResponse, PatientDemographics
from app.schemas.encounter import (
    EncounterCreateRequest,
    EncounterListResponse,
    EncounterResponse,
    EncounterStatus,
)
from app.schemas.patient import PatientResponse
from app.schemas.vital import (
    VitalCreateRequest,
    VitalListResponse,
    VitalResponse,
    VitalType,
)
from app.services.base import BaseService

logger = get_logger("app.clinical_record")


# ---------------------------------------------------------------------------
# Mapping helpers — repository → schema
# ---------------------------------------------------------------------------

def _map_history_to_response(r: ClinicalHistoryRecord) -> ClinicalHistoryResponse:
    return ClinicalHistoryResponse(
        id=r.id,
        patient_id=r.patient_id,
        description=r.description,
        condition_status=r.condition_status,
        onset_date=r.onset_date,
        resolved_date=r.resolved_date,
        source=r.source,
        recorded_by=r.recorded_by,
        notes=r.notes,
        created_at=r.created_at,
        updated_at=r.updated_at,
        is_archived=r.is_archived,
    )


def _map_allergy_to_response(r: AllergyRecord) -> AllergyResponse:
    return AllergyResponse(
        id=r.id,
        patient_id=r.patient_id,
        allergen=r.allergen,
        reaction=r.reaction,
        severity=r.severity,
        status=r.status,
        source=r.source,
        recorded_by=r.recorded_by,
        notes=r.notes,
        created_at=r.created_at,
        updated_at=r.updated_at,
        is_archived=r.is_archived,
    )


def _map_vital_to_response(r: VitalRecord) -> VitalResponse:
    return VitalResponse(
        id=r.id,
        patient_id=r.patient_id,
        vital_type=r.vital_type,
        value=r.value,
        unit=r.unit,
        measured_at=r.measured_at,
        source=r.source,
        recorded_by=r.recorded_by,
        device_id=r.device_id,
        notes=r.notes,
        created_at=r.created_at,
    )


def _map_encounter_to_response(r: EncounterRecord) -> EncounterResponse:
    return EncounterResponse(
        id=r.id,
        patient_id=r.patient_id,
        encounter_type=r.encounter_type,
        status=r.status,
        start_time=r.start_time,
        end_time=r.end_time,
        provider_id=r.provider_id,
        organization_id=r.organization_id,
        external_id=r.external_id,
        source=r.source,
        notes=r.notes,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ClinicalRecordService(BaseService[ClinicalHistoryRepository]):
    """Service managing all Phase 4 clinical sub-domains for a patient."""

    def __init__(
        self,
        history_repo: ClinicalHistoryRepository,
        allergy_repo: AllergyRepository,
        vitals_repo: VitalsRepository,
        encounter_repo: EncounterRepository,
    ) -> None:
        super().__init__(repository=history_repo)
        self.history_repo = history_repo
        self.allergy_repo = allergy_repo
        self.vitals_repo = vitals_repo
        self.encounter_repo = encounter_repo

    # -----------------------------------------------------------------------
    # Clinical History
    # -----------------------------------------------------------------------

    async def list_history(
        self,
        patient_id: str,
        include_archived: bool = False,
    ) -> ClinicalHistoryListResponse:
        """Return all clinical history entries for a patient."""
        records = await self.history_repo.list_by_patient(
            patient_id, include_archived=include_archived
        )
        items = [_map_history_to_response(r) for r in records]
        return ClinicalHistoryListResponse(items=items, total=len(items))

    async def get_history_entry(
        self, patient_id: str, entry_id: str
    ) -> ClinicalHistoryResponse:
        """Retrieve a specific clinical history entry."""
        record = await self.history_repo.get_by_id(entry_id)
        if record is None or record.patient_id != patient_id:
            raise NotFoundException("Clinical history entry not found.")
        return _map_history_to_response(record)

    async def create_history_entry(
        self,
        patient_id: str,
        actor_id: str,
        request: ClinicalHistoryCreateRequest,
    ) -> ClinicalHistoryResponse:
        """Create a new clinical history entry.

        Validates date logic: resolved_date must be >= onset_date if both provided.
        No medical inference is performed.
        """
        if (
            request.onset_date is not None
            and request.resolved_date is not None
            and request.resolved_date < request.onset_date
        ):
            raise ValidationException("resolved_date must be on or after onset_date.")

        now = datetime.now(timezone.utc)
        entry_id = str(uuid.uuid4())
        record = ClinicalHistoryRecord(
            id=entry_id,
            patient_id=patient_id,
            description=request.description,
            condition_status=request.condition_status,
            onset_date=request.onset_date,
            resolved_date=request.resolved_date,
            source=request.source,
            recorded_by=actor_id,
            notes=request.notes,
            created_at=now,
            updated_at=now,
        )
        created = await self.history_repo.create(record)
        logger.info(
            "Clinical history entry created",
            extra={
                "event_type": "CLINICAL_HISTORY_CREATED",
                "actor_id": actor_id,
                "patient_id": patient_id,
                "entry_id": entry_id,
            },
        )
        return _map_history_to_response(created)

    async def update_history_entry(
        self,
        patient_id: str,
        entry_id: str,
        actor_id: str,
        request: ClinicalHistoryUpdateRequest,
    ) -> ClinicalHistoryResponse:
        """Partial update of a clinical history entry."""
        record = await self.history_repo.get_by_id(entry_id)
        if record is None or record.patient_id != patient_id:
            raise NotFoundException("Clinical history entry not found.")
        if record.is_archived:
            raise ValidationException("Cannot update an archived clinical history entry.")

        updates = {k: v for k, v in request.model_dump(exclude_unset=True).items()}
        if not updates:
            return _map_history_to_response(record)

        updated = await self.history_repo.update(entry_id, updates)
        if updated is None:
            raise NotFoundException("Clinical history entry not found after update.")

        logger.info(
            "Clinical history entry updated",
            extra={
                "event_type": "CLINICAL_HISTORY_UPDATED",
                "actor_id": actor_id,
                "patient_id": patient_id,
                "entry_id": entry_id,
            },
        )
        return _map_history_to_response(updated)

    # -----------------------------------------------------------------------
    # Allergies
    # -----------------------------------------------------------------------

    async def list_allergies(
        self,
        patient_id: str,
        include_archived: bool = False,
    ) -> AllergyListResponse:
        """Return all allergy records for a patient."""
        records = await self.allergy_repo.list_by_patient(
            patient_id, include_archived=include_archived
        )
        items = [_map_allergy_to_response(r) for r in records]
        return AllergyListResponse(items=items, total=len(items))

    async def get_allergy(self, patient_id: str, allergy_id: str) -> AllergyResponse:
        """Retrieve a specific allergy record."""
        record = await self.allergy_repo.get_by_id(allergy_id)
        if record is None or record.patient_id != patient_id:
            raise NotFoundException("Allergy record not found.")
        return _map_allergy_to_response(record)

    async def create_allergy(
        self,
        patient_id: str,
        actor_id: str,
        request: AllergyCreateRequest,
    ) -> AllergyResponse:
        """Record a new allergy.

        No medication interaction checking is performed.
        Severity is recorded as provided — not inferred.
        """
        now = datetime.now(timezone.utc)
        allergy_id = str(uuid.uuid4())
        record = AllergyRecord(
            id=allergy_id,
            patient_id=patient_id,
            allergen=request.allergen,
            reaction=request.reaction,
            severity=request.severity,
            status=request.status,
            source=request.source,
            recorded_by=actor_id,
            notes=request.notes,
            created_at=now,
            updated_at=now,
        )
        created = await self.allergy_repo.create(record)
        logger.info(
            "Allergy record created",
            extra={
                "event_type": "ALLERGY_CREATED",
                "actor_id": actor_id,
                "patient_id": patient_id,
                "allergy_id": allergy_id,
            },
        )
        return _map_allergy_to_response(created)

    async def update_allergy(
        self,
        patient_id: str,
        allergy_id: str,
        actor_id: str,
        request: AllergyUpdateRequest,
    ) -> AllergyResponse:
        """Partial update of an allergy record."""
        record = await self.allergy_repo.get_by_id(allergy_id)
        if record is None or record.patient_id != patient_id:
            raise NotFoundException("Allergy record not found.")
        if record.is_archived:
            raise ValidationException("Cannot update an archived allergy record.")

        updates = {k: v for k, v in request.model_dump(exclude_unset=True).items()}
        if not updates:
            return _map_allergy_to_response(record)

        updated = await self.allergy_repo.update(allergy_id, updates)
        if updated is None:
            raise NotFoundException("Allergy record not found after update.")

        logger.info(
            "Allergy record updated",
            extra={
                "event_type": "ALLERGY_UPDATED",
                "actor_id": actor_id,
                "patient_id": patient_id,
                "allergy_id": allergy_id,
            },
        )
        return _map_allergy_to_response(updated)

    # -----------------------------------------------------------------------
    # Vitals (append-only)
    # -----------------------------------------------------------------------

    async def list_vitals(
        self,
        patient_id: str,
        vital_type: VitalType | None = None,
        limit: int = 100,
    ) -> VitalListResponse:
        """Return vital measurements for a patient."""
        records = await self.vitals_repo.list_by_patient(
            patient_id, vital_type=vital_type, limit=limit
        )
        items = [_map_vital_to_response(r) for r in records]
        return VitalListResponse(items=items, total=len(items))

    async def get_vital(self, patient_id: str, vital_id: str) -> VitalResponse:
        """Retrieve a specific vital measurement."""
        record = await self.vitals_repo.get_by_id(vital_id)
        if record is None or record.patient_id != patient_id:
            raise NotFoundException("Vital measurement not found.")
        return _map_vital_to_response(record)

    async def record_vital(
        self,
        patient_id: str,
        actor_id: str,
        request: VitalCreateRequest,
    ) -> VitalResponse:
        """Record a new vital measurement.

        Vitals are append-only — each call creates a new record.
        Historical measurements are never overwritten.
        No medical interpretation is performed.
        """
        now = datetime.now(timezone.utc)
        vital_id = str(uuid.uuid4())
        record = VitalRecord(
            id=vital_id,
            patient_id=patient_id,
            vital_type=request.vital_type,
            value=request.value,
            unit=request.unit,
            measured_at=request.measured_at,
            source=request.source,
            recorded_by=actor_id,
            device_id=request.device_id,
            notes=request.notes,
            created_at=now,
        )
        created = await self.vitals_repo.append(record)
        logger.info(
            "Vital measurement recorded",
            extra={
                "event_type": "VITAL_RECORDED",
                "actor_id": actor_id,
                "patient_id": patient_id,
                "vital_id": vital_id,
                "vital_type": request.vital_type.value,
            },
        )
        return _map_vital_to_response(created)

    # -----------------------------------------------------------------------
    # Encounters
    # -----------------------------------------------------------------------

    async def list_encounters(
        self,
        patient_id: str,
        status_filter: EncounterStatus | None = None,
    ) -> EncounterListResponse:
        """Return encounter records for a patient."""
        records = await self.encounter_repo.list_by_patient(
            patient_id, status_filter=status_filter
        )
        items = [_map_encounter_to_response(r) for r in records]
        return EncounterListResponse(items=items, total=len(items))

    async def get_encounter(
        self, patient_id: str, encounter_id: str
    ) -> EncounterResponse:
        """Retrieve a specific encounter."""
        record = await self.encounter_repo.get_by_id(encounter_id)
        if record is None or record.patient_id != patient_id:
            raise NotFoundException("Encounter not found.")
        return _map_encounter_to_response(record)

    async def create_encounter(
        self,
        patient_id: str,
        actor_id: str,
        request: EncounterCreateRequest,
    ) -> EncounterResponse:
        """Create a new encounter record.

        Does NOT implement appointment scheduling, billing, or workflow.
        """
        now = datetime.now(timezone.utc)
        encounter_id = str(uuid.uuid4())
        record = EncounterRecord(
            id=encounter_id,
            patient_id=patient_id,
            encounter_type=request.encounter_type,
            status=request.status,
            start_time=request.start_time,
            end_time=request.end_time,
            provider_id=request.provider_id,
            organization_id=request.organization_id,
            external_id=request.external_id,
            source=request.source,
            notes=request.notes,
            created_at=now,
            updated_at=now,
        )
        created = await self.encounter_repo.create(record)
        logger.info(
            "Encounter created",
            extra={
                "event_type": "ENCOUNTER_CREATED",
                "actor_id": actor_id,
                "patient_id": patient_id,
                "encounter_id": encounter_id,
            },
        )
        return _map_encounter_to_response(created)

    # -----------------------------------------------------------------------
    # Clinical Summary
    # -----------------------------------------------------------------------

    async def get_clinical_summary(
        self,
        patient_id: str,
        patient_profile: PatientResponse,
    ) -> ClinicalSummaryResponse:
        """Assemble a controlled clinical summary for a patient.

        Summary includes:
          - Basic demographics (from patient_profile)
          - Active/unresolved clinical history
          - Active allergies
          - Most recent vital per type
          - Active/planned encounters

        Explicitly excluded (pending later phases):
          - prescriptions, medications, care plans, documents

        No clinical interpretation is performed.
        """
        from app.schemas.clinical_history import ConditionStatus as CS
        from app.schemas.allergy import AllergyStatus as AS

        # Active conditions: ACTIVE or UNKNOWN status, not archived
        all_history = await self.history_repo.list_by_patient(patient_id)
        active_conditions = [
            _map_history_to_response(r) for r in all_history
            if r.condition_status in (CS.ACTIVE, CS.UNKNOWN)
        ]

        # Active allergies
        all_allergies = await self.allergy_repo.list_by_patient(patient_id)
        known_allergies = [
            _map_allergy_to_response(r) for r in all_allergies
            if r.status in (AS.ACTIVE, AS.UNKNOWN)
        ]

        # Latest vital per type
        latest_vitals_map = await self.vitals_repo.get_latest_per_type(patient_id)
        recent_vitals = [
            _map_vital_to_response(r) for r in latest_vitals_map.values()
        ]

        # Active encounters
        active_enc_records = await self.encounter_repo.list_active_by_patient(patient_id)
        active_encounters = [_map_encounter_to_response(r) for r in active_enc_records]

        demographics = PatientDemographics(
            id=patient_profile.id,
            first_name=patient_profile.first_name,
            last_name=patient_profile.last_name,
            date_of_birth=patient_profile.date_of_birth,
            sex=patient_profile.sex,
            preferred_language=patient_profile.preferred_language,
            status=patient_profile.status,
        )

        return ClinicalSummaryResponse(
            patient=demographics,
            active_conditions=active_conditions,
            known_allergies=known_allergies,
            recent_vitals=recent_vitals,
            active_encounters=active_encounters,
            summary_generated_at=datetime.now(timezone.utc),
        )
