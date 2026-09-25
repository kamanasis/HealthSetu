"""Symptom Intake Repository (Phase 8).

DATABASE TEAM DEPENDENCY — PHASE 8
===================================
In-memory repository implementing the data contract for structured symptoms
and intake sessions.
Expected PostgreSQL tables:
- patient_symptom_intakes
- patient_symptoms
"""

import asyncio
from datetime import datetime, timezone
from typing import Any
import uuid

from app.repositories.base import BaseRepository
from app.schemas.symptom import SymptomRecord, SymptomSource, SymptomSeverity


class SymptomRepository(BaseRepository[SymptomRecord]):
    """Thread-safe in-memory repository for symptom records and intake sessions."""

    def __init__(self, session: Any = None) -> None:
        super().__init__(session=session)
        self._symptoms: dict[str, SymptomRecord] = {}
        self._intake_sessions: dict[str, dict[str, Any]] = {}
        self._patient_symptoms: dict[str, list[str]] = {}
        self._lock = asyncio.Lock()

    async def get_by_id(self, id: str) -> SymptomRecord | None:
        async with self._lock:
            return self._symptoms.get(id)

    async def create(self, item: SymptomRecord) -> SymptomRecord:
        async with self._lock:
            self._symptoms[item.id] = item
            if item.patient_id not in self._patient_symptoms:
                self._patient_symptoms[item.patient_id] = []
            self._patient_symptoms[item.patient_id].append(item.id)
            return item

    async def update(self, id: str, item: SymptomRecord) -> SymptomRecord | None:
        async with self._lock:
            if id in self._symptoms:
                self._symptoms[id] = item
                return item
            return None

    async def delete(self, id: str) -> bool:
        async with self._lock:
            if id in self._symptoms:
                sym = self._symptoms.pop(id)
                if sym.patient_id in self._patient_symptoms and id in self._patient_symptoms[sym.patient_id]:
                    self._patient_symptoms[sym.patient_id].remove(id)
                return True
            return False

    async def create_intake_session(
        self,
        intake_id: str,
        patient_id: str,
        encounter_id: str | None,
        source: SymptomSource,
        symptoms: list[SymptomRecord],
        notes: str | None,
    ) -> dict[str, Any]:
        """Record an atomic intake session containing multiple symptoms."""
        async with self._lock:
            # Store symptoms
            for s in symptoms:
                self._symptoms[s.id] = s
                if patient_id not in self._patient_symptoms:
                    self._patient_symptoms[patient_id] = []
                if s.id not in self._patient_symptoms[patient_id]:
                    self._patient_symptoms[patient_id].append(s.id)

            session_record = {
                "intake_id": intake_id,
                "patient_id": patient_id,
                "encounter_id": encounter_id,
                "source": source,
                "symptoms": symptoms,
                "notes": notes,
                "created_at": datetime.now(timezone.utc),
            }
            self._intake_sessions[intake_id] = session_record
            return session_record

    async def get_intake_session(self, intake_id: str) -> dict[str, Any] | None:
        """Retrieve an intake session by ID."""
        async with self._lock:
            return self._intake_sessions.get(intake_id)

    async def list_by_patient(
        self,
        patient_id: str,
        limit: int = 50,
        offset: int = 0,
        source: SymptomSource | None = None,
        encounter_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> tuple[list[SymptomRecord], int]:
        """List paginated symptoms for a patient with filtering."""
        async with self._lock:
            symptom_ids = self._patient_symptoms.get(patient_id, [])
            records: list[SymptomRecord] = []
            for sid in symptom_ids:
                sym = self._symptoms.get(sid)
                if not sym:
                    continue
                if source and sym.source != source:
                    continue
                if encounter_id and sym.encounter_id != encounter_id:
                    continue
                if start_date and sym.created_at < start_date:
                    continue
                if end_date and sym.created_at > end_date:
                    continue
                records.append(sym)

            # Sort descending by creation date
            records.sort(key=lambda s: s.created_at, reverse=True)
            total = len(records)
            paginated = records[offset : offset + limit]
            return paginated, total

    def clear(self) -> None:
        """Clear all stored state (for unit test isolation)."""
        self._symptoms.clear()
        self._intake_sessions.clear()
        self._patient_symptoms.clear()
