"""Encounters API endpoints."""

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
from app.schemas.encounter import (
    EncounterCreateRequest,
    EncounterListResponse,
    EncounterResponse,
    EncounterStatus,
)
from app.schemas.response import StandardErrorResponse, StandardSuccessResponse
from app.schemas.user import AuthenticatedUserContext
from app.services.audit_service import AuditService
from app.services.authorization_service import AuthorizationService
from app.services.clinical_record_service import ClinicalRecordService
from app.services.patient_service import PatientService

router = APIRouter(prefix="/patients/{patient_id}/encounters", tags=["Encounters"])


def _req_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request_id_ctx_var.get() or "unknown"


@router.get(
    "",
    response_model=StandardSuccessResponse[EncounterListResponse],
    summary="List patient encounters",
    description="Retrieve clinical encounter records for a patient. Optionally filter by status.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
    },
)
async def list_encounters(
    request: Request,
    patient_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    clinical_service: Annotated[ClinicalRecordService, Depends(get_clinical_record_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    status_filter: EncounterStatus | None = None,
) -> StandardSuccessResponse[EncounterListResponse]:
    """List encounter records for a patient."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="encounter:read",
        resource_type="encounter",
    )
    result = await clinical_service.list_encounters(
        patient_id=patient_id,
        status_filter=status_filter,
    )
    await audit_service.record_clinical_record_viewed(
        actor_id=current_user.user_id,
        patient_id=patient_id,
        resource_type="encounter",
    )
    return StandardSuccessResponse(data=result, request_id=_req_id(request))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardSuccessResponse[EncounterResponse],
    summary="Create encounter record",
    description="Record a clinical encounter context. Requires provider authorization.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
        422: {"model": StandardErrorResponse, "description": "Validation error"},
    },
)
async def create_encounter(
    request: Request,
    patient_id: str,
    body: EncounterCreateRequest,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    clinical_service: Annotated[ClinicalRecordService, Depends(get_clinical_record_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> StandardSuccessResponse[EncounterResponse]:
    """Create a new encounter record."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="encounter:create",
        resource_type="encounter",
    )
    entry = await clinical_service.create_encounter(
        patient_id=patient_id,
        actor_id=current_user.user_id,
        request=body,
    )
    await audit_service.record_encounter_created(
        actor_id=current_user.user_id,
        patient_id=patient_id,
        encounter_id=entry.id,
    )
    return StandardSuccessResponse(data=entry, request_id=_req_id(request))


@router.get(
    "/{encounter_id}",
    response_model=StandardSuccessResponse[EncounterResponse],
    summary="Get encounter record",
    description="Retrieve a specific clinical encounter by ID.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Encounter or patient not found"},
    },
)
async def get_encounter_entry(
    request: Request,
    patient_id: str,
    encounter_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    clinical_service: Annotated[ClinicalRecordService, Depends(get_clinical_record_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> StandardSuccessResponse[EncounterResponse]:
    """Retrieve a single encounter record."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="encounter:read",
        resource_type="encounter",
        resource_id=encounter_id,
    )
    entry = await clinical_service.get_encounter(patient_id=patient_id, encounter_id=encounter_id)
    await audit_service.record_encounter_viewed(
        actor_id=current_user.user_id,
        patient_id=patient_id,
        encounter_id=encounter_id,
    )
    return StandardSuccessResponse(data=entry, request_id=_req_id(request))
