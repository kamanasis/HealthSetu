"""Structured Symptom Intake API Endpoints (Phase 8).

Endpoints for patient symptom reporting, session tracking, and normalization.
Authorization:
- Requires authentication.
- Strict patient boundary and relationship/consent checks.
- Zero clinical access for administrators.
"""

from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import (
    get_authorization_service,
    get_current_user,
    get_patient_service,
    get_symptom_service,
    verify_patient_access,
)
from app.core.logging import request_id_ctx_var
from app.schemas.response import StandardErrorResponse, StandardSuccessResponse
from app.schemas.symptom import (
    SymptomIntakeCreate,
    SymptomIntakeResponse,
    SymptomListResponse,
    SymptomRecord,
    SymptomSource,
)
from app.schemas.user import AuthenticatedUserContext
from app.services.authorization_service import AuthorizationService
from app.services.patient_service import PatientService
from app.services.symptom_service import SymptomService

router = APIRouter(prefix="/patients/{patient_id}/symptoms", tags=["Symptom Intake"])


def _req_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request_id_ctx_var.get() or "unknown"


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardSuccessResponse[SymptomIntakeResponse],
    summary="Record structured symptom intake session",
    description="Records one or more structured symptoms for a patient, preserving provenance and normalizing terminology.",
    responses={
        400: {"model": StandardErrorResponse, "description": "Invalid symptom intake payload"},
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied or insufficient consent"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
    },
)
async def record_symptoms(
    patient_id: str,
    payload: SymptomIntakeCreate,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    symptom_service: Annotated[SymptomService, Depends(get_symptom_service)],
) -> StandardSuccessResponse[SymptomIntakeResponse]:
    """Record structured symptoms for patient."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="symptom:create",
        resource_type="symptom",
        consent_scope="symptoms",
    )

    result = await symptom_service.record_symptom_intake(
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
    response_model=StandardSuccessResponse[SymptomListResponse],
    summary="List patient symptoms",
    description="Retrieves a paginated list of recorded symptoms with optional filtering.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied or insufficient consent"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
    },
)
async def list_symptoms(
    patient_id: str,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    symptom_service: Annotated[SymptomService, Depends(get_symptom_service)],
    limit: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
    offset: Annotated[int, Query(ge=0, description="Offset for pagination")] = 0,
    source: Annotated[SymptomSource | None, Query(description="Filter by symptom source provenance")] = None,
    encounter_id: Annotated[str | None, Query(description="Filter by clinical encounter ID")] = None,
    start_date: Annotated[datetime | None, Query(description="Filter by earliest creation date")] = None,
    end_date: Annotated[datetime | None, Query(description="Filter by latest creation date")] = None,
) -> StandardSuccessResponse[SymptomListResponse]:
    """List paginated symptoms for a patient."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="symptom:read",
        resource_type="symptom",
        consent_scope="symptoms",
    )

    result = await symptom_service.list_patient_symptoms(
        patient_id=patient_id,
        actor_id=current_user.user_id,
        limit=limit,
        offset=offset,
        source=source,
        encounter_id=encounter_id,
        start_date=start_date,
        end_date=end_date,
    )

    return StandardSuccessResponse(
        data=result,
        request_id=_req_id(request),
    )


@router.get(
    "/{symptom_id}",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[SymptomRecord],
    summary="Get single symptom record",
    description="Retrieves a specific structured symptom record by ID.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied or insufficient consent"},
        404: {"model": StandardErrorResponse, "description": "Symptom not found"},
    },
)
async def get_symptom(
    patient_id: str,
    symptom_id: str,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    symptom_service: Annotated[SymptomService, Depends(get_symptom_service)],
) -> StandardSuccessResponse[SymptomRecord]:
    """Retrieve an individual symptom record."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="symptom:read",
        resource_type="symptom",
        resource_id=symptom_id,
        consent_scope="symptoms",
    )

    record = await symptom_service.get_symptom_by_id(
        patient_id=patient_id,
        symptom_id=symptom_id,
        actor_id=current_user.user_id,
    )

    return StandardSuccessResponse(
        data=record,
        request_id=_req_id(request),
    )
