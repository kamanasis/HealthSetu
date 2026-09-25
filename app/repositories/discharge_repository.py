"""Discharge Instructions Repository (Phase 9).

DATABASE TEAM DEPENDENCY — PHASE 9
===================================
In-memory repository implementing the data contract for structured discharge
instructions and clinician verification states.
Expected PostgreSQL tables:
- clinical_discharge_instructions
- clinical_discharge_medications
- clinical_discharge_activities
- clinical_discharge_warning_signs
- clinical_discharge_follow_ups
"""

import asyncio
from datetime import datetime, timezone
from typing import Any
import uuid

from app.repositories.base import BaseRepository
from app.schemas.discharge import (
    DischargeInstructionRecord,
    DischargeVerificationStatus,
)


class DischargeRepository(BaseRepository[DischargeInstructionRecord]):
    """Thread-safe in-memory repository for discharge instructions."""

    def __init__(self, session: Any = None) -> None:
        super().__init__(session=session)
        self._records: dict[str, DischargeInstructionRecord] = {}
        self._patient_records: dict[str, list[str]] = {}
        self._document_map: dict[str, str] = {}  # document_id -> discharge_id
        self._lock = asyncio.Lock()

    async def get_by_id(self, id: str) -> DischargeInstructionRecord | None:
        async with self._lock:
            return self._records.get(id)

    async def get_by_document_id(self, document_id: str) -> DischargeInstructionRecord | None:
        async with self._lock:
            discharge_id = self._document_map.get(document_id)
            if discharge_id:
                return self._records.get(discharge_id)
            return None

    async def create(self, item: DischargeInstructionRecord) -> DischargeInstructionRecord:
        async with self._lock:
            self._records[item.id] = item
            if item.patient_id not in self._patient_records:
                self._patient_records[item.patient_id] = []
            self._patient_records[item.patient_id].append(item.id)
            self._document_map[item.document_id] = item.id
            return item

    async def update(self, id: str, item: DischargeInstructionRecord) -> DischargeInstructionRecord | None:
        async with self._lock:
            if id in self._records:
                self._records[id] = item
                return item
            return None

    async def delete(self, id: str) -> bool:
        async with self._lock:
            if id in self._records:
                rec = self._records.pop(id)
                if rec.patient_id in self._patient_records and id in self._patient_records[rec.patient_id]:
                    self._patient_records[rec.patient_id].remove(id)
                self._document_map.pop(rec.document_id, None)
                return True
            return False

    async def list_by_patient(
        self,
        patient_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[DischargeInstructionRecord], int]:
        """List paginated discharge instruction records for a patient."""
        async with self._lock:
            record_ids = self._patient_records.get(patient_id, [])
            records: list[DischargeInstructionRecord] = []
            for rid in record_ids:
                r = self._records.get(rid)
                if r:
                    records.append(r)

            records.sort(key=lambda x: x.created_at, reverse=True)
            total = len(records)
            paginated = records[offset : offset + limit]
            return paginated, total

    def clear(self) -> None:
        """Clear in-memory state for test isolation."""
        self._records.clear()
        self._patient_records.clear()
        self._document_map.clear()
