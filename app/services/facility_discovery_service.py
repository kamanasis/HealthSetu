"""Facility Discovery Service (Phase 12).

Orchestrates patient-facing healthcare facility discovery, geographic proximity queries,
service/capability filtering, and triage integration.

Boundaries:
- Discovery != Diagnosis
- Discovery != Treatment Recommendation
- Discovery != Hospital Ranking
- No fabricated facility availability
"""

from typing import Any
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    FacilityDiscoveryDisabledException,
    PatientAccessDeniedException,
)
from app.core.logging import get_logger
from app.repositories.facility_discovery_repository import FacilityDiscoveryRepository
from app.repositories.triage_repository import TriageRepository
from app.schemas.audit import AuditEventType
from app.schemas.facility import FacilityStatus
from app.schemas.facility_result import FacilityDiscoveryResult
from app.schemas.user import AuthenticatedUserContext
from app.services.audit_service import AuditService
from app.services.facility_capability_service import FacilityCapabilityService
from app.services.geographic_service import GeographicService

logger = get_logger("app.services.facility_discovery")


class FacilityDiscoveryService:
    """Service discovering facilities based on location, capabilities, and clinical urgency."""

    def __init__(
        self,
        discovery_repo: FacilityDiscoveryRepository,
        capability_service: FacilityCapabilityService,
        geo_service: GeographicService,
        triage_repo: TriageRepository,
        audit_service: AuditService,
        settings: Settings | None = None,
    ) -> None:
        self.discovery_repo = discovery_repo
        self.capability_service = capability_service
        self.geo_service = geo_service
        self.triage_repo = triage_repo
        self.audit_service = audit_service
        self.settings = settings or get_settings()

    async def discover_facilities(
        self,
        user_context: AuthenticatedUserContext,
        latitude: float | None = None,
        longitude: float | None = None,
        radius_km: float | None = None,
        facility_type: str | None = None,
        required_service: str | None = None,
        required_capability: str | None = None,
        organization_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[FacilityDiscoveryResult], int]:
        """Discover healthcare facilities matching location, type, service, and capability criteria."""
        if not self.settings.FACILITY_DISCOVERY_ENABLED:
            raise FacilityDiscoveryDisabledException("Facility discovery is currently disabled by policy.")

        # 1. Validate geographic inputs
        self.geo_service.validate_coordinates(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
        )

        await self.audit_service.record(
            event_type=AuditEventType.FACILITY_DISCOVERY_STARTED,
            outcome="ALLOW",
            actor_id=user_context.user_id,
            action="facility:discover",
            resource_type="facility_discovery",
            metadata={
                "has_coordinates": latitude is not None and longitude is not None,
                "radius_km": radius_km,
                "facility_type": facility_type,
            },
        )

        try:
            # 2. Query candidates from repository (only ACTIVE facilities)
            candidates = await self.discovery_repo.query_facilities(
                facility_type=facility_type,
                required_service=required_service,
                required_capability=required_capability,
                organization_id=organization_id,
                status=FacilityStatus.ACTIVE,
            )

            # 3. Calculate distances and apply radius filtering
            filtered_results: list[FacilityDiscoveryResult] = []
            has_origin = latitude is not None and longitude is not None

            for fac in candidates:
                distance = None
                if has_origin and fac.latitude is not None and fac.longitude is not None:
                    distance = self.geo_service.calculate_distance_km(
                        origin_lat=latitude,
                        origin_lon=longitude,
                        dest_lat=fac.latitude,
                        dest_lon=fac.longitude,
                    )
                fac.distance_km = distance

                # If radius filtering requested, exclude facilities outside radius or without coordinates
                if radius_km is not None:
                    if distance is None or distance > radius_km:
                        continue

                filtered_results.append(fac)

            # 4. Sort: facilities with distance ascending, then by name
            filtered_results.sort(
                key=lambda x: (
                    x.distance_km if x.distance_km is not None else float("inf"),
                    x.name,
                )
            )

            total = len(filtered_results)
            paginated = filtered_results[offset : offset + limit]

            await self.audit_service.record(
                event_type=AuditEventType.FACILITY_DISCOVERY_COMPLETED,
                outcome="ALLOW",
                actor_id=user_context.user_id,
                action="facility:discover",
                resource_type="facility_discovery",
                metadata={"total_found": total, "returned": len(paginated)},
            )

            return paginated, total

        except Exception as e:
            await self.audit_service.record(
                event_type=AuditEventType.FACILITY_DISCOVERY_FAILED,
                outcome="DENY",
                actor_id=user_context.user_id,
                action="facility:discover",
                resource_type="facility_discovery",
                reason_code=type(e).__name__,
            )
            raise

    async def discover_for_patient(
        self,
        patient_id: str,
        user_context: AuthenticatedUserContext,
        latitude: float | None = None,
        longitude: float | None = None,
        radius_km: float | None = None,
        facility_type: str | None = None,
        required_service: str | None = None,
        required_capability: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[FacilityDiscoveryResult], int]:
        """Discover facilities in patient context, optionally integrating existing triage urgency."""
        # Retrieve latest triage assessment if present (without performing new triage or reinterpretation)
        triage_assessments, _ = await self.triage_repo.list_by_patient(patient_id=patient_id, limit=1)

        effective_service = required_service
        if triage_assessments and not effective_service:
            latest_triage = triage_assessments[0]
            urgency_val = getattr(latest_triage, "urgency", None) or getattr(latest_triage, "urgency_level", None)
            urgency_str = (
                urgency_val.value
                if hasattr(urgency_val, "value")
                else str(urgency_val or "")
            )
            if urgency_str == "EMERGENCY":
                effective_service = "EMERGENCY_CARE"

        return await self.discover_facilities(
            user_context=user_context,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            facility_type=facility_type,
            required_service=effective_service,
            required_capability=required_capability,
            limit=limit,
            offset=offset,
        )
