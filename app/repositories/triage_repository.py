"""Clinical Triage Repository (Phase 8).

DATABASE TEAM DEPENDENCY — PHASE 8
===================================
In-memory repository implementing the data contract for clinical triage
assessments and versioned evaluation results.
Expected PostgreSQL tables:
- clinical_triage_assessments
- clinical_triage_reasons
- clinical_triage_missing_info
"""

import asyncio
from datetime import datetime, timezone
from typing import Any
import uuid

from app.repositories.base import BaseRepository
from app.schemas.triage import (
    TriageAssessmentRecord,
    TriageUrgency,
    TriageStatus,
)


class TriageRepository(BaseRepository[TriageAssessmentRecord]):
    """Thread-safe in-memory repository for triage assessment records."""

    def __init__(self, session: Any = None) -> None:
        super().__init__(session=session)
        self._assessments: dict[str, TriageAssessmentRecord] = {}
        self._patient_assessments: dict[str, list[str]] = {}
        self._idempotency_index: dict[str, str] = {}  # f"{patient_id}:{key}" -> assessment_id
        self._lock = asyncio.Lock()

    async def get_by_id(self, id: str) -> TriageAssessmentRecord | None:
        async with self._lock:
            return self._assessments.get(id)

    async def create(self, item: TriageAssessmentRecord) -> TriageAssessmentRecord:
        async with self._lock:
            self._assessments[item.id] = item
            if item.patient_id not in self._patient_assessments:
                self._patient_assessments[item.patient_id] = []
            self._patient_assessments[item.patient_id].append(item.id)

            if item.idempotency_key:
                idx_key = f"{item.patient_id}:{item.idempotency_key}"
                self._idempotency_index[idx_key] = item.id

            return item

    async def update(self, id: str, item: TriageAssessmentRecord) -> TriageAssessmentRecord | None:
        async with self._lock:
            if id in self._assessments:
                self._assessments[id] = item
                return item
            return None

    async def delete(self, id: str) -> bool:
        async with self._lock:
            if id in self._assessments:
                rec = self._assessments.pop(id)
                if rec.patient_id in self._patient_assessments and id in self._patient_assessments[rec.patient_id]:
                    self._patient_assessments[rec.patient_id].remove(id)
                if rec.idempotency_key:
                    idx_key = f"{rec.patient_id}:{rec.idempotency_key}"
                    self._idempotency_index.pop(idx_key, None)
                return True
            return False

    async def get_by_idempotency_key(self, patient_id: str, idempotency_key: str) -> TriageAssessmentRecord | None:
        """Find an existing assessment by client-supplied idempotency key."""
        async with self._lock:
            idx_key = f"{patient_id}:{idempotency_key}"
            assessment_id = self._idempotency_index.get(idx_key)
            if assessment_id:
                return self._assessments.get(assessment_id)
            return None

    async def list_by_patient(
        self,
        patient_id: str,
        limit: int = 50,
        offset: int = 0,
        urgency: TriageUrgency | None = None,
        encounter_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> tuple[list[TriageAssessmentRecord], int]:
        """List paginated triage assessments for a patient with filtering."""
        async with self._lock:
            assessment_ids = self._patient_assessments.get(patient_id, [])
            records: list[TriageAssessmentRecord] = []
            for aid in assessment_ids:
                rec = self._assessments.get(aid)
                if not rec:
                    continue
                if urgency and rec.urgency != urgency:
                    continue
                if encounter_id and rec.encounter_id != encounter_id:
                    continue
                if start_date and rec.assessed_at < start_date:
                    continue
                if end_date and rec.assessed_at > end_date:
                    continue
                records.append(rec)

            records.sort(key=lambda r: r.assessed_at, reverse=True)
            total = len(records)
            paginated = records[offset : offset + limit]
            return paginated, total

    def clear(self) -> None:
        """Clear all stored state (for unit test isolation)."""
        self._assessments.clear()
        self._patient_assessments.clear()
        self._idempotency_index.clear()
