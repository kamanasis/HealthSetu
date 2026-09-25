"""SBAR Clinical Summary API Endpoints (Phase 8).

Endpoints for generating and retrieving standardized SBAR
(Situation, Background, Assessment, Recommendation) clinical communication summaries.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, Request, status

from app.api.deps import (
    get_authorization_service,
    get_current_user,
    get_patient_service,
    get_sbar_service,
    verify_patient_access,
)
from app.core.logging import request_id_ctx_var
from app.schemas.response import StandardErrorResponse, StandardSuccessResponse
from app.schemas.sbar import (
    SBARCreate,
    SBARResponse,
)
from app.schemas.user import AuthenticatedUserContext
from app.services.authorization_service import AuthorizationService
from app.services.patient_service import PatientService
from app.services.sbar_service import SBARService

router = APIRouter(prefix="/patients/{patient_id}/sbar", tags=["SBAR Summary"])


def _req_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request_id_ctx_var.get() or "unknown"


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardSuccessResponse[SBARResponse],
    summary="Generate SBAR clinical summary",
    description=(
        "Synthesizes a structured SBAR clinical communication summary from authoritative triage facts "
        "and documented patient history. Supports deterministic templating and fact-validated AI generation."
    ),
    responses={
        400: {"model": StandardErrorResponse, "description": "Invalid input or generation parameters"},
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied or insufficient consent"},
        404: {"model": StandardErrorResponse, "description": "Patient or triage assessment not found"},
    },
)
async def generate_sbar(
    patient_id: str,
    payload: SBARCreate,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    sbar_service: Annotated[SBARService, Depends(get_sbar_service)],
) -> StandardSuccessResponse[SBARResponse]:
    """Generate SBAR summary for a clinical triage assessment."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="sbar:create",
        resource_type="sbar",
        consent_scope="triage",
    )

    result = await sbar_service.generate_sbar(
        patient_id=patient_id,
        payload=payload,
        actor_id=current_user.user_id,
    )

    return StandardSuccessResponse(
        data=result,
        request_id=_req_id(request),
    )


@router.get(
    "/{sbar_id}",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[SBARResponse],
    summary="Get SBAR clinical summary",
    description="Retrieves a specific generated SBAR record by ID with both structured sections and plain text format.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied or insufficient consent"},
        404: {"model": StandardErrorResponse, "description": "SBAR record not found"},
    },
)
async def get_sbar(
    patient_id: str,
    sbar_id: str,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    sbar_service: Annotated[SBARService, Depends(get_sbar_service)],
) -> StandardSuccessResponse[SBARResponse]:
    """Retrieve an existing SBAR record."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="sbar:read",
        resource_type="sbar",
        resource_id=sbar_id,
        consent_scope="triage",
    )

    result = await sbar_service.get_sbar(
        patient_id=patient_id,
        sbar_id=sbar_id,
        actor_id=current_user.user_id,
    )

    return StandardSuccessResponse(
        data=result,
        request_id=_req_id(request),
    )
