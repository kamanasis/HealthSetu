"""Facility Discovery Repository (Phase 12).

DATABASE TEAM DEPENDENCY — PHASE 12
=====================================
Thread-safe in-memory repository implementing the data contract for facility discovery queries,
geographic coordinates, supported services, and clinical capabilities.

Expected PostgreSQL tables/relations:
- `facilities` (with geo coordinates or PostGIS extension)
- `facility_services`
- `facility_capabilities`
- `departments`

See docs/phase-12-database-dependencies.md for full schema contract.
"""

import asyncio
from typing import Any

from app.repositories.base import BaseRepository
from app.repositories.department_repository import DepartmentRepository
from app.repositories.facility_repository import FacilityRepository
from app.schemas.facility import FacilityRecord, FacilityStatus
from app.schemas.facility_result import FacilityDiscoveryResult


class FacilityDiscoveryRepository(BaseRepository[FacilityRecord]):
    """Repository accessing authoritative facility discovery data."""

    def __init__(
        self,
        facility_repo: FacilityRepository,
        department_repo: DepartmentRepository,
        session: Any = None,
    ) -> None:
        super().__init__(session=session)
        self.facility_repo = facility_repo
        self.department_repo = department_repo
        # facility_id -> {"latitude": float, "longitude": float, "services": set[str], "capabilities": set[str]}
        self._facility_metadata: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def set_facility_metadata(
        self,
        facility_id: str,
        latitude: float | None = None,
        longitude: float | None = None,
        services: list[str] | None = None,
        capabilities: list[str] | None = None,
    ) -> None:
        """Register or update authoritative metadata for a facility."""
        async with self._lock:
            meta = self._facility_metadata.get(facility_id, {})
            if latitude is not None:
                meta["latitude"] = latitude
            if longitude is not None:
                meta["longitude"] = longitude
            if services is not None:
                meta["services"] = [s.upper() for s in services]
            if capabilities is not None:
                meta["capabilities"] = [c.upper() for c in capabilities]
            self._facility_metadata[facility_id] = meta

    async def get_facility_metadata(self, facility_id: str) -> dict[str, Any]:
        """Retrieve registered metadata (coordinates, services, capabilities)."""
        async with self._lock:
            return dict(self._facility_metadata.get(facility_id, {}))

    async def query_facilities(
        self,
        facility_type: str | None = None,
        required_service: str | None = None,
        required_capability: str | None = None,
        organization_id: str | None = None,
        status: FacilityStatus | None = FacilityStatus.ACTIVE,
    ) -> list[FacilityDiscoveryResult]:
        """Query facilities matching database-backed filters without clinical inference."""
        async with self._lock:
            # Query base facilities from facility_repo
            all_facilities = list(self.facility_repo._facilities.values())
            results: list[FacilityDiscoveryResult] = []

            req_svc = required_service.strip().upper() if required_service else None
            req_cap = required_capability.strip().upper() if required_capability else None
            req_type = facility_type.strip().upper() if facility_type else None

            for fac in all_facilities:
                # Status filter
                if status and fac.status != status:
                    continue

                # Organization filter
                if organization_id and fac.organization_id != organization_id:
                    continue

                # Facility type filter
                if req_type and fac.facility_type.value.upper() != req_type:
                    continue

                # Retrieve metadata & departments
                meta = self._facility_metadata.get(fac.id, {})

                # Also inspect operational_metadata if present on facility
                op_meta = fac.operational_metadata or {}
                lat = meta.get("latitude", op_meta.get("latitude"))
                lon = meta.get("longitude", op_meta.get("longitude"))

                services = list(meta.get("services") or op_meta.get("services") or [])
                services = [s.upper() for s in services]

                capabilities = list(meta.get("capabilities") or op_meta.get("capabilities") or [])
                capabilities = [c.upper() for c in capabilities]

                # Check required service
                if req_svc and req_svc not in services:
                    continue

                # Check required capability
                if req_cap and req_cap not in capabilities:
                    continue

                # Retrieve registered departments
                dep_ids = self.department_repo._facility_departments.get(fac.id, [])
                departments = [
                    self.department_repo._departments[d].name
                    for d in dep_ids
                    if d in self.department_repo._departments
                ]

                results.append(
                    FacilityDiscoveryResult(
                        facility_id=fac.id,
                        organization_id=fac.organization_id,
                        name=fac.name,
                        facility_type=fac.facility_type.value,
                        status=fac.status.value,
                        address=fac.address,
                        phone=fac.phone,
                        email=fac.email,
                        latitude=lat,
                        longitude=lon,
                        distance_km=None,  # Computed by GeographicService
                        services=services,
                        capabilities=capabilities,
                        departments=departments,
                        provenance=fac.provenance,
                    )
                )

            return results

    def clear(self) -> None:
        """Clear registered discovery metadata."""
        self._facility_metadata.clear()
