"""Allergy data access repository.

DATABASE TEAM DEPENDENCY — PHASE 4
====================================
See app/schemas/allergy.py for the full entity field contract.

No medication-interaction checking or allergy inference in this repository.
"""

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository
from app.schemas.allergy import AllergySeverity, AllergyStatus
from app.schemas.clinical_history import ClinicalDataSource


@dataclass
class AllergyRecord:
    """Internal contract for an allergy entity."""
    id: str
    patient_id: str
    allergen: str
    severity: AllergySeverity
    status: AllergyStatus
    source: ClinicalDataSource
    created_at: datetime
    updated_at: datetime
    reaction: str | None = None
    recorded_by: str | None = None
    notes: str | None = None
    is_archived: bool = False


class AllergyRepository(BaseRepository[Any]):
    """Repository managing patient allergy records."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        super().__init__(session=session)  # type: ignore[arg-type]
        self._records: dict[str, AllergyRecord] = {}

    async def create(self, record: AllergyRecord) -> AllergyRecord:
        """Persist a new allergy record.

        NOTE FOR DATABASE TEAM: INSERT into allergies table.
        """
        self._records[record.id] = record
        return record

    async def update(self, allergy_id: str, updates: dict) -> AllergyRecord | None:
        """Partial update for an allergy record.

        NOTE FOR DATABASE TEAM: selective UPDATE; preserve unmodified fields.
        """
        record = self._records.get(allergy_id)
        if record is None:
            return None
        updated = replace(record, **updates, updated_at=datetime.now(timezone.utc))
        self._records[allergy_id] = updated
        return updated

    async def get_by_id(self, allergy_id: str) -> AllergyRecord | None:
        return self._records.get(allergy_id)

    async def list_by_patient(
        self,
        patient_id: str,
        include_archived: bool = False,
    ) -> list[AllergyRecord]:
        """List all allergy records for a patient.

        NOTE FOR DATABASE TEAM: indexed query on (patient_id, is_archived, status).
        """
        results = [r for r in self._records.values() if r.patient_id == patient_id]
        if not include_archived:
            results = [r for r in results if not r.is_archived]
        return sorted(results, key=lambda r: r.created_at, reverse=True)
