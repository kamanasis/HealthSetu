"""Facility Repository (Phase 11).

DATABASE TEAM DEPENDENCY — PHASE 11
=====================================
Thread-safe in-memory repository implementing the data contract for healthcare facilities
and clinician-facility memberships.

Expected PostgreSQL tables:
- `facilities`
- `clinician_facilities` (memberships)

See docs/phase-11-database-dependencies.md for full schema contract.
"""

import asyncio
from typing import Any

from app.repositories.base import BaseRepository
from app.schemas.facility import (
    ClinicianFacilityMembershipRecord,
    FacilityRecord,
    FacilityStatus,
    FacilityType,
)


class FacilityRepository(BaseRepository[FacilityRecord]):
    """Thread-safe in-memory repository for healthcare facilities and memberships."""

    def __init__(self, session: Any = None) -> None:
        super().__init__(session=session)
        self._facilities: dict[str, FacilityRecord] = {}
        # organization_id -> list of facility_ids
        self._org_facilities: dict[str, list[str]] = {}
        # clinician_id -> list of ClinicianFacilityMembershipRecord
        self._clinician_memberships: dict[str, list[ClinicianFacilityMembershipRecord]] = {}
        self._lock = asyncio.Lock()

    async def get_by_id(self, id: str) -> FacilityRecord | None:
        async with self._lock:
            return self._facilities.get(id)

    async def create(self, facility: FacilityRecord) -> FacilityRecord:
        async with self._lock:
            self._facilities[facility.id] = facility
            if facility.organization_id not in self._org_facilities:
                self._org_facilities[facility.organization_id] = []
            if facility.id not in self._org_facilities[facility.organization_id]:
                self._org_facilities[facility.organization_id].append(facility.id)
            return facility

    async def update(self, id: str, facility: FacilityRecord) -> FacilityRecord | None:
        async with self._lock:
            if id in self._facilities:
                old = self._facilities[id]
                # If organization_id changed, update organization index
                if old.organization_id != facility.organization_id:
                    if old.organization_id in self._org_facilities and id in self._org_facilities[old.organization_id]:
                        self._org_facilities[old.organization_id].remove(id)
                    if facility.organization_id not in self._org_facilities:
                        self._org_facilities[facility.organization_id] = []
                    self._org_facilities[facility.organization_id].append(id)
                self._facilities[id] = facility
                return facility
            return None

    async def delete(self, id: str) -> bool:
        async with self._lock:
            if id in self._facilities:
                facility = self._facilities.pop(id)
                if facility.organization_id in self._org_facilities and id in self._org_facilities[facility.organization_id]:
                    self._org_facilities[facility.organization_id].remove(id)
                return True
            return False

    async def list_by_organization(
        self,
        organization_id: str,
        limit: int = 50,
        offset: int = 0,
        status: FacilityStatus | None = None,
        facility_type: FacilityType | None = None,
    ) -> tuple[list[FacilityRecord], int]:
        """List facilities belonging to a specific organization."""
        async with self._lock:
            fac_ids = self._org_facilities.get(organization_id, [])
            filtered: list[FacilityRecord] = []
            for fid in fac_ids:
                f = self._facilities.get(fid)
                if not f:
                    continue
                if status and f.status != status:
                    continue
                if facility_type and f.facility_type != facility_type:
                    continue
                filtered.append(f)

            filtered.sort(key=lambda x: x.created_at, reverse=True)
            total = len(filtered)
            return filtered[offset: offset + limit], total

    async def list_facilities(
        self,
        limit: int = 50,
        offset: int = 0,
        name: str | None = None,
        organization_id: str | None = None,
        facility_type: FacilityType | None = None,
        status: FacilityStatus | None = None,
    ) -> tuple[list[FacilityRecord], int]:
        """Search and list facilities with flexible filtering."""
        async with self._lock:
            records = list(self._facilities.values())
            filtered: list[FacilityRecord] = []
            for r in records:
                if organization_id and r.organization_id != organization_id:
                    continue
                if status and r.status != status:
                    continue
                if facility_type and r.facility_type != facility_type:
                    continue
                if name and name.lower() not in r.name.lower():
                    continue
                filtered.append(r)

            filtered.sort(key=lambda x: x.created_at, reverse=True)
            total = len(filtered)
            return filtered[offset: offset + limit], total

    async def add_clinician_membership(
        self, membership: ClinicianFacilityMembershipRecord
    ) -> ClinicianFacilityMembershipRecord:
        """Associate a clinician with a facility."""
        async with self._lock:
            if membership.clinician_id not in self._clinician_memberships:
                self._clinician_memberships[membership.clinician_id] = []
            # Avoid duplicate active membership for same facility
            existing = [
                m for m in self._clinician_memberships[membership.clinician_id]
                if m.facility_id == membership.facility_id
            ]
            if existing:
                self._clinician_memberships[membership.clinician_id].remove(existing[0])
            self._clinician_memberships[membership.clinician_id].append(membership)
            return membership

    async def get_clinician_memberships(
        self, clinician_id: str
    ) -> list[ClinicianFacilityMembershipRecord]:
        """Retrieve all facility memberships for a clinician."""
        async with self._lock:
            return list(self._clinician_memberships.get(clinician_id, []))

    async def get_clinician_membership(
        self, clinician_id: str, facility_id: str
    ) -> ClinicianFacilityMembershipRecord | None:
        """Retrieve membership record for a clinician and facility pair."""
        async with self._lock:
            memberships = self._clinician_memberships.get(clinician_id, [])
            for m in memberships:
                if m.facility_id == facility_id:
                    return m
            return None

    def clear(self) -> None:
        """Clear in-memory state for test isolation."""
        self._facilities.clear()
        self._org_facilities.clear()
        self._clinician_memberships.clear()
