"""Clinical history data access repository.

DATABASE TEAM DEPENDENCY — PHASE 4
====================================
See app/schemas/clinical_history.py for the full entity field contract.

Clinical history records are append-oriented.
Existing entries should NOT be hard-deleted.
Archival (is_archived = True) is the soft-delete mechanism.
"""

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository
from app.schemas.clinical_history import ClinicalDataSource, ConditionStatus


@dataclass
class ClinicalHistoryRecord:
    """Internal contract for a clinical history entry."""
    id: str
    patient_id: str
    description: str
    condition_status: ConditionStatus
    source: ClinicalDataSource
    created_at: datetime
    updated_at: datetime
    onset_date: date | None = None
    resolved_date: date | None = None
    recorded_by: str | None = None
    notes: str | None = None
    is_archived: bool = False


class ClinicalHistoryRepository(BaseRepository[Any]):
    """Repository for patient clinical history entries."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        super().__init__(session=session)  # type: ignore[arg-type]
        self._records: dict[str, ClinicalHistoryRecord] = {}  # id → record

    async def create(self, record: ClinicalHistoryRecord) -> ClinicalHistoryRecord:
        """Append a new clinical history entry.

        NOTE FOR DATABASE TEAM: INSERT into clinical_history table.
        """
        self._records[record.id] = record
        return record

    async def update(self, entry_id: str, updates: dict) -> ClinicalHistoryRecord | None:
        """Apply a partial update to a clinical history entry.

        NOTE FOR DATABASE TEAM: selective UPDATE; preserve unmodified fields.
        """
        record = self._records.get(entry_id)
        if record is None:
            return None
        updated = replace(record, **updates, updated_at=datetime.now(timezone.utc))
        self._records[entry_id] = updated
        return updated

    async def get_by_id(self, entry_id: str) -> ClinicalHistoryRecord | None:
        return self._records.get(entry_id)

    async def list_by_patient(
        self,
        patient_id: str,
        include_archived: bool = False,
    ) -> list[ClinicalHistoryRecord]:
        """List all clinical history entries for a patient.

        NOTE FOR DATABASE TEAM: indexed query on (patient_id, is_archived).
        """
        results = [r for r in self._records.values() if r.patient_id == patient_id]
        if not include_archived:
            results = [r for r in results if not r.is_archived]
        return sorted(results, key=lambda r: r.created_at, reverse=True)

    async def archive(self, entry_id: str) -> ClinicalHistoryRecord | None:
        """Soft-delete a clinical history entry (set is_archived = True).

        Hard deletion is NOT supported. See phase requirements.
        """
        return await self.update(entry_id, {"is_archived": True})
