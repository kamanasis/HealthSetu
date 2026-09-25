"""SBAR Clinical Summary Repository (Phase 8).

DATABASE TEAM DEPENDENCY — PHASE 8
===================================
In-memory repository implementing the data contract for SBAR clinical
communication records and fact verification reports.
Expected PostgreSQL tables:
- clinical_sbar_summaries
- clinical_sbar_fact_validations
"""

import asyncio
from datetime import datetime, timezone
from typing import Any
import uuid

from app.repositories.base import BaseRepository
from app.schemas.sbar import SBARRecord


class SBARRepository(BaseRepository[SBARRecord]):
    """Thread-safe in-memory repository for SBAR clinical records."""

    def __init__(self, session: Any = None) -> None:
        super().__init__(session=session)
        self._sbar_records: dict[str, SBARRecord] = {}
        self._patient_sbar_records: dict[str, list[str]] = {}
        self._assessment_sbar_map: dict[str, str] = {}  # assessment_id -> sbar_id
        self._lock = asyncio.Lock()

    async def get_by_id(self, id: str) -> SBARRecord | None:
        async with self._lock:
            return self._sbar_records.get(id)

    async def create(self, item: SBARRecord) -> SBARRecord:
        async with self._lock:
            self._sbar_records[item.id] = item
            if item.patient_id not in self._patient_sbar_records:
                self._patient_sbar_records[item.patient_id] = []
            self._patient_sbar_records[item.patient_id].append(item.id)
            self._assessment_sbar_map[item.assessment_id] = item.id
            return item

    async def update(self, id: str, item: SBARRecord) -> SBARRecord | None:
        async with self._lock:
            if id in self._sbar_records:
                self._sbar_records[id] = item
                return item
            return None

    async def delete(self, id: str) -> bool:
        async with self._lock:
            if id in self._sbar_records:
                rec = self._sbar_records.pop(id)
                if rec.patient_id in self._patient_sbar_records and id in self._patient_sbar_records[rec.patient_id]:
                    self._patient_sbar_records[rec.patient_id].remove(id)
                self._assessment_sbar_map.pop(rec.assessment_id, None)
                return True
            return False

    async def get_by_assessment_id(self, assessment_id: str) -> SBARRecord | None:
        """Find the latest SBAR generated for an assessment."""
        async with self._lock:
            sbar_id = self._assessment_sbar_map.get(assessment_id)
            if sbar_id:
                return self._sbar_records.get(sbar_id)
            return None

    async def list_by_patient(
        self,
        patient_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[SBARRecord], int]:
        """List paginated SBAR summaries for a patient."""
        async with self._lock:
            sbar_ids = self._patient_sbar_records.get(patient_id, [])
            records: list[SBARRecord] = []
            for sid in sbar_ids:
                rec = self._sbar_records.get(sid)
                if rec:
                    records.append(rec)

            records.sort(key=lambda r: r.created_at, reverse=True)
            total = len(records)
            paginated = records[offset : offset + limit]
            return paginated, total

    def clear(self) -> None:
        """Clear all stored state (for unit test isolation)."""
        self._sbar_records.clear()
        self._patient_sbar_records.clear()
        self._assessment_sbar_map.clear()
