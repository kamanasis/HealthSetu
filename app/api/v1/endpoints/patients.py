"""Patient profile and clinical summary endpoints."""

from typing import Annotated
from fastapi import APIRouter, Depends, Request, status

from app.api.deps import (
    get_audit_service,
    get_authorization_service,
    get_clinical_record_service,
    get_current_user,
    get_patient_service,
    verify_patient_access,
)
from app.core.logging import request_id_ctx_var
from app.schemas.clinical_summary import ClinicalSummaryResponse
from app.schemas.patient import PatientResponse, PatientUpdateRequest
from app.schemas.response import StandardErrorResponse, StandardSuccessResponse
from app.schemas.user import AuthenticatedUserContext
from app.services.audit_service import AuditService
from app.services.authorization_service import AuthorizationService
from app.services.clinical_record_service import ClinicalRecordService
from app.services.patient_service import PatientService

router = APIRouter(prefix="/patients", tags=["Patients"])


def _req_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request_id_ctx_var.get() or "unknown"


@router.get(
    "/{patient_id}",
    response_model=StandardSuccessResponse[PatientResponse],
    summary="Get patient profile",
    description="Retrieve patient demographic profile. Subject to ownership and authorization policies.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
    },
)
async def get_patient_profile(
    request: Request,
    patient_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> StandardSuccessResponse[PatientResponse]:
    """Retrieve patient demographic profile."""
    patient = await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="patient_profile:read",
        resource_type="patient_profile",
    )
    await audit_service.record_clinical_record_viewed(
        actor_id=current_user.user_id,
        patient_id=patient_id,
        resource_type="patient",
    )
    return StandardSuccessResponse(data=patient, request_id=_req_id(request))


@router.patch(
    "/{patient_id}",
    response_model=StandardSuccessResponse[PatientResponse],
    summary="Update patient profile",
    description="Update permitted demographic and contact fields for patient. Self-update only.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
        422: {"model": StandardErrorResponse, "description": "Validation error"},
    },
)
async def update_patient_profile(
    request: Request,
    patient_id: str,
    body: PatientUpdateRequest,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> StandardSuccessResponse[PatientResponse]:
    """Update patient demographic profile."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="patient_profile:update",
        resource_type="patient_profile",
    )
    updated = await patient_service.update_patient(patient_id=patient_id, request=body)
    await audit_service.record_patient_profile_updated(
        actor_id=current_user.user_id,
        patient_id=patient_id,
        updated_fields=list(body.model_dump(exclude_unset=True).keys()),
    )
    return StandardSuccessResponse(data=updated, request_id=_req_id(request))


@router.get(
    "/{patient_id}/clinical-summary",
    response_model=StandardSuccessResponse[ClinicalSummaryResponse],
    summary="Get patient clinical summary",
    description="Assembles a controlled clinical summary including active conditions, allergies, vitals, and encounters.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
    },
)
async def get_patient_clinical_summary(
    request: Request,
    patient_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    clinical_service: Annotated[ClinicalRecordService, Depends(get_clinical_record_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> StandardSuccessResponse[ClinicalSummaryResponse]:
    """Retrieve assembled clinical summary."""
    patient = await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="clinical_summary:read",
        resource_type="clinical_summary",
    )
    summary = await clinical_service.get_clinical_summary(
        patient_id=patient_id,
        patient_profile=patient,
    )
    await audit_service.record_clinical_summary_viewed(
        actor_id=current_user.user_id,
        patient_id=patient_id,
    )
    return StandardSuccessResponse(data=summary, request_id=_req_id(request))
