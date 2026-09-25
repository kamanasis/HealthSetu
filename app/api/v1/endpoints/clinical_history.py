"""Clinical history API endpoints."""

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
from app.schemas.clinical_history import (
    ClinicalHistoryCreateRequest,
    ClinicalHistoryListResponse,
    ClinicalHistoryResponse,
    ClinicalHistoryUpdateRequest,
)
from app.schemas.response import StandardErrorResponse, StandardSuccessResponse
from app.schemas.user import AuthenticatedUserContext
from app.services.audit_service import AuditService
from app.services.authorization_service import AuthorizationService
from app.services.clinical_record_service import ClinicalRecordService
from app.services.patient_service import PatientService

router = APIRouter(prefix="/patients/{patient_id}/history", tags=["Clinical History"])


def _req_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request_id_ctx_var.get() or "unknown"


@router.get(
    "",
    response_model=StandardSuccessResponse[ClinicalHistoryListResponse],
    summary="List patient clinical history",
    description="Retrieve all clinical history entries for a patient.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
    },
)
async def list_clinical_history(
    request: Request,
    patient_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    clinical_service: Annotated[ClinicalRecordService, Depends(get_clinical_record_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    include_archived: bool = False,
) -> StandardSuccessResponse[ClinicalHistoryListResponse]:
    """List clinical history entries for a patient."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="clinical_history:read",
        resource_type="clinical_history",
    )
    result = await clinical_service.list_history(
        patient_id=patient_id,
        include_archived=include_archived,
    )
    await audit_service.record_clinical_record_viewed(
        actor_id=current_user.user_id,
        patient_id=patient_id,
        resource_type="clinical_history",
    )
    return StandardSuccessResponse(data=result, request_id=_req_id(request))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardSuccessResponse[ClinicalHistoryResponse],
    summary="Create clinical history entry",
    description="Add a new condition or past clinical event to the patient's record.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
        422: {"model": StandardErrorResponse, "description": "Validation error"},
    },
)
async def create_clinical_history(
    request: Request,
    patient_id: str,
    body: ClinicalHistoryCreateRequest,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    clinical_service: Annotated[ClinicalRecordService, Depends(get_clinical_record_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> StandardSuccessResponse[ClinicalHistoryResponse]:
    """Create a new clinical history entry."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="clinical_history:create",
        resource_type="clinical_history",
    )
    entry = await clinical_service.create_history_entry(
        patient_id=patient_id,
        actor_id=current_user.user_id,
        request=body,
    )
    await audit_service.record_clinical_history_created(
        actor_id=current_user.user_id,
        patient_id=patient_id,
        entry_id=entry.id,
    )
    return StandardSuccessResponse(data=entry, request_id=_req_id(request))


@router.get(
    "/{history_id}",
    response_model=StandardSuccessResponse[ClinicalHistoryResponse],
    summary="Get clinical history entry",
    description="Retrieve a specific clinical history entry by ID.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "History entry or patient not found"},
    },
)
async def get_clinical_history_entry(
    request: Request,
    patient_id: str,
    history_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    clinical_service: Annotated[ClinicalRecordService, Depends(get_clinical_record_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> StandardSuccessResponse[ClinicalHistoryResponse]:
    """Retrieve a single clinical history entry."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="clinical_history:read",
        resource_type="clinical_history",
        resource_id=history_id,
    )
    entry = await clinical_service.get_history_entry(patient_id=patient_id, entry_id=history_id)
    await audit_service.record_clinical_record_viewed(
        actor_id=current_user.user_id,
        patient_id=patient_id,
        resource_type="clinical_history",
    )
    return StandardSuccessResponse(data=entry, request_id=_req_id(request))


@router.patch(
    "/{history_id}",
    response_model=StandardSuccessResponse[ClinicalHistoryResponse],
    summary="Update clinical history entry",
    description="Update a clinical history entry. Requires provider authorization.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "History entry or patient not found"},
        422: {"model": StandardErrorResponse, "description": "Validation error"},
    },
)
async def update_clinical_history_entry(
    request: Request,
    patient_id: str,
    history_id: str,
    body: ClinicalHistoryUpdateRequest,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    clinical_service: Annotated[ClinicalRecordService, Depends(get_clinical_record_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> StandardSuccessResponse[ClinicalHistoryResponse]:
    """Update a clinical history entry."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="clinical_history:update",
        resource_type="clinical_history",
        resource_id=history_id,
    )
    updated = await clinical_service.update_history_entry(
        patient_id=patient_id,
        entry_id=history_id,
        actor_id=current_user.user_id,
        request=body,
    )
    await audit_service.record_clinical_history_updated(
        actor_id=current_user.user_id,
        patient_id=patient_id,
        entry_id=history_id,
    )
    return StandardSuccessResponse(data=updated, request_id=_req_id(request))
