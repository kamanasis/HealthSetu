"""Organization Repository (Phase 11).

DATABASE TEAM DEPENDENCY — PHASE 11
=====================================
Thread-safe in-memory repository implementing the data contract for healthcare organizations
and clinician-organization memberships.

Expected PostgreSQL tables:
- `organizations`
- `clinician_organizations` (memberships)

See docs/phase-11-database-dependencies.md for full schema contract.
"""

import asyncio
from typing import Any

from app.repositories.base import BaseRepository
from app.schemas.organization import (
    ClinicianOrganizationMembershipRecord,
    OrganizationRecord,
    OrganizationStatus,
    OrganizationType,
)


class OrganizationRepository(BaseRepository[OrganizationRecord]):
    """Thread-safe in-memory repository for healthcare organizations and memberships."""

    def __init__(self, session: Any = None) -> None:
        super().__init__(session=session)
        self._organizations: dict[str, OrganizationRecord] = {}
        # clinician_id -> list of ClinicianOrganizationMembershipRecord
        self._clinician_memberships: dict[str, list[ClinicianOrganizationMembershipRecord]] = {}
        self._lock = asyncio.Lock()

    async def get_by_id(self, id: str) -> OrganizationRecord | None:
        async with self._lock:
            return self._organizations.get(id)

    async def create(self, org: OrganizationRecord) -> OrganizationRecord:
        async with self._lock:
            self._organizations[org.id] = org
            return org

    async def update(self, id: str, org: OrganizationRecord) -> OrganizationRecord | None:
        async with self._lock:
            if id in self._organizations:
                self._organizations[id] = org
                return org
            return None

    async def delete(self, id: str) -> bool:
        async with self._lock:
            if id in self._organizations:
                del self._organizations[id]
                return True
            return False

    async def list_organizations(
        self,
        limit: int = 50,
        offset: int = 0,
        name: str | None = None,
        status: OrganizationStatus | None = None,
        org_type: OrganizationType | None = None,
    ) -> tuple[list[OrganizationRecord], int]:
        """List paginated organizations with optional filtering."""
        async with self._lock:
            records = list(self._organizations.values())
            filtered: list[OrganizationRecord] = []
            for r in records:
                if status and r.status != status:
                    continue
                if org_type and r.organization_type != org_type:
                    continue
                if name and name.lower() not in r.name.lower():
                    continue
                filtered.append(r)

            filtered.sort(key=lambda x: x.created_at, reverse=True)
            total = len(filtered)
            return filtered[offset: offset + limit], total

    async def add_clinician_membership(
        self, membership: ClinicianOrganizationMembershipRecord
    ) -> ClinicianOrganizationMembershipRecord:
        """Associate a clinician with an organization."""
        async with self._lock:
            if membership.clinician_id not in self._clinician_memberships:
                self._clinician_memberships[membership.clinician_id] = []
            # Avoid duplicate active membership for same org
            existing = [
                m for m in self._clinician_memberships[membership.clinician_id]
                if m.organization_id == membership.organization_id
            ]
            if existing:
                self._clinician_memberships[membership.clinician_id].remove(existing[0])
            self._clinician_memberships[membership.clinician_id].append(membership)
            return membership

    async def get_clinician_memberships(
        self, clinician_id: str
    ) -> list[ClinicianOrganizationMembershipRecord]:
        """Retrieve all organization memberships for a clinician."""
        async with self._lock:
            return list(self._clinician_memberships.get(clinician_id, []))

    async def get_clinician_membership(
        self, clinician_id: str, organization_id: str
    ) -> ClinicianOrganizationMembershipRecord | None:
        """Retrieve membership record for a clinician and organization pair."""
        async with self._lock:
            memberships = self._clinician_memberships.get(clinician_id, [])
            for m in memberships:
                if m.organization_id == organization_id:
                    return m
            return None

    def clear(self) -> None:
        """Clear in-memory state for test isolation."""
        self._organizations.clear()
        self._clinician_memberships.clear()
