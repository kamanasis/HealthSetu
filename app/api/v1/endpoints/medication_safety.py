"""Medication Safety API Endpoints (Phase 7).

CRITICAL CLINICAL & SECURITY POLICIES:
- Requires authentication and strict patient authorization via verify_patient_access.
- Doctors must have an active relationship and valid patient consent.
- Admin role has ZERO access to clinical safety evaluations.
- Cross-patient enumeration returns 404.
- Safety findings are clinical decision-support evidence, NOT autonomous clinical decisions.
- Mandatory clinical disclaimer is always returned.
"""

from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import (
    get_audit_service,
    get_authorization_service,
    get_current_user,
    get_medication_safety_provider_dep,
    get_medication_safety_service,
    get_patient_service,
    verify_patient_access,
)
from app.core.logging import request_id_ctx_var
from app.integrations.medication_safety.base import MedicationSafetyProvider
from app.integrations.medication_safety.registry import get_safety_capabilities
from app.schemas.medication_safety import (
    PatientSafetyCheckRequest,
    ProspectiveMedicationsCheckRequest,
    SafetyEvaluationListResponse,
    SafetyEvaluationResponse,
    SafetyEvaluationStatus,
    SafetyProviderCapabilities,
)
from app.schemas.response import StandardErrorResponse, StandardSuccessResponse
from app.schemas.user import AuthenticatedUserContext
from app.services.audit_service import AuditService
from app.services.authorization_service import AuthorizationService
from app.services.medication_safety_service import MedicationSafetyService
from app.services.patient_service import PatientService

router = APIRouter(prefix="/patients/{patient_id}/medication-safety", tags=["Medication Safety"])


def _req_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request_id_ctx_var.get() or "unknown"


@router.post(
    "/check",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[SafetyEvaluationResponse],
    summary="Evaluate patient active medications safety",
    description=(
        "Evaluates the patient's current active medications or selected medications against configured "
        "authoritative safety providers (DDIs, allergy conflicts, drug-disease interactions, duplicate therapy)."
    ),
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied or consent required"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
    },
)
async def check_patient_medications(
    request: Request,
    patient_id: str,
    payload: PatientSafetyCheckRequest,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    safety_service: Annotated[MedicationSafetyService, Depends(get_medication_safety_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
) -> StandardSuccessResponse[SafetyEvaluationResponse]:
    """Evaluate patient's active or selected medication list."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="medication_safety:check",
        resource_type="medication_safety",
        consent_scope="medications",
    )

    evaluation = await safety_service.evaluate_patient_safety(
        patient_id=patient_id,
        request=payload,
        actor_id=current_user.user_id,
    )
    return StandardSuccessResponse(
        data=evaluation,
        request_id=_req_id(request),
    )


@router.post(
    "/check-medications",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[SafetyEvaluationResponse],
    summary="Evaluate prospective medications",
    description=(
        "Evaluates prospective new medications (e.g. before prescribing) optionally cross-checking "
        "against current active medications, allergies, and documented clinical conditions."
    ),
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied or consent required"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
    },
)
async def check_prospective_medications(
    request: Request,
    patient_id: str,
    payload: ProspectiveMedicationsCheckRequest,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    safety_service: Annotated[MedicationSafetyService, Depends(get_medication_safety_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
) -> StandardSuccessResponse[SafetyEvaluationResponse]:
    """Evaluate prospective medications against current patient clinical context."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="medication_safety:check",
        resource_type="medication_safety",
        consent_scope="medications",
    )

    evaluation = await safety_service.evaluate_prospective_medications(
        patient_id=patient_id,
        request=payload,
        actor_id=current_user.user_id,
    )
    return StandardSuccessResponse(
        data=evaluation,
        request_id=_req_id(request),
    )


@router.get(
    "/capabilities",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[SafetyProviderCapabilities],
    summary="Get configured safety provider capabilities",
    description="Returns metadata detailing which safety check types are supported by the configured provider.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
    },
)
async def get_capabilities(
    request: Request,
    patient_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    provider: Annotated[MedicationSafetyProvider, Depends(get_medication_safety_provider_dep)],
) -> StandardSuccessResponse[SafetyProviderCapabilities]:
    """Retrieve capabilities supported by the configured medication safety provider."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="medication_safety:read",
        resource_type="medication_safety",
        consent_scope="medications",
    )

    caps = get_safety_capabilities(provider)
    return StandardSuccessResponse(
        data=caps,
        request_id=_req_id(request),
    )


@router.get(
    "/evaluations/{evaluation_id}",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[SafetyEvaluationResponse],
    summary="Get safety evaluation details",
    description="Retrieve a historical medication safety evaluation with full alert details and provenance.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied or consent required"},
        404: {"model": StandardErrorResponse, "description": "Evaluation or patient not found"},
    },
)
async def get_safety_evaluation(
    request: Request,
    patient_id: str,
    evaluation_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    safety_service: Annotated[MedicationSafetyService, Depends(get_medication_safety_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
) -> StandardSuccessResponse[SafetyEvaluationResponse]:
    """Retrieve details of a historical safety evaluation."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="medication_safety:read",
        resource_type="medication_safety",
        resource_id=evaluation_id,
        consent_scope="medications",
    )

    evaluation = await safety_service.get_evaluation(
        patient_id=patient_id,
        evaluation_id=evaluation_id,
        actor_id=current_user.user_id,
    )
    return StandardSuccessResponse(
        data=evaluation,
        request_id=_req_id(request),
    )


@router.get(
    "/evaluations",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[SafetyEvaluationListResponse],
    summary="List patient safety evaluations",
    description="List historical medication safety evaluations with pagination and status/date filtering.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied or consent required"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
    },
)
async def list_safety_evaluations(
    request: Request,
    patient_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    safety_service: Annotated[MedicationSafetyService, Depends(get_medication_safety_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    status_filter: Annotated[SafetyEvaluationStatus | None, Query(alias="status")] = None,
    start_date: Annotated[datetime | None, Query()] = None,
    end_date: Annotated[datetime | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> StandardSuccessResponse[SafetyEvaluationListResponse]:
    """List historical safety evaluations for a patient."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="medication_safety:read",
        resource_type="medication_safety",
        consent_scope="medications",
    )

    result = await safety_service.list_evaluations(
        patient_id=patient_id,
        status=status_filter,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )
    return StandardSuccessResponse(
        data=result,
        request_id=_req_id(request),
    )
