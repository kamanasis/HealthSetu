"""Vitals API endpoints."""

from typing import Annotated
from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import (
    get_audit_service,
    get_authorization_service,
    get_clinical_record_service,
    get_current_user,
    get_patient_service,
    verify_patient_access,
)
from app.core.logging import request_id_ctx_var
from app.schemas.response import StandardErrorResponse, StandardSuccessResponse
from app.schemas.user import AuthenticatedUserContext
from app.schemas.vital import VitalCreateRequest, VitalListResponse, VitalResponse, VitalType
from app.services.audit_service import AuditService
from app.services.authorization_service import AuthorizationService
from app.services.clinical_record_service import ClinicalRecordService
from app.services.patient_service import PatientService

router = APIRouter(prefix="/patients/{patient_id}/vitals", tags=["Vitals"])


def _req_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request_id_ctx_var.get() or "unknown"


@router.get(
    "",
    response_model=StandardSuccessResponse[VitalListResponse],
    summary="List patient vitals",
    description="Retrieve vital measurements for a patient. Supports filtering by vital type and limiting results.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
    },
)
async def list_vitals(
    request: Request,
    patient_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    clinical_service: Annotated[ClinicalRecordService, Depends(get_clinical_record_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    vital_type: VitalType | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> StandardSuccessResponse[VitalListResponse]:
    """List vital measurements for a patient."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="vital:read",
        resource_type="vital",
    )
    result = await clinical_service.list_vitals(
        patient_id=patient_id,
        vital_type=vital_type,
        limit=limit,
    )
    await audit_service.record_clinical_record_viewed(
        actor_id=current_user.user_id,
        patient_id=patient_id,
        resource_type="vital",
    )
    return StandardSuccessResponse(data=result, request_id=_req_id(request))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardSuccessResponse[VitalResponse],
    summary="Record vital measurement",
    description="Append a new vital measurement to the patient record. Vitals are strictly append-only.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
        422: {"model": StandardErrorResponse, "description": "Validation error"},
    },
)
async def record_vital(
    request: Request,
    patient_id: str,
    body: VitalCreateRequest,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    clinical_service: Annotated[ClinicalRecordService, Depends(get_clinical_record_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> StandardSuccessResponse[VitalResponse]:
    """Append a vital measurement."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="vital:create",
        resource_type="vital",
    )
    entry = await clinical_service.record_vital(
        patient_id=patient_id,
        actor_id=current_user.user_id,
        request=body,
    )
    await audit_service.record_vital_recorded(
        actor_id=current_user.user_id,
        patient_id=patient_id,
        vital_id=entry.id,
        vital_type=body.vital_type.value,
    )
    return StandardSuccessResponse(data=entry, request_id=_req_id(request))


@router.get(
    "/{vital_id}",
    response_model=StandardSuccessResponse[VitalResponse],
    summary="Get vital measurement",
    description="Retrieve a single vital measurement by ID.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Vital measurement or patient not found"},
    },
)
async def get_vital_entry(
    request: Request,
    patient_id: str,
    vital_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    clinical_service: Annotated[ClinicalRecordService, Depends(get_clinical_record_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> StandardSuccessResponse[VitalResponse]:
    """Retrieve a single vital measurement."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="vital:read",
        resource_type="vital",
        resource_id=vital_id,
    )
    entry = await clinical_service.get_vital(patient_id=patient_id, vital_id=vital_id)
    await audit_service.record_clinical_record_viewed(
        actor_id=current_user.user_id,
        patient_id=patient_id,
        resource_type="vital",
    )
    return StandardSuccessResponse(data=entry, request_id=_req_id(request))
