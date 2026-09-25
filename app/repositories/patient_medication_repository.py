"""Patient medication repository.

DATABASE TEAM DEPENDENCY — PHASE 6
===================================
In-memory repository implementing the data contract for longitudinal patient medication records.
Expected PostgreSQL table:
- patient_medications
"""

import asyncio
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.repositories.base import BaseRepository
from app.schemas.medication import (
    MedicationSource,
    PatientMedicationStatus,
    VerificationStatus,
)


class PatientMedicationRecord(BaseModel):
    """Database record representation of a patient medication entry."""
    model_config = ConfigDict(frozen=True)

    id: str
    patient_id: str
    status: PatientMedicationStatus = PatientMedicationStatus.PRESCRIBED
    verification_status: VerificationStatus = VerificationStatus.EXTRACTED
    drug_name_raw: str
    strength_raw: str | None = None
    dosage_form_raw: str | None = None
    route_raw: str | None = None
    frequency_raw: str | None = None
    duration_raw: str | None = None
    instructions_raw: str | None = None
    normalized_medication_id: str | None = None
    source: MedicationSource = MedicationSource.PRESCRIPTION
    # Provenance
    document_id: str | None = None
    extraction_id: str | None = None
    prescription_id: str | None = None
    prescription_item_id: str | None = None
    # Duplicate data flag (data-level only; no clinical claim)
    potential_duplicate: bool = False
    # Correction tracking
    is_corrected: bool = False
    original_raw_value: str | None = None
    corrected_raw_value: str | None = None
    corrected_by: str | None = None
    corrected_at: datetime | None = None
    # Timing
    start_date: datetime | None = None
    end_date: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PatientMedicationRepository(BaseRepository[Any]):
    """Repository managing patient medication records."""

    def __init__(self, session: Any = None) -> None:
        super().__init__(session=session)
        self._medications: dict[str, PatientMedicationRecord] = {}
        self._lock = asyncio.Lock()

    def clear(self) -> None:
        """Clear in-memory state for testing."""
        self._medications.clear()

    async def create_record(self, record: PatientMedicationRecord) -> PatientMedicationRecord:
        """Persist a new patient medication record."""
        async with self._lock:
            self._medications[record.id] = record
            return record

    async def get_record(self, record_id: str) -> PatientMedicationRecord | None:
        """Fetch patient medication record by ID."""
        async with self._lock:
            return self._medications.get(record_id)

    async def list_by_patient(
        self,
        patient_id: str,
        status_filter: PatientMedicationStatus | None = None,
        source_filter: MedicationSource | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[PatientMedicationRecord]:
        """List patient medications with optional status/source filtering and pagination."""
        async with self._lock:
            records = [r for r in self._medications.values() if r.patient_id == patient_id]

            if status_filter is not None:
                records = [r for r in records if r.status == status_filter]

            if source_filter is not None:
                records = [r for r in records if r.source == source_filter]

            records.sort(key=lambda x: x.created_at, reverse=True)
            return records[skip : skip + limit]

    async def count_by_patient(
        self,
        patient_id: str,
        status_filter: PatientMedicationStatus | None = None,
        source_filter: MedicationSource | None = None,
    ) -> int:
        """Count patient medications matching criteria."""
        async with self._lock:
            records = [r for r in self._medications.values() if r.patient_id == patient_id]
            if status_filter is not None:
                records = [r for r in records if r.status == status_filter]
            if source_filter is not None:
                records = [r for r in records if r.source == source_filter]
            return len(records)

    async def update_record(self, record: PatientMedicationRecord) -> PatientMedicationRecord:
        """Update existing patient medication record."""
        async with self._lock:
            self._medications[record.id] = record
            return record

    async def check_potential_duplicate(
        self,
        patient_id: str,
        drug_name_raw: str,
        normalized_medication_id: str | None = None,
    ) -> bool:
        """Detect potential duplicate records at data level.

        CRITICAL ARCHITECTURAL BOUNDARY:
        Returns True if a duplicate record is detected, but DOES NOT assert
        clinical duplicate-therapy risk or safety hazards.
        """
        async with self._lock:
            normalized_name = drug_name_raw.strip().lower()
            for rec in self._medications.values():
                if rec.patient_id != patient_id:
                    continue
                # If normalized concept matches
                if normalized_medication_id and rec.normalized_medication_id == normalized_medication_id:
                    return True
                # If raw drug name matches exactly
                if rec.drug_name_raw.strip().lower() == normalized_name:
                    return True
            return False
