"""Clinical Note Repository (Phase 10).

DATABASE TEAM DEPENDENCY — PHASE 10
=====================================
In-memory repository implementing the data contract for clinician-authored
clinical notes.

Expected PostgreSQL table: clinical_notes

See docs/phase-10-database-dependencies.md for full schema contract.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any

from app.repositories.base import BaseRepository
from app.schemas.clinical_workflow import ClinicalNoteRecord, ClinicalNoteType


class ClinicalNoteRepository(BaseRepository[ClinicalNoteRecord]):
    """Thread-safe in-memory repository for clinical notes."""

    def __init__(self, session: Any = None) -> None:
        super().__init__(session=session)
        self._notes: dict[str, ClinicalNoteRecord] = {}
        self._patient_notes: dict[str, list[str]] = {}
        self._lock = asyncio.Lock()

    async def get_by_id(self, id: str) -> ClinicalNoteRecord | None:
        async with self._lock:
            return self._notes.get(id)

    async def create(self, item: ClinicalNoteRecord) -> ClinicalNoteRecord:
        async with self._lock:
            self._notes[item.id] = item
            if item.patient_id not in self._patient_notes:
                self._patient_notes[item.patient_id] = []
            self._patient_notes[item.patient_id].append(item.id)
            return item

    async def update(self, id: str, item: ClinicalNoteRecord) -> ClinicalNoteRecord | None:
        async with self._lock:
            if id in self._notes:
                self._notes[id] = item
                return item
            return None

    async def delete(self, id: str) -> bool:
        async with self._lock:
            if id in self._notes:
                rec = self._notes.pop(id)
                patient_list = self._patient_notes.get(rec.patient_id, [])
                if id in patient_list:
                    patient_list.remove(id)
                return True
            return False

    async def list_by_patient(
        self,
        patient_id: str,
        limit: int = 50,
        offset: int = 0,
        note_type: ClinicalNoteType | None = None,
        encounter_id: str | None = None,
        clinician_id: str | None = None,
        signed_only: bool = False,
    ) -> tuple[list[ClinicalNoteRecord], int]:
        """List paginated clinical notes for a patient with optional filters."""
        async with self._lock:
            note_ids = self._patient_notes.get(patient_id, [])
            records: list[ClinicalNoteRecord] = []
            for nid in note_ids:
                n = self._notes.get(nid)
                if not n:
                    continue
                if note_type and n.note_type != note_type:
                    continue
                if encounter_id and n.encounter_id != encounter_id:
                    continue
                if clinician_id and n.clinician_id != clinician_id:
                    continue
                if signed_only and not n.is_signed:
                    continue
                records.append(n)

            records.sort(key=lambda x: x.created_at, reverse=True)
            total = len(records)
            return records[offset: offset + limit], total

    def clear(self) -> None:
        """Clear in-memory state for test isolation."""
        self._notes.clear()
        self._patient_notes.clear()
