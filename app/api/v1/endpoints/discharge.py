"""Discharge Information Extraction and Verification API Endpoints (Phase 9).

Endpoints for extracting structured discharge instructions from medical documents
and clinician verification boundary enforcement.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, Request, status

from app.api.deps import (
    get_authorization_service,
    get_current_user,
    get_discharge_service,
    get_patient_service,
    verify_patient_access,
)
from app.core.logging import request_id_ctx_var
from app.schemas.discharge import (
    DischargeExtractionRequest,
    DischargeInstructionResponse,
    DischargeVerificationUpdate,
)
from app.schemas.response import StandardErrorResponse, StandardSuccessResponse
from app.schemas.user import AuthenticatedUserContext
from app.services.authorization_service import AuthorizationService
from app.services.discharge_service import DischargeService
from app.services.patient_service import PatientService

router = APIRouter(prefix="/patients/{patient_id}/discharge", tags=["Discharge Instructions"])


def _req_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request_id_ctx_var.get() or "unknown"


@router.post(
    "/extract",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardSuccessResponse[DischargeInstructionResponse],
    summary="Extract structured discharge instructions from document",
    description=(
        "Extracts structured discharge instructions (diagnoses, medications, activity, diet, wound care, "
        "warning signs, follow-up) from a processed clinical document. Initial verification status is UNVERIFIED."
    ),
    responses={
        400: {"model": StandardErrorResponse, "description": "Invalid input or document processing failure"},
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied or insufficient consent"},
        404: {"model": StandardErrorResponse, "description": "Patient or document not found"},
    },
)
async def extract_discharge_instructions(
    patient_id: str,
    payload: DischargeExtractionRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    discharge_service: Annotated[DischargeService, Depends(get_discharge_service)],
) -> StandardSuccessResponse[DischargeInstructionResponse]:
    """Extract structured discharge instructions from an uploaded clinical document."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="discharge:extract",
        resource_type="discharge",
        consent_scope="discharge_summary",
    )

    result = await discharge_service.extract_from_document(
        patient_id=patient_id,
        document_id=payload.document_id,
        encounter_id=payload.encounter_id,
        actor_id=current_user.user_id,
    )

    return StandardSuccessResponse(
        data=result,
        request_id=_req_id(request),
    )


@router.get(
    "/{discharge_id}",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[DischargeInstructionResponse],
    summary="Get structured discharge instructions",
    description="Retrieves extracted discharge instructions by ID, including verification status and clinical provenance.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied or insufficient consent"},
        404: {"model": StandardErrorResponse, "description": "Discharge record not found"},
    },
)
async def get_discharge_instructions(
    patient_id: str,
    discharge_id: str,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    discharge_service: Annotated[DischargeService, Depends(get_discharge_service)],
) -> StandardSuccessResponse[DischargeInstructionResponse]:
    """Retrieve structured discharge instructions by ID."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="discharge:read",
        resource_type="discharge",
        resource_id=discharge_id,
        consent_scope="discharge_summary",
    )

    result = await discharge_service.get_discharge_instructions(
        patient_id=patient_id,
        discharge_id=discharge_id,
        actor_id=current_user.user_id,
    )

    return StandardSuccessResponse(
        data=result,
        request_id=_req_id(request),
    )


@router.post(
    "/{discharge_id}/verify",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[DischargeInstructionResponse],
    summary="Clinician review and verification of discharge instructions",
    description=(
        "Enforces the clinical verification boundary. Allows licensed healthcare providers to review, "
        "modify/correct, and approve extracted discharge instructions before they can generate an active care plan."
    ),
    responses={
        400: {"model": StandardErrorResponse, "description": "Invalid verification status or data"},
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied (Doctor role required with consent)"},
        404: {"model": StandardErrorResponse, "description": "Discharge record not found"},
    },
)
async def verify_discharge_instructions(
    patient_id: str,
    discharge_id: str,
    payload: DischargeVerificationUpdate,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    discharge_service: Annotated[DischargeService, Depends(get_discharge_service)],
) -> StandardSuccessResponse[DischargeInstructionResponse]:
    """Clinician verification and correction boundary for extracted discharge instructions."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="discharge:verify",
        resource_type="discharge",
        resource_id=discharge_id,
        consent_scope="discharge_summary",
    )

    result = await discharge_service.verify_discharge_instructions(
        patient_id=patient_id,
        discharge_id=discharge_id,
        payload=payload,
        clinician_id=current_user.user_id,
    )

    return StandardSuccessResponse(
        data=result,
        request_id=_req_id(request),
    )
