"""Encounter data access repository.

DATABASE TEAM DEPENDENCY — PHASE 4
====================================
See app/schemas/encounter.py for the full entity field contract.

Encounters provide a stable clinical context anchor.
No appointment scheduling, billing, or admission/discharge workflow here.
"""

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository
from app.schemas.clinical_history import ClinicalDataSource
from app.schemas.encounter import EncounterStatus, EncounterType


@dataclass
class EncounterRecord:
    """Internal contract for an encounter entity."""
    id: str
    patient_id: str
    encounter_type: EncounterType
    status: EncounterStatus
    start_time: datetime
    source: ClinicalDataSource
    created_at: datetime
    updated_at: datetime
    end_time: datetime | None = None
    provider_id: str | None = None
    organization_id: str | None = None
    external_id: str | None = None
    notes: str | None = None


class EncounterRepository(BaseRepository[Any]):
    """Repository managing clinical encounter records."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        super().__init__(session=session)  # type: ignore[arg-type]
        self._records: dict[str, EncounterRecord] = {}

    async def create(self, record: EncounterRecord) -> EncounterRecord:
        """Persist a new encounter record.

        NOTE FOR DATABASE TEAM: INSERT into encounters table.
        """
        self._records[record.id] = record
        return record

    async def update_status(
        self,
        encounter_id: str,
        new_status: EncounterStatus,
        end_time: datetime | None = None,
    ) -> EncounterRecord | None:
        """Update encounter status (e.g., IN_PROGRESS → COMPLETED).

        NOTE FOR DATABASE TEAM: selective UPDATE on status, end_time.
        """
        record = self._records.get(encounter_id)
        if record is None:
            return None
        updates: dict = {"status": new_status, "updated_at": datetime.now(timezone.utc)}
        if end_time is not None:
            updates["end_time"] = end_time
        updated = replace(record, **updates)
        self._records[encounter_id] = updated
        return updated

    async def get_by_id(self, encounter_id: str) -> EncounterRecord | None:
        return self._records.get(encounter_id)

    async def list_by_patient(
        self,
        patient_id: str,
        status_filter: EncounterStatus | None = None,
        limit: int = 50,
    ) -> list[EncounterRecord]:
        """List encounters for a patient, newest first.

        NOTE FOR DATABASE TEAM: indexed query on (patient_id, status, start_time DESC).
        """
        results = [r for r in self._records.values() if r.patient_id == patient_id]
        if status_filter:
            results = [r for r in results if r.status == status_filter]
        results.sort(key=lambda r: r.start_time, reverse=True)
        return results[:limit]

    async def list_active_by_patient(self, patient_id: str) -> list[EncounterRecord]:
        """Return encounters in PLANNED or IN_PROGRESS status for clinical summary."""
        active_statuses = {EncounterStatus.PLANNED, EncounterStatus.IN_PROGRESS}
        results = [
            r for r in self._records.values()
            if r.patient_id == patient_id and r.status in active_statuses
        ]
        return sorted(results, key=lambda r: r.start_time)
