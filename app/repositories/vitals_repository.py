"""Vitals data access repository.

DATABASE TEAM DEPENDENCY — PHASE 4
====================================
See app/schemas/vital.py for the full entity field contract.

Vitals are append-only.
Historical measurements must NOT be overwritten or deleted.
Each recording creates a new immutable row.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository
from app.schemas.vital import VitalSource, VitalType


@dataclass(frozen=True)
class VitalRecord:
    """Immutable vital measurement entity — append-only."""
    id: str
    patient_id: str
    vital_type: VitalType
    value: float
    unit: str
    measured_at: datetime
    source: VitalSource
    created_at: datetime
    recorded_by: str | None = None
    device_id: str | None = None
    notes: str | None = None


class VitalsRepository(BaseRepository[Any]):
    """Repository managing patient vital measurement records.

    Append-only: vitals are never updated or deleted.
    """

    def __init__(self, session: AsyncSession | None = None) -> None:
        super().__init__(session=session)  # type: ignore[arg-type]
        self._records: dict[str, VitalRecord] = {}

    async def append(self, record: VitalRecord) -> VitalRecord:
        """Append a new vital measurement.

        NOTE FOR DATABASE TEAM: INSERT into vitals table.
        Vitals must be append-only — no UPDATE/DELETE semantics.
        """
        self._records[record.id] = record
        return record

    async def get_by_id(self, vital_id: str) -> VitalRecord | None:
        return self._records.get(vital_id)

    async def list_by_patient(
        self,
        patient_id: str,
        vital_type: VitalType | None = None,
        limit: int = 100,
    ) -> list[VitalRecord]:
        """List vital measurements for a patient, newest first.

        NOTE FOR DATABASE TEAM:
            indexed query on (patient_id, vital_type, measured_at DESC) with LIMIT.
        """
        results = [r for r in self._records.values() if r.patient_id == patient_id]
        if vital_type:
            results = [r for r in results if r.vital_type == vital_type]
        results.sort(key=lambda r: r.measured_at, reverse=True)
        return results[:limit]

    async def get_latest_per_type(self, patient_id: str) -> dict[VitalType, VitalRecord]:
        """Return the most recent measurement for each vital type.

        Used to populate clinical summary recent vitals.

        NOTE FOR DATABASE TEAM: use DISTINCT ON (vital_type) ORDER BY measured_at DESC
        """
        latest: dict[VitalType, VitalRecord] = {}
        for record in self._records.values():
            if record.patient_id != patient_id:
                continue
            existing = latest.get(record.vital_type)
            if existing is None or record.measured_at > existing.measured_at:
                latest[record.vital_type] = record
        return latest
