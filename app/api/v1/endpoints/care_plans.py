"""Personalized Care Plan API Endpoints (Phase 9).

Endpoints for creating, synthesizing from verified discharge instructions,
listing, retrieving, and updating patient recovery care plans.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import (
    get_authorization_service,
    get_care_plan_service,
    get_current_user,
    get_patient_service,
    verify_patient_access,
)
from app.core.logging import request_id_ctx_var
from app.schemas.care_plan import (
    CarePlanCreate,
    CarePlanGenerateFromDischargeRequest,
    CarePlanListResponse,
    CarePlanResponse,
    CarePlanStatus,
    CarePlanUpdate,
)
from app.schemas.response import StandardErrorResponse, StandardSuccessResponse
from app.schemas.user import AuthenticatedUserContext
from app.services.authorization_service import AuthorizationService
from app.services.care_plan_service import CarePlanService
from app.services.patient_service import PatientService

router = APIRouter(prefix="/patients/{patient_id}/care-plans", tags=["Care Plans"])


def _req_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request_id_ctx_var.get() or "unknown"


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardSuccessResponse[CarePlanResponse],
    summary="Create personalized care plan",
    description="Directly creates a personalized care plan with goals, schedule tasks, and red flag warnings.",
    responses={
        400: {"model": StandardErrorResponse, "description": "Invalid input parameters"},
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied or insufficient consent"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
    },
)
async def create_care_plan(
    patient_id: str,
    payload: CarePlanCreate,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    care_plan_service: Annotated[CarePlanService, Depends(get_care_plan_service)],
) -> StandardSuccessResponse[CarePlanResponse]:
    """Create a new personalized care plan directly."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="care_plan:create",
        resource_type="care_plan",
        consent_scope="care_plan",
    )

    result = await care_plan_service.create_care_plan(
        patient_id=patient_id,
        payload=payload,
        actor_id=current_user.user_id,
    )

    return StandardSuccessResponse(
        data=result,
        request_id=_req_id(request),
    )


@router.post(
    "/from-discharge",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardSuccessResponse[CarePlanResponse],
    summary="Generate care plan from verified discharge instructions",
    description=(
        "Synthesizes an actionable, daily recovery schedule from structured discharge instructions. "
        "Enforces the clinical verification boundary: discharge summary must be verified by a clinician "
        "unless explicitly overridden."
    ),
    responses={
        400: {"model": StandardErrorResponse, "description": "Discharge instructions unverified or invalid"},
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied or insufficient consent"},
        404: {"model": StandardErrorResponse, "description": "Patient or discharge instructions not found"},
    },
)
async def generate_from_discharge(
    patient_id: str,
    payload: CarePlanGenerateFromDischargeRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    care_plan_service: Annotated[CarePlanService, Depends(get_care_plan_service)],
) -> StandardSuccessResponse[CarePlanResponse]:
    """Synthesize a personalized recovery care plan from clinically verified discharge instructions."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="care_plan:create",
        resource_type="care_plan",
        consent_scope="care_plan",
    )

    result = await care_plan_service.generate_from_discharge(
        patient_id=patient_id,
        payload=payload,
        actor_id=current_user.user_id,
    )

    return StandardSuccessResponse(
        data=result,
        request_id=_req_id(request),
    )


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[CarePlanListResponse],
    summary="List patient care plans",
    description="Retrieves a paginated list of care plans for a patient, optionally filtered by status.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied or insufficient consent"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
    },
)
async def list_care_plans(
    patient_id: str,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    care_plan_service: Annotated[CarePlanService, Depends(get_care_plan_service)],
    status: CarePlanStatus | None = Query(None, description="Filter by care plan status"),
    limit: int = Query(50, ge=1, le=100, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
) -> StandardSuccessResponse[CarePlanListResponse]:
    """List paginated care plans for a patient."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="care_plan:read",
        resource_type="care_plan",
        consent_scope="care_plan",
    )

    result = await care_plan_service.list_patient_care_plans(
        patient_id=patient_id,
        actor_id=current_user.user_id,
        limit=limit,
        offset=offset,
        status=status,
    )

    return StandardSuccessResponse(
        data=result,
        request_id=_req_id(request),
    )


@router.get(
    "/{care_plan_id}",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[CarePlanResponse],
    summary="Get patient care plan",
    description="Retrieves a specific care plan by ID, including tasks, goals, and warning signs.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied or insufficient consent"},
        404: {"model": StandardErrorResponse, "description": "Care plan not found"},
    },
)
async def get_care_plan(
    patient_id: str,
    care_plan_id: str,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    care_plan_service: Annotated[CarePlanService, Depends(get_care_plan_service)],
) -> StandardSuccessResponse[CarePlanResponse]:
    """Retrieve a specific care plan by ID."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="care_plan:read",
        resource_type="care_plan",
        resource_id=care_plan_id,
        consent_scope="care_plan",
    )

    result = await care_plan_service.get_care_plan(
        patient_id=patient_id,
        care_plan_id=care_plan_id,
        actor_id=current_user.user_id,
    )

    return StandardSuccessResponse(
        data=result,
        request_id=_req_id(request),
    )


@router.patch(
    "/{care_plan_id}",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[CarePlanResponse],
    summary="Update care plan or mark tasks complete",
    description="Updates care plan status, completes daily tasks, or adds coordination notes.",
    responses={
        400: {"model": StandardErrorResponse, "description": "Invalid update parameters"},
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied or insufficient consent"},
        404: {"model": StandardErrorResponse, "description": "Care plan not found"},
    },
)
async def update_care_plan(
    patient_id: str,
    care_plan_id: str,
    payload: CarePlanUpdate,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    care_plan_service: Annotated[CarePlanService, Depends(get_care_plan_service)],
) -> StandardSuccessResponse[CarePlanResponse]:
    """Update care plan status or complete tasks."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="care_plan:update",
        resource_type="care_plan",
        resource_id=care_plan_id,
        consent_scope="care_plan",
    )

    result = await care_plan_service.update_care_plan(
        patient_id=patient_id,
        care_plan_id=care_plan_id,
        payload=payload,
        actor_id=current_user.user_id,
    )

    return StandardSuccessResponse(
        data=result,
        request_id=_req_id(request),
    )
