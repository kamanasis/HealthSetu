"""Medication API endpoints."""

from typing import Annotated
from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import (
    get_audit_service,
    get_authorization_service,
    get_current_user,
    get_medication_service,
    get_patient_service,
    verify_patient_access,
)
from app.core.logging import request_id_ctx_var
from app.schemas.medication import (
    MedicationCorrectionRequest,
    MedicationSource,
    MedicationStatusUpdateRequest,
    PatientMedicationListResponse,
    PatientMedicationResponse,
    PatientMedicationStatus,
)
from app.schemas.response import StandardErrorResponse, StandardSuccessResponse
from app.schemas.user import AuthenticatedUserContext
from app.services.audit_service import AuditService
from app.services.authorization_service import AuthorizationService
from app.services.medication_service import MedicationService
from app.services.patient_service import PatientService

router = APIRouter(prefix="/patients/{patient_id}/medications", tags=["Medications"])


def _req_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request_id_ctx_var.get() or "unknown"


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[PatientMedicationListResponse],
    summary="List patient medications",
    description="List longitudinal patient medications with pagination, status filtering (PRESCRIBED, ACTIVE, INACTIVE, etc.), and source filtering.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
    },
)
async def list_patient_medications(
    request: Request,
    patient_id: str,
    status_filter: Annotated[PatientMedicationStatus | None, Query(alias="status")] = None,
    source_filter: Annotated[MedicationSource | None, Query(alias="source")] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)] = None,
    patient_service: Annotated[PatientService, Depends(get_patient_service)] = None,
    medication_service: Annotated[MedicationService, Depends(get_medication_service)] = None,
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)] = None,
) -> StandardSuccessResponse[PatientMedicationListResponse]:
    """List patient medications with pagination and filters."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="medication:read",
        resource_type="medication",
        consent_scope="medications",
    )

    medications = await medication_service.list_patient_medications(
        patient_id=patient_id,
        status_filter=status_filter,
        source_filter=source_filter,
        skip=skip,
        limit=limit,
    )
    return StandardSuccessResponse(data=medications, request_id=_req_id(request))


@router.get(
    "/{medication_id}",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[PatientMedicationResponse],
    summary="Get patient medication",
    description="Retrieve specific patient medication entry with full provenance chain and normalized terminology.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Medication record not found"},
    },
)
async def get_patient_medication(
    request: Request,
    patient_id: str,
    medication_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    medication_service: Annotated[MedicationService, Depends(get_medication_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> StandardSuccessResponse[PatientMedicationResponse]:
    """Retrieve patient medication record."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="medication:read",
        resource_type="medication",
        resource_id=medication_id,
        consent_scope="medications",
    )

    medication = await medication_service.get_patient_medication(
        patient_id=patient_id, medication_id=medication_id
    )
    await audit_service.record_medication_viewed(
        actor_id=current_user.user_id,
        patient_id=patient_id,
        medication_id=medication_id,
    )
    return StandardSuccessResponse(data=medication, request_id=_req_id(request))


@router.patch(
    "/{medication_id}/status",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[PatientMedicationResponse],
    summary="Update medication status",
    description="Update patient medication status (e.g. PRESCRIBED -> ACTIVE / INACTIVE / HISTORICAL) preserving longitudinal history.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Medication record not found"},
        422: {"model": StandardErrorResponse, "description": "Validation error"},
    },
)
async def update_medication_status(
    request: Request,
    patient_id: str,
    medication_id: str,
    payload: MedicationStatusUpdateRequest,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    medication_service: Annotated[MedicationService, Depends(get_medication_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
) -> StandardSuccessResponse[PatientMedicationResponse]:
    """Update medication status."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="medication:status",
        resource_type="medication",
        resource_id=medication_id,
        consent_scope="medications",
    )

    updated = await medication_service.update_medication_status(
        patient_id=patient_id,
        medication_id=medication_id,
        request=payload,
        actor_id=current_user.user_id,
    )
    return StandardSuccessResponse(data=updated, request_id=_req_id(request))


@router.patch(
    "/{medication_id}/correct",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[PatientMedicationResponse],
    summary="Correct extracted medication",
    description="Perform human review correction of raw extracted medication data, preserving original values and re-normalizing against terminology.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Medication record not found"},
        422: {"model": StandardErrorResponse, "description": "Validation error"},
    },
)
async def correct_medication(
    request: Request,
    patient_id: str,
    medication_id: str,
    payload: MedicationCorrectionRequest,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    medication_service: Annotated[MedicationService, Depends(get_medication_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
) -> StandardSuccessResponse[PatientMedicationResponse]:
    """Correct raw extracted medication data."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="medication:correct",
        resource_type="medication",
        resource_id=medication_id,
        consent_scope="medications",
    )

    corrected = await medication_service.correct_medication(
        patient_id=patient_id,
        medication_id=medication_id,
        request=payload,
        actor_id=current_user.user_id,
    )
    return StandardSuccessResponse(data=corrected, request_id=_req_id(request))
