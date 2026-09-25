"""Clinical Plan Repository (Phase 10).

DATABASE TEAM DEPENDENCY — PHASE 10
=====================================
In-memory repository implementing the data contract for clinician-authored
clinical plans.

Expected PostgreSQL table: clinical_plans

See docs/phase-10-database-dependencies.md for full schema contract.
"""

import asyncio
from typing import Any

from app.repositories.base import BaseRepository
from app.schemas.clinical_workflow import ClinicalPlanRecord, ClinicalPlanStatus, ClinicalPlanType


class ClinicalPlanRepository(BaseRepository[ClinicalPlanRecord]):
    """Thread-safe in-memory repository for clinical plans."""

    def __init__(self, session: Any = None) -> None:
        super().__init__(session=session)
        self._plans: dict[str, ClinicalPlanRecord] = {}
        self._patient_plans: dict[str, list[str]] = {}
        self._lock = asyncio.Lock()

    async def get_by_id(self, id: str) -> ClinicalPlanRecord | None:
        async with self._lock:
            return self._plans.get(id)

    async def create(self, item: ClinicalPlanRecord) -> ClinicalPlanRecord:
        async with self._lock:
            self._plans[item.id] = item
            if item.patient_id not in self._patient_plans:
                self._patient_plans[item.patient_id] = []
            self._patient_plans[item.patient_id].append(item.id)
            return item

    async def update(self, id: str, item: ClinicalPlanRecord) -> ClinicalPlanRecord | None:
        async with self._lock:
            if id in self._plans:
                self._plans[id] = item
                return item
            return None

    async def delete(self, id: str) -> bool:
        async with self._lock:
            if id in self._plans:
                rec = self._plans.pop(id)
                patient_list = self._patient_plans.get(rec.patient_id, [])
                if id in patient_list:
                    patient_list.remove(id)
                return True
            return False

    async def list_by_patient(
        self,
        patient_id: str,
        limit: int = 50,
        offset: int = 0,
        plan_type: ClinicalPlanType | None = None,
        status: ClinicalPlanStatus | None = None,
        encounter_id: str | None = None,
        clinician_id: str | None = None,
    ) -> tuple[list[ClinicalPlanRecord], int]:
        """List paginated clinical plans for a patient with optional filters."""
        async with self._lock:
            ids = self._patient_plans.get(patient_id, [])
            records: list[ClinicalPlanRecord] = []
            for pid in ids:
                p = self._plans.get(pid)
                if not p:
                    continue
                if plan_type and p.plan_type != plan_type:
                    continue
                if status and p.status != status:
                    continue
                if encounter_id and p.encounter_id != encounter_id:
                    continue
                if clinician_id and p.clinician_id != clinician_id:
                    continue
                records.append(p)

            records.sort(key=lambda x: x.created_at, reverse=True)
            total = len(records)
            return records[offset: offset + limit], total

    def clear(self) -> None:
        """Clear in-memory state for test isolation."""
        self._plans.clear()
        self._patient_plans.clear()
