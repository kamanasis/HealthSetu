"""Facility Discovery API Endpoints (Phase 12).

Provides patient-facing and patient-context healthcare facility discovery.
Critical boundaries:
- Discovery != Diagnosis
- Discovery != Treatment Recommendation
- Discovery != Hospital Ranking
- No fabricated facility availability
"""

from typing import Annotated
from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import (
    get_authorization_service,
    get_current_user,
    get_facility_discovery_service,
    get_patient_service,
    require_permission,
    verify_patient_access,
)
from app.core.logging import request_id_ctx_var
from app.core.policies import Permission
from app.schemas.facility_discovery import (
    FacilityDiscoveryQueryParams,
    FacilityDiscoveryResponse,
)
from app.schemas.response import StandardSuccessResponse
from app.schemas.user import AuthenticatedUserContext
from app.services.authorization_service import AuthorizationService
from app.services.facility_discovery_service import FacilityDiscoveryService
from app.services.patient_service import PatientService

router = APIRouter(tags=["Facility Discovery"])


def _req_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request_id_ctx_var.get() or "unknown"


# ============================================================================
# Public / Patient-facing Facility Discovery
# ============================================================================

@router.get(
    "/facilities/discover",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[FacilityDiscoveryResponse],
    summary="Discover healthcare facilities",
    description="Discover facilities by location proximity, facility type, supported services, and capabilities.",
)
async def discover_facilities(
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(require_permission(Permission.FACILITY_DISCOVER))],
    discovery_service: Annotated[FacilityDiscoveryService, Depends(get_facility_discovery_service)],
    latitude: Annotated[float | None, Query(description="Caller latitude coordinate")] = None,
    longitude: Annotated[float | None, Query(description="Caller longitude coordinate")] = None,
    radius_km: Annotated[float | None, Query(description="Proximity search radius in kilometers")] = None,
    facility_type: Annotated[str | None, Query(description="Filter by facility type (e.g. HOSPITAL, CLINIC)")] = None,
    required_service: Annotated[str | None, Query(description="Filter by required service (e.g. EMERGENCY_CARE)")] = None,
    required_capability: Annotated[str | None, Query(description="Filter by capability (e.g. ICU)")] = None,
    organization_id: Annotated[str | None, Query(description="Filter by parent organization ID")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Page limit")] = 50,
    offset: Annotated[int, Query(ge=0, description="Page offset")] = 0,
) -> StandardSuccessResponse[FacilityDiscoveryResponse]:
    items, total = await discovery_service.discover_facilities(
        user_context=current_user,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        facility_type=facility_type,
        required_service=required_service,
        required_capability=required_capability,
        organization_id=organization_id,
        limit=limit,
        offset=offset,
    )

    return StandardSuccessResponse(
        data=FacilityDiscoveryResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            origin_latitude=latitude,
            origin_longitude=longitude,
            radius_km=radius_km,
        ),
        request_id=_req_id(request),
    )


# ============================================================================
# Patient-Specific Contextual Facility Discovery
# ============================================================================

@router.get(
    "/patients/{patient_id}/facilities/discover",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[FacilityDiscoveryResponse],
    summary="Discover facilities in patient context",
    description="Discover facilities tailored to patient context, optionally utilizing existing triage urgency.",
)
async def discover_facilities_for_patient(
    request: Request,
    patient_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    discovery_service: Annotated[FacilityDiscoveryService, Depends(get_facility_discovery_service)],
    latitude: Annotated[float | None, Query(description="Search origin latitude")] = None,
    longitude: Annotated[float | None, Query(description="Search origin longitude")] = None,
    radius_km: Annotated[float | None, Query(description="Radius in kilometers")] = None,
    facility_type: Annotated[str | None, Query(description="Filter by facility type")] = None,
    required_service: Annotated[str | None, Query(description="Filter by required service")] = None,
    required_capability: Annotated[str | None, Query(description="Filter by required capability")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Page limit")] = 50,
    offset: Annotated[int, Query(ge=0, description="Page offset")] = 0,
) -> StandardSuccessResponse[FacilityDiscoveryResponse]:
    # 1. Authorize patient access
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="facility_discovery:read",
        resource_type="facility_discovery",
        consent_scope="clinical_records",
    )

    # 2. Perform patient contextual discovery
    items, total = await discovery_service.discover_for_patient(
        patient_id=patient_id,
        user_context=current_user,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        facility_type=facility_type,
        required_service=required_service,
        required_capability=required_capability,
        limit=limit,
        offset=offset,
    )

    return StandardSuccessResponse(
        data=FacilityDiscoveryResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            origin_latitude=latitude,
            origin_longitude=longitude,
            radius_km=radius_km,
        ),
        request_id=_req_id(request),
    )
