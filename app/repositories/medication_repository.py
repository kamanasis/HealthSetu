"""Canonical medication repository.

DATABASE TEAM DEPENDENCY — PHASE 6
===================================
In-memory repository implementing the data contract for canonical normalized medications.
Expected PostgreSQL table:
- medications
"""

import asyncio
from datetime import datetime, timezone
import uuid
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.repositories.base import BaseRepository


class MedicationRecord(BaseModel):
    """Canonical normalized medication concept record."""
    model_config = ConfigDict(frozen=True)

    id: str
    canonical_name: str
    generic_name: str | None = None
    brand_name: str | None = None
    terminology_system: str
    terminology_code: str
    strength: str | None = None
    dosage_form: str | None = None
    route: str | None = None
    provider: str
    provider_version: str | None = None
    confidence_score: float = 1.0
    created_at: datetime


class MedicationRepository(BaseRepository[Any]):
    """Repository managing canonical normalized medication entities."""

    def __init__(self, session: Any = None) -> None:
        super().__init__(session=session)
        self._medications: dict[str, MedicationRecord] = {}
        # Index on (terminology_system, terminology_code, strength, dosage_form)
        self._concept_index: dict[tuple[str, str, str | None, str | None], str] = {}
        self._lock = asyncio.Lock()

    def clear(self) -> None:
        """Clear in-memory state for testing."""
        self._medications.clear()
        self._concept_index.clear()

    async def get_by_id(self, medication_id: str) -> MedicationRecord | None:
        """Retrieve canonical medication record by primary key."""
        async with self._lock:
            return self._medications.get(medication_id)

    async def find_by_terminology(
        self,
        terminology_system: str,
        terminology_code: str,
        strength: str | None = None,
        dosage_form: str | None = None,
    ) -> MedicationRecord | None:
        """Find existing canonical medication by terminology code and form."""
        async with self._lock:
            key = (terminology_system.upper(), terminology_code, strength, dosage_form)
            med_id = self._concept_index.get(key)
            if med_id:
                return self._medications.get(med_id)
            return None

    async def save_medication(self, record: MedicationRecord) -> MedicationRecord:
        """Persist or return existing canonical medication concept (idempotent)."""
        async with self._lock:
            key = (
                record.terminology_system.upper(),
                record.terminology_code,
                record.strength,
                record.dosage_form,
            )
            existing_id = self._concept_index.get(key)
            if existing_id and existing_id in self._medications:
                return self._medications[existing_id]

            self._medications[record.id] = record
            self._concept_index[key] = record.id
            return record
