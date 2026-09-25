"""Allergies API endpoints."""

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
from app.schemas.allergy import (
    AllergyCreateRequest,
    AllergyListResponse,
    AllergyResponse,
    AllergyUpdateRequest,
)
from app.schemas.response import StandardErrorResponse, StandardSuccessResponse
from app.schemas.user import AuthenticatedUserContext
from app.services.audit_service import AuditService
from app.services.authorization_service import AuthorizationService
from app.services.clinical_record_service import ClinicalRecordService
from app.services.patient_service import PatientService

router = APIRouter(prefix="/patients/{patient_id}/allergies", tags=["Allergies"])


def _req_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request_id_ctx_var.get() or "unknown"


@router.get(
    "",
    response_model=StandardSuccessResponse[AllergyListResponse],
    summary="List patient allergies",
    description="Retrieve all allergy records for a patient.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
    },
)
async def list_allergies(
    request: Request,
    patient_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    clinical_service: Annotated[ClinicalRecordService, Depends(get_clinical_record_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    include_archived: bool = False,
) -> StandardSuccessResponse[AllergyListResponse]:
    """List allergy records for a patient."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="allergy:read",
        resource_type="allergy",
    )
    result = await clinical_service.list_allergies(
        patient_id=patient_id,
        include_archived=include_archived,
    )
    await audit_service.record_clinical_record_viewed(
        actor_id=current_user.user_id,
        patient_id=patient_id,
        resource_type="allergy",
    )
    return StandardSuccessResponse(data=result, request_id=_req_id(request))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardSuccessResponse[AllergyResponse],
    summary="Record an allergy",
    description="Add a new allergy to the patient's clinical record.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
        422: {"model": StandardErrorResponse, "description": "Validation error"},
    },
)
async def create_allergy(
    request: Request,
    patient_id: str,
    body: AllergyCreateRequest,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    clinical_service: Annotated[ClinicalRecordService, Depends(get_clinical_record_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> StandardSuccessResponse[AllergyResponse]:
    """Record a new allergy for a patient."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="allergy:create",
        resource_type="allergy",
    )
    entry = await clinical_service.create_allergy(
        patient_id=patient_id,
        actor_id=current_user.user_id,
        request=body,
    )
    await audit_service.record_allergy_created(
        actor_id=current_user.user_id,
        patient_id=patient_id,
        allergy_id=entry.id,
    )
    return StandardSuccessResponse(data=entry, request_id=_req_id(request))


@router.get(
    "/{allergy_id}",
    response_model=StandardSuccessResponse[AllergyResponse],
    summary="Get allergy record",
    description="Retrieve a specific allergy entry by ID.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Allergy or patient not found"},
    },
)
async def get_allergy_entry(
    request: Request,
    patient_id: str,
    allergy_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    clinical_service: Annotated[ClinicalRecordService, Depends(get_clinical_record_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> StandardSuccessResponse[AllergyResponse]:
    """Retrieve a single allergy entry."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="allergy:read",
        resource_type="allergy",
        resource_id=allergy_id,
    )
    entry = await clinical_service.get_allergy(patient_id=patient_id, allergy_id=allergy_id)
    await audit_service.record_clinical_record_viewed(
        actor_id=current_user.user_id,
        patient_id=patient_id,
        resource_type="allergy",
    )
    return StandardSuccessResponse(data=entry, request_id=_req_id(request))


@router.patch(
    "/{allergy_id}",
    response_model=StandardSuccessResponse[AllergyResponse],
    summary="Update allergy record",
    description="Update an allergy record. Requires provider authorization.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Allergy or patient not found"},
        422: {"model": StandardErrorResponse, "description": "Validation error"},
    },
)
async def update_allergy_entry(
    request: Request,
    patient_id: str,
    allergy_id: str,
    body: AllergyUpdateRequest,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    clinical_service: Annotated[ClinicalRecordService, Depends(get_clinical_record_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> StandardSuccessResponse[AllergyResponse]:
    """Update an allergy record."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="allergy:update",
        resource_type="allergy",
        resource_id=allergy_id,
    )
    updated = await clinical_service.update_allergy(
        patient_id=patient_id,
        allergy_id=allergy_id,
        actor_id=current_user.user_id,
        request=body,
    )
    await audit_service.record_allergy_updated(
        actor_id=current_user.user_id,
        patient_id=patient_id,
        allergy_id=allergy_id,
    )
    return StandardSuccessResponse(data=updated, request_id=_req_id(request))
