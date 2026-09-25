"""Prescription API endpoints."""

from typing import Annotated
from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import (
    get_audit_service,
    get_authorization_service,
    get_current_user,
    get_patient_service,
    get_prescription_service,
    verify_patient_access,
)
from app.core.logging import request_id_ctx_var
from app.schemas.prescription import (
    PrescriptionCreate,
    PrescriptionItemResponse,
    PrescriptionListResponse,
    PrescriptionNormalizeResponse,
    PrescriptionResponse,
)
from app.schemas.response import StandardErrorResponse, StandardSuccessResponse
from app.schemas.user import AuthenticatedUserContext
from app.services.audit_service import AuditService
from app.services.authorization_service import AuthorizationService
from app.services.patient_service import PatientService
from app.services.prescription_service import PrescriptionService

router = APIRouter(prefix="/patients/{patient_id}/prescriptions", tags=["Prescriptions"])


def _req_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request_id_ctx_var.get() or "unknown"


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardSuccessResponse[PrescriptionResponse],
    summary="Create prescription",
    description="Create a prescription entity with items, optionally linking to a Phase 5 medical document and auto-normalizing medication items.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
        422: {"model": StandardErrorResponse, "description": "Validation error"},
    },
)
async def create_prescription(
    request: Request,
    patient_id: str,
    payload: PrescriptionCreate,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    prescription_service: Annotated[PrescriptionService, Depends(get_prescription_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
) -> StandardSuccessResponse[PrescriptionResponse]:
    """Create a new prescription."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="prescription:create",
        resource_type="prescription",
        consent_scope="prescriptions",
    )

    created = await prescription_service.create_prescription(
        patient_id=patient_id,
        request=payload,
        actor_id=current_user.user_id,
        auto_normalize=True,
    )
    return StandardSuccessResponse(data=created, request_id=_req_id(request))


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[PrescriptionListResponse],
    summary="List patient prescriptions",
    description="List prescriptions belonging to a patient with pagination.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
    },
)
async def list_prescriptions(
    request: Request,
    patient_id: str,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)] = None,
    patient_service: Annotated[PatientService, Depends(get_patient_service)] = None,
    prescription_service: Annotated[PrescriptionService, Depends(get_prescription_service)] = None,
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)] = None,
) -> StandardSuccessResponse[PrescriptionListResponse]:
    """List prescriptions for a patient."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="prescription:read",
        resource_type="prescription",
        consent_scope="prescriptions",
    )

    prescriptions = await prescription_service.list_prescriptions(
        patient_id=patient_id, skip=skip, limit=limit
    )
    return StandardSuccessResponse(data=prescriptions, request_id=_req_id(request))


@router.get(
    "/{prescription_id}",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[PrescriptionResponse],
    summary="Get prescription details",
    description="Retrieve full prescription metadata, medication items, and normalized concept references.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Prescription not found"},
    },
)
async def get_prescription(
    request: Request,
    patient_id: str,
    prescription_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    prescription_service: Annotated[PrescriptionService, Depends(get_prescription_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> StandardSuccessResponse[PrescriptionResponse]:
    """Retrieve prescription details."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="prescription:read",
        resource_type="prescription",
        resource_id=prescription_id,
        consent_scope="prescriptions",
    )

    prescription = await prescription_service.get_prescription(
        patient_id=patient_id, prescription_id=prescription_id
    )
    await audit_service.record_prescription_viewed(
        actor_id=current_user.user_id,
        patient_id=patient_id,
        prescription_id=prescription_id,
    )
    return StandardSuccessResponse(data=prescription, request_id=_req_id(request))


@router.post(
    "/{prescription_id}/normalize",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[PrescriptionNormalizeResponse],
    summary="Normalize prescription items",
    description="Trigger terminology normalization against configured provider for all items in this prescription.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Prescription not found"},
    },
)
async def normalize_prescription(
    request: Request,
    patient_id: str,
    prescription_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    prescription_service: Annotated[PrescriptionService, Depends(get_prescription_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
) -> StandardSuccessResponse[PrescriptionNormalizeResponse]:
    """Trigger normalization for prescription items."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="prescription:normalize",
        resource_type="prescription",
        resource_id=prescription_id,
        consent_scope="prescriptions",
    )

    result = await prescription_service.normalize_prescription(
        patient_id=patient_id,
        prescription_id=prescription_id,
        actor_id=current_user.user_id,
    )
    return StandardSuccessResponse(data=result, request_id=_req_id(request))


@router.get(
    "/{prescription_id}/items/{item_id}",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[PrescriptionItemResponse],
    summary="Get prescription item",
    description="Retrieve details and normalization status of a specific prescription item.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Item not found"},
    },
)
async def get_prescription_item(
    request: Request,
    patient_id: str,
    prescription_id: str,
    item_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    prescription_service: Annotated[PrescriptionService, Depends(get_prescription_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
) -> StandardSuccessResponse[PrescriptionItemResponse]:
    """Retrieve single prescription item."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="prescription:read",
        resource_type="prescription_item",
        resource_id=item_id,
        consent_scope="prescriptions",
    )

    item = await prescription_service.get_prescription_item(
        patient_id=patient_id, prescription_id=prescription_id, item_id=item_id
    )
    return StandardSuccessResponse(data=item, request_id=_req_id(request))
