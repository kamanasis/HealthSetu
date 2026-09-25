"""Department Repository (Phase 11).

DATABASE TEAM DEPENDENCY — PHASE 11
=====================================
Thread-safe in-memory repository implementing the data contract for hospital/clinic departments.

Expected PostgreSQL table:
- `departments`

See docs/phase-11-database-dependencies.md for full schema contract.
"""

import asyncio
from typing import Any

from app.repositories.base import BaseRepository
from app.schemas.department import DepartmentRecord, DepartmentStatus


class DepartmentRepository(BaseRepository[DepartmentRecord]):
    """Thread-safe in-memory repository for departments."""

    def __init__(self, session: Any = None) -> None:
        super().__init__(session=session)
        self._departments: dict[str, DepartmentRecord] = {}
        # facility_id -> list of department_ids
        self._facility_departments: dict[str, list[str]] = {}
        self._lock = asyncio.Lock()

    async def get_by_id(self, id: str) -> DepartmentRecord | None:
        async with self._lock:
            return self._departments.get(id)

    async def create(self, department: DepartmentRecord) -> DepartmentRecord:
        async with self._lock:
            self._departments[department.id] = department
            if department.facility_id not in self._facility_departments:
                self._facility_departments[department.facility_id] = []
            if department.id not in self._facility_departments[department.facility_id]:
                self._facility_departments[department.facility_id].append(department.id)
            return department

    async def update(self, id: str, department: DepartmentRecord) -> DepartmentRecord | None:
        async with self._lock:
            if id in self._departments:
                old = self._departments[id]
                if old.facility_id != department.facility_id:
                    if old.facility_id in self._facility_departments and id in self._facility_departments[old.facility_id]:
                        self._facility_departments[old.facility_id].remove(id)
                    if department.facility_id not in self._facility_departments:
                        self._facility_departments[department.facility_id] = []
                    self._facility_departments[department.facility_id].append(id)
                self._departments[id] = department
                return department
            return None

    async def delete(self, id: str) -> bool:
        async with self._lock:
            if id in self._departments:
                dep = self._departments.pop(id)
                if dep.facility_id in self._facility_departments and id in self._facility_departments[dep.facility_id]:
                    self._facility_departments[dep.facility_id].remove(id)
                return True
            return False

    async def list_by_facility(
        self,
        facility_id: str,
        status: DepartmentStatus | None = None,
    ) -> list[DepartmentRecord]:
        """List departments belonging to a facility with optional status filter."""
        async with self._lock:
            dep_ids = self._facility_departments.get(facility_id, [])
            records: list[DepartmentRecord] = []
            for did in dep_ids:
                d = self._departments.get(did)
                if not d:
                    continue
                if status and d.status != status:
                    continue
                records.append(d)

            records.sort(key=lambda x: x.name)
            return records

    def clear(self) -> None:
        """Clear in-memory state for test isolation."""
        self._departments.clear()
        self._facility_departments.clear()
