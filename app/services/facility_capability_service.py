"""Facility Capability Service (Phase 12).

Manages authoritative facility services and clinical capabilities.
Boundary: Avoids clinical inference; matches requirements only against explicitly recorded capabilities.
"""

from typing import Any
from app.repositories.facility_discovery_repository import FacilityDiscoveryRepository
from app.schemas.facility_result import FacilityDiscoveryResult


class FacilityCapabilityService:
    """Service evaluating authoritative facility capabilities and services."""

    def __init__(self, discovery_repo: FacilityDiscoveryRepository) -> None:
        self.discovery_repo = discovery_repo

    async def get_facility_capabilities(self, facility_id: str) -> dict[str, Any]:
        """Return registered services and capabilities for a facility."""
        return await self.discovery_repo.get_facility_metadata(facility_id)

    def filter_by_requirements(
        self,
        facilities: list[FacilityDiscoveryResult],
        required_service: str | None = None,
        required_capability: str | None = None,
    ) -> list[FacilityDiscoveryResult]:
        """Filter facility results matching explicit requirements without clinical extrapolation."""
        req_svc = required_service.strip().upper() if required_service else None
        req_cap = required_capability.strip().upper() if required_capability else None

        filtered: list[FacilityDiscoveryResult] = []
        for f in facilities:
            if req_svc and req_svc not in [s.upper() for s in f.services]:
                continue
            if req_cap and req_cap not in [c.upper() for c in f.capabilities]:
                continue
            filtered.append(f)

        return filtered
