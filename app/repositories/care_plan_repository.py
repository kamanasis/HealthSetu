"""Care Plan Repository (Phase 9).

DATABASE TEAM DEPENDENCY — PHASE 9
===================================
In-memory repository implementing the data contract for personalized
care plans, daily tasks, and goals.
Expected PostgreSQL tables:
- patient_care_plans
- patient_care_plan_goals
- patient_care_plan_tasks
"""

import asyncio
from datetime import datetime, timezone
from typing import Any
import uuid

from app.repositories.base import BaseRepository
from app.schemas.care_plan import (
    CarePlanRecord,
    CarePlanStatus,
)


class CarePlanRepository(BaseRepository[CarePlanRecord]):
    """Thread-safe in-memory repository for patient care plans."""

    def __init__(self, session: Any = None) -> None:
        super().__init__(session=session)
        self._care_plans: dict[str, CarePlanRecord] = {}
        self._patient_care_plans: dict[str, list[str]] = {}
        self._lock = asyncio.Lock()

    async def get_by_id(self, id: str) -> CarePlanRecord | None:
        async with self._lock:
            return self._care_plans.get(id)

    async def create(self, item: CarePlanRecord) -> CarePlanRecord:
        async with self._lock:
            self._care_plans[item.id] = item
            if item.patient_id not in self._patient_care_plans:
                self._patient_care_plans[item.patient_id] = []
            self._patient_care_plans[item.patient_id].append(item.id)
            return item

    async def update(self, id: str, item: CarePlanRecord) -> CarePlanRecord | None:
        async with self._lock:
            if id in self._care_plans:
                self._care_plans[id] = item
                return item
            return None

    async def delete(self, id: str) -> bool:
        async with self._lock:
            if id in self._care_plans:
                rec = self._care_plans.pop(id)
                if rec.patient_id in self._patient_care_plans and id in self._patient_care_plans[rec.patient_id]:
                    self._patient_care_plans[rec.patient_id].remove(id)
                return True
            return False

    async def list_by_patient(
        self,
        patient_id: str,
        limit: int = 50,
        offset: int = 0,
        status: CarePlanStatus | None = None,
    ) -> tuple[list[CarePlanRecord], int]:
        """List paginated care plans for a patient with status filtering."""
        async with self._lock:
            plan_ids = self._patient_care_plans.get(patient_id, [])
            records: list[CarePlanRecord] = []
            for pid in plan_ids:
                p = self._care_plans.get(pid)
                if not p:
                    continue
                if status and p.status != status:
                    continue
                records.append(p)

            records.sort(key=lambda x: x.created_at, reverse=True)
            total = len(records)
            paginated = records[offset : offset + limit]
            return paginated, total

    def clear(self) -> None:
        """Clear in-memory state for test isolation."""
        self._care_plans.clear()
        self._patient_care_plans.clear()
