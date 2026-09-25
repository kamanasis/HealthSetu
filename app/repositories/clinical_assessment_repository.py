"""Clinical Assessment Repository (Phase 10).

DATABASE TEAM DEPENDENCY — PHASE 10
=====================================
In-memory repository implementing the data contract for clinician-authored
clinical assessments.

Expected PostgreSQL table: clinical_assessments

See docs/phase-10-database-dependencies.md for full schema contract.
"""

import asyncio
from typing import Any

from app.repositories.base import BaseRepository
from app.schemas.clinical_workflow import ClinicalAssessmentRecord, ClinicalAssessmentType


class ClinicalAssessmentRepository(BaseRepository[ClinicalAssessmentRecord]):
    """Thread-safe in-memory repository for clinical assessments."""

    def __init__(self, session: Any = None) -> None:
        super().__init__(session=session)
        self._assessments: dict[str, ClinicalAssessmentRecord] = {}
        self._patient_assessments: dict[str, list[str]] = {}
        self._lock = asyncio.Lock()

    async def get_by_id(self, id: str) -> ClinicalAssessmentRecord | None:
        async with self._lock:
            return self._assessments.get(id)

    async def create(self, item: ClinicalAssessmentRecord) -> ClinicalAssessmentRecord:
        async with self._lock:
            self._assessments[item.id] = item
            if item.patient_id not in self._patient_assessments:
                self._patient_assessments[item.patient_id] = []
            self._patient_assessments[item.patient_id].append(item.id)
            return item

    async def update(self, id: str, item: ClinicalAssessmentRecord) -> ClinicalAssessmentRecord | None:
        async with self._lock:
            if id in self._assessments:
                self._assessments[id] = item
                return item
            return None

    async def delete(self, id: str) -> bool:
        async with self._lock:
            if id in self._assessments:
                rec = self._assessments.pop(id)
                patient_list = self._patient_assessments.get(rec.patient_id, [])
                if id in patient_list:
                    patient_list.remove(id)
                return True
            return False

    async def list_by_patient(
        self,
        patient_id: str,
        limit: int = 50,
        offset: int = 0,
        assessment_type: ClinicalAssessmentType | None = None,
        encounter_id: str | None = None,
        clinician_id: str | None = None,
        finalized_only: bool = False,
    ) -> tuple[list[ClinicalAssessmentRecord], int]:
        """List paginated clinical assessments for a patient with optional filters."""
        async with self._lock:
            ids = self._patient_assessments.get(patient_id, [])
            records: list[ClinicalAssessmentRecord] = []
            for aid in ids:
                a = self._assessments.get(aid)
                if not a:
                    continue
                if assessment_type and a.assessment_type != assessment_type:
                    continue
                if encounter_id and a.encounter_id != encounter_id:
                    continue
                if clinician_id and a.clinician_id != clinician_id:
                    continue
                if finalized_only and not a.is_finalized:
                    continue
                records.append(a)

            records.sort(key=lambda x: x.created_at, reverse=True)
            total = len(records)
            return records[offset: offset + limit], total

    def clear(self) -> None:
        """Clear in-memory state for test isolation."""
        self._assessments.clear()
        self._patient_assessments.clear()
