"""Clinical Triage API Endpoints (Phase 8).

Endpoints for deterministic rule-based triage assessment, urgency categorization,
explanation generation, and assessment history.

CRITICAL CLINICAL BOUNDARIES:
- Triage determines clinical urgency classification, NOT a disease diagnosis.
- Urgency decisions are determined by authoritative rule protocols, never an LLM.
- Facility discovery and care plans are handled in later phases.
"""

from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import (
    get_authorization_service,
    get_current_user,
    get_patient_service,
    get_triage_service,
    verify_patient_access,
)
from app.core.logging import request_id_ctx_var
from app.schemas.response import StandardErrorResponse, StandardSuccessResponse
from app.schemas.triage import (
    TriageAssessmentCreate,
    TriageAssessmentResponse,
    TriageListResponse,
    TriageUrgency,
)
from app.schemas.user import AuthenticatedUserContext
from app.services.authorization_service import AuthorizationService
from app.services.patient_service import PatientService
from app.services.triage_service import TriageService

router = APIRouter(prefix="/patients/{patient_id}/triage", tags=["Clinical Triage"])


def _req_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request_id_ctx_var.get() or "unknown"


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardSuccessResponse[TriageAssessmentResponse],
    summary="Conduct clinical triage assessment",
    description=(
        "Evaluates structured patient symptoms, vital signs, and clinical context against configured "
        "authoritative rule protocols to produce a deterministic urgency classification and explanation."
    ),
    responses={
        400: {"model": StandardErrorResponse, "description": "Invalid input or missing required symptoms"},
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied or insufficient consent"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
        504: {"model": StandardErrorResponse, "description": "Triage rule engine timeout"},
    },
)
async def assess_triage(
    patient_id: str,
    payload: TriageAssessmentCreate,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    triage_service: Annotated[TriageService, Depends(get_triage_service)],
) -> StandardSuccessResponse[TriageAssessmentResponse]:
    """Execute clinical triage evaluation."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="triage:assess",
        resource_type="triage",
        consent_scope="triage",
    )

    result = await triage_service.assess_patient(
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
    response_model=StandardSuccessResponse[TriageListResponse],
    summary="List patient triage assessments",
    description="Retrieves a paginated list of historical triage assessments for a patient.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied or insufficient consent"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
    },
)
async def list_triage_assessments(
    patient_id: str,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    triage_service: Annotated[TriageService, Depends(get_triage_service)],
    limit: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
    offset: Annotated[int, Query(ge=0, description="Offset for pagination")] = 0,
    urgency: Annotated[TriageUrgency | None, Query(description="Filter by urgency level")] = None,
    encounter_id: Annotated[str | None, Query(description="Filter by clinical encounter ID")] = None,
    start_date: Annotated[datetime | None, Query(description="Filter by earliest assessment date")] = None,
    end_date: Annotated[datetime | None, Query(description="Filter by latest assessment date")] = None,
) -> StandardSuccessResponse[TriageListResponse]:
    """List historical triage assessments."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="triage:read",
        resource_type="triage",
        consent_scope="triage",
    )

    result = await triage_service.list_assessments(
        patient_id=patient_id,
        actor_id=current_user.user_id,
        limit=limit,
        offset=offset,
        urgency=urgency,
        encounter_id=encounter_id,
        start_date=start_date,
        end_date=end_date,
    )

    return StandardSuccessResponse(
        data=result,
        request_id=_req_id(request),
    )


@router.get(
    "/{assessment_id}",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[TriageAssessmentResponse],
    summary="Get single triage assessment",
    description="Retrieves a specific triage assessment by ID with complete rationale and missing data tracking.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied or insufficient consent"},
        404: {"model": StandardErrorResponse, "description": "Triage assessment not found"},
    },
)
async def get_triage_assessment(
    patient_id: str,
    assessment_id: str,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    triage_service: Annotated[TriageService, Depends(get_triage_service)],
) -> StandardSuccessResponse[TriageAssessmentResponse]:
    """Retrieve an individual triage assessment."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="triage:read",
        resource_type="triage",
        resource_id=assessment_id,
        consent_scope="triage",
    )

    result = await triage_service.get_assessment(
        patient_id=patient_id,
        assessment_id=assessment_id,
        actor_id=current_user.user_id,
    )

    return StandardSuccessResponse(
        data=result,
        request_id=_req_id(request),
    )
