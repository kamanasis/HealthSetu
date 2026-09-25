"""Healthcare Organization API Endpoints (Phase 11).

Provides routes for healthcare organizations, organizational facility lookups,
and clinician organization context.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import (
    get_current_user,
    get_organization_service,
    require_permission,
    require_role,
)
from app.core.logging import request_id_ctx_var
from app.core.policies import Permission
from app.schemas.facility import FacilityListResponse, FacilityStatus, FacilityType
from app.schemas.organization import (
    OrganizationListResponse,
    OrganizationResponse,
    OrganizationStatus,
    OrganizationType,
)
from app.schemas.organization_context import ClinicianOrganizationContextResponse
from app.schemas.response import StandardSuccessResponse
from app.schemas.user import AuthenticatedUserContext
from app.services.organization_service import OrganizationService

router = APIRouter(tags=["Healthcare Organizations"])


def _req_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request_id_ctx_var.get() or "unknown"


# ============================================================================
# Clinician Self Organization Context Endpoints (placed before dynamic {id} routes)
# ============================================================================

@router.get(
    "/clinicians/me/organizations",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[list[OrganizationResponse]],
    summary="List organizations associated with the authenticated clinician",
    description="Returns all active organizations the authenticated clinician has membership in. Supports multiple organizations.",
)
async def get_my_organizations(
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(require_permission(Permission.CLINICIAN_NETWORK_READ))],
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> StandardSuccessResponse[list[OrganizationResponse]]:
    orgs = await org_service.get_clinician_organizations(
        clinician_id=current_user.user_id,
        user_context=current_user,
    )
    return StandardSuccessResponse(data=orgs, request_id=_req_id(request))


@router.get(
    "/clinicians/me/organizations/{organization_id}/context",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[ClinicianOrganizationContextResponse],
    summary="Get organization context for the authenticated clinician",
    description="Returns organization details, status, clinician affiliation, and accessible facilities for the clinician.",
)
async def get_my_organization_context(
    request: Request,
    organization_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(require_permission(Permission.CLINICIAN_NETWORK_READ))],
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> StandardSuccessResponse[ClinicianOrganizationContextResponse]:
    context = await org_service.get_clinician_organization_context(
        clinician_id=current_user.user_id,
        organization_id=organization_id,
        user_context=current_user,
    )
    return StandardSuccessResponse(data=context, request_id=_req_id(request))


# ============================================================================
# General Organization Endpoints
# ============================================================================

@router.get(
    "/organizations/search",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[OrganizationListResponse],
    summary="Internal organization search",
    description="Search internal organizations by name, status, and organization type.",
)
async def search_organizations(
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(require_permission(Permission.ORGANIZATION_READ))],
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
    name: Annotated[str | None, Query(description="Case-insensitive substring match on organization name")] = None,
    status: Annotated[OrganizationStatus | None, Query(description="Filter by operational status")] = None,
    org_type: Annotated[OrganizationType | None, Query(description="Filter by organization type")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Page limit")] = 50,
    offset: Annotated[int, Query(ge=0, description="Page offset")] = 0,
) -> StandardSuccessResponse[OrganizationListResponse]:
    items, total = await org_service.list_organizations(
        user_context=current_user,
        limit=limit,
        offset=offset,
        name=name,
        status=status,
        org_type=org_type,
    )
    return StandardSuccessResponse(
        data=OrganizationListResponse(items=items, total=total, limit=limit, offset=offset),
        request_id=_req_id(request),
    )


@router.get(
    "/organizations",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[OrganizationListResponse],
    summary="List healthcare organizations",
    description="Return organizations accessible to the authenticated user.",
)
async def list_organizations(
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(require_permission(Permission.ORGANIZATION_READ))],
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
    name: Annotated[str | None, Query(description="Filter by organization name")] = None,
    status: Annotated[OrganizationStatus | None, Query(description="Filter by status")] = None,
    org_type: Annotated[OrganizationType | None, Query(description="Filter by organization type")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Page limit")] = 50,
    offset: Annotated[int, Query(ge=0, description="Page offset")] = 0,
) -> StandardSuccessResponse[OrganizationListResponse]:
    items, total = await org_service.list_organizations(
        user_context=current_user,
        limit=limit,
        offset=offset,
        name=name,
        status=status,
        org_type=org_type,
    )
    return StandardSuccessResponse(
        data=OrganizationListResponse(items=items, total=total, limit=limit, offset=offset),
        request_id=_req_id(request),
    )


@router.get(
    "/organizations/{organization_id}",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[OrganizationResponse],
    summary="Get healthcare organization details",
    description="Return organization details if access is permitted.",
)
async def get_organization(
    request: Request,
    organization_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(require_permission(Permission.ORGANIZATION_READ))],
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> StandardSuccessResponse[OrganizationResponse]:
    org = await org_service.get_organization(
        organization_id=organization_id,
        user_context=current_user,
    )
    return StandardSuccessResponse(data=org, request_id=_req_id(request))


@router.get(
    "/organizations/{organization_id}/facilities",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[FacilityListResponse],
    summary="List facilities belonging to an organization",
    description="Return facilities belonging to the organization after validating existence and active status.",
)
async def get_organization_facilities(
    request: Request,
    organization_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(require_permission(Permission.FACILITY_READ))],
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
    status: Annotated[FacilityStatus | None, Query(description="Filter by facility status")] = None,
    facility_type: Annotated[FacilityType | None, Query(description="Filter by facility type")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Page limit")] = 50,
    offset: Annotated[int, Query(ge=0, description="Page offset")] = 0,
) -> StandardSuccessResponse[FacilityListResponse]:
    items, total = await org_service.get_organization_facilities(
        organization_id=organization_id,
        user_context=current_user,
        limit=limit,
        offset=offset,
        status=status,
        facility_type=facility_type,
    )
    return StandardSuccessResponse(
        data=FacilityListResponse(items=items, total=total, limit=limit, offset=offset),
        request_id=_req_id(request),
    )
