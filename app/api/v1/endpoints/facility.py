"""Healthcare Facility API Endpoints (Phase 11).

Provides routes for healthcare facilities, department listings, facility search,
and clinician facility context.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import (
    get_current_user,
    get_facility_service,
    require_permission,
    require_role,
)
from app.core.logging import request_id_ctx_var
from app.core.policies import Permission
from app.schemas.department import DepartmentListResponse, DepartmentStatus
from app.schemas.facility import (
    FacilityListResponse,
    FacilityResponse,
    FacilityStatus,
    FacilityType,
)
from app.schemas.facility_context import ClinicianFacilityContextResponse
from app.schemas.response import StandardSuccessResponse
from app.schemas.user import AuthenticatedUserContext
from app.services.facility_service import FacilityService

router = APIRouter(tags=["Healthcare Facilities"])


def _req_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request_id_ctx_var.get() or "unknown"


# ============================================================================
# Clinician Self Facility Context Endpoints (placed before dynamic {id} routes)
# ============================================================================

@router.get(
    "/clinicians/me/facilities",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[list[FacilityResponse]],
    summary="List facilities accessible to the authenticated clinician",
    description="Returns all active facilities where the authenticated clinician has active privileges/membership. Supports multiple facilities.",
)
async def get_my_facilities(
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(require_permission(Permission.CLINICIAN_NETWORK_READ))],
    facility_service: Annotated[FacilityService, Depends(get_facility_service)],
) -> StandardSuccessResponse[list[FacilityResponse]]:
    facilities = await facility_service.get_clinician_facilities(
        clinician_id=current_user.user_id,
        user_context=current_user,
    )
    return StandardSuccessResponse(data=facilities, request_id=_req_id(request))


@router.get(
    "/clinicians/me/facilities/{facility_id}/context",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[ClinicianFacilityContextResponse],
    summary="Get facility context for the authenticated clinician",
    description="Returns facility details, parent organization, departments, clinician affiliation, and operational status.",
)
async def get_my_facility_context(
    request: Request,
    facility_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(require_permission(Permission.CLINICIAN_NETWORK_READ))],
    facility_service: Annotated[FacilityService, Depends(get_facility_service)],
) -> StandardSuccessResponse[ClinicianFacilityContextResponse]:
    context = await facility_service.get_clinician_facility_context(
        clinician_id=current_user.user_id,
        facility_id=facility_id,
        user_context=current_user,
    )
    return StandardSuccessResponse(data=context, request_id=_req_id(request))


# ============================================================================
# General Facility Endpoints
# ============================================================================

@router.get(
    "/facilities/search",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[FacilityListResponse],
    summary="Internal facility search",
    description="Search internal facilities by name, parent organization, facility type, and status.",
)
async def search_facilities(
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(require_permission(Permission.FACILITY_READ))],
    facility_service: Annotated[FacilityService, Depends(get_facility_service)],
    name: Annotated[str | None, Query(description="Case-insensitive substring match on facility name")] = None,
    organization_id: Annotated[str | None, Query(description="Filter by owning organization ID")] = None,
    facility_type: Annotated[FacilityType | None, Query(description="Filter by facility type")] = None,
    status: Annotated[FacilityStatus | None, Query(description="Filter by facility status")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Page limit")] = 50,
    offset: Annotated[int, Query(ge=0, description="Page offset")] = 0,
) -> StandardSuccessResponse[FacilityListResponse]:
    items, total = await facility_service.list_facilities(
        user_context=current_user,
        limit=limit,
        offset=offset,
        name=name,
        organization_id=organization_id,
        facility_type=facility_type,
        status=status,
    )
    return StandardSuccessResponse(
        data=FacilityListResponse(items=items, total=total, limit=limit, offset=offset),
        request_id=_req_id(request),
    )


@router.get(
    "/facilities/{facility_id}",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[FacilityResponse],
    summary="Get healthcare facility details",
    description="Return facility details if access is permitted.",
)
async def get_facility(
    request: Request,
    facility_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(require_permission(Permission.FACILITY_READ))],
    facility_service: Annotated[FacilityService, Depends(get_facility_service)],
) -> StandardSuccessResponse[FacilityResponse]:
    facility = await facility_service.get_facility(
        facility_id=facility_id,
        user_context=current_user,
    )
    return StandardSuccessResponse(data=facility, request_id=_req_id(request))


@router.get(
    "/facilities/{facility_id}/departments",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[DepartmentListResponse],
    summary="List departments belonging to a facility",
    description="Return departments belonging to the requested healthcare facility.",
)
async def get_facility_departments(
    request: Request,
    facility_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(require_permission(Permission.DEPARTMENT_READ))],
    facility_service: Annotated[FacilityService, Depends(get_facility_service)],
    status: Annotated[DepartmentStatus | None, Query(description="Filter by department status")] = None,
) -> StandardSuccessResponse[DepartmentListResponse]:
    departments = await facility_service.get_facility_departments(
        facility_id=facility_id,
        user_context=current_user,
        status=status,
    )
    return StandardSuccessResponse(
        data=DepartmentListResponse(items=departments, total=len(departments)),
        request_id=_req_id(request),
    )
