"""Doctor Clinical Workflow API Endpoints (Phase 10).

Provides three endpoint groups for authorized clinicians:

1. /clinical-workspace    — Consolidated read-only workspace view
2. /clinical-notes        — CRUD + sign lifecycle for clinical notes
3. /clinical-assessments  — CRUD + finalize lifecycle for clinical assessments
4. /clinical-plans        — CRUD + finalize lifecycle for clinical plans

AUTHORIZATION:
  - All endpoints require DOCTOR role with an authorized patient relationship and consent.
  - clinician_id is ALWAYS sourced from the server-side JWT (current_user.user_id).
  - The client must never supply clinician_id in the request body.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import (
    get_authorization_service,
    get_current_user,
    get_patient_service,
    verify_patient_access,
    get_clinical_note_service,
    get_clinical_assessment_service,
    get_clinical_plan_service,
    get_clinical_workspace_service,
)
from app.core.logging import request_id_ctx_var
from app.schemas.clinical_workflow import (
    ClinicalAssessmentCreate,
    ClinicalAssessmentFinalize,
    ClinicalAssessmentListResponse,
    ClinicalAssessmentResponse,
    ClinicalAssessmentType,
    ClinicalAssessmentUpdate,
    ClinicalNoteCreate,
    ClinicalNoteListResponse,
    ClinicalNoteResponse,
    ClinicalNoteSign,
    ClinicalNoteType,
    ClinicalNoteUpdate,
    ClinicalPlanCreate,
    ClinicalPlanFinalize,
    ClinicalPlanListResponse,
    ClinicalPlanResponse,
    ClinicalPlanStatus,
    ClinicalPlanType,
    ClinicalPlanUpdate,
    ClinicalWorkspaceResponse,
)
from app.schemas.response import StandardErrorResponse, StandardSuccessResponse
from app.schemas.user import AuthenticatedUserContext
from app.services.authorization_service import AuthorizationService
from app.services.clinical_assessment_service import ClinicalAssessmentService
from app.services.clinical_note_service import ClinicalNoteService
from app.services.clinical_plan_service import ClinicalPlanService
from app.services.clinical_workspace_service import ClinicalWorkspaceService
from app.services.patient_service import PatientService

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/patients/{patient_id}", tags=["Doctor Clinical Workflow"])


def _req_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request_id_ctx_var.get() or "unknown"


# ============================================================================
# Clinical Workspace
# ============================================================================

@router.get(
    "/clinical-workspace",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[ClinicalWorkspaceResponse],
    summary="Open consolidated clinical workspace",
    description=(
        "Returns a consolidated clinical workspace view for an authorized clinician. "
        "Aggregates patient demographics, domain summary counts, and the most recent "
        "clinical notes, assessments, and active plans across all phases. "
        "Requires DOCTOR role with authorized patient relationship and care_delivery consent."
    ),
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied — DOCTOR role + consent required"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
    },
)
async def get_clinical_workspace(
    patient_id: str,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    workspace_service: Annotated[ClinicalWorkspaceService, Depends(get_clinical_workspace_service)],
    encounter_id: str | None = Query(None, description="Optional encounter scope filter"),
) -> StandardSuccessResponse[ClinicalWorkspaceResponse]:
    """Open the consolidated clinical workspace for a patient."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="clinical_workspace:read",
        resource_type="clinical_workspace",
        consent_scope="clinical_records",
    )

    result = await workspace_service.get_workspace(
        patient_id=patient_id,
        clinician_id=current_user.user_id,
        encounter_id=encounter_id,
    )

    return StandardSuccessResponse(data=result, request_id=_req_id(request))


# ============================================================================
# Clinical Notes
# ============================================================================

@router.post(
    "/clinical-notes",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardSuccessResponse[ClinicalNoteResponse],
    summary="Create clinical note",
    description=(
        "Creates a new clinician-authored clinical note (SOAP, Progress, Consultation, etc.). "
        "The clinician identity is sourced from the authenticated JWT — never from the request body."
    ),
    responses={
        400: {"model": StandardErrorResponse, "description": "Invalid input or addendum reference"},
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Patient or parent note not found"},
    },
)
async def create_clinical_note(
    patient_id: str,
    payload: ClinicalNoteCreate,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    note_service: Annotated[ClinicalNoteService, Depends(get_clinical_note_service)],
) -> StandardSuccessResponse[ClinicalNoteResponse]:
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="clinical_note:create",
        resource_type="clinical_note",
        consent_scope="clinical_records",
    )

    result = await note_service.create_note(
        patient_id=patient_id,
        payload=payload,
        clinician_id=current_user.user_id,  # ALWAYS from JWT
    )
    return StandardSuccessResponse(data=result, request_id=_req_id(request))


@router.get(
    "/clinical-notes",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[ClinicalNoteListResponse],
    summary="List clinical notes",
    description="Retrieves a paginated list of clinical notes for a patient.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
    },
)
async def list_clinical_notes(
    patient_id: str,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    note_service: Annotated[ClinicalNoteService, Depends(get_clinical_note_service)],
    note_type: ClinicalNoteType | None = Query(None, description="Filter by note type"),
    encounter_id: str | None = Query(None, description="Filter by encounter"),
    signed_only: bool = Query(False, description="Only return signed notes"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> StandardSuccessResponse[ClinicalNoteListResponse]:
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="clinical_note:read",
        resource_type="clinical_note",
        consent_scope="clinical_records",
    )

    result = await note_service.list_notes(
        patient_id=patient_id,
        actor_id=current_user.user_id,
        limit=limit,
        offset=offset,
        note_type=note_type,
        encounter_id=encounter_id,
        signed_only=signed_only,
    )
    return StandardSuccessResponse(data=result, request_id=_req_id(request))


@router.get(
    "/clinical-notes/{note_id}",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[ClinicalNoteResponse],
    summary="Get clinical note",
    description="Retrieves a specific clinical note by ID.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Clinical note not found"},
    },
)
async def get_clinical_note(
    patient_id: str,
    note_id: str,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    note_service: Annotated[ClinicalNoteService, Depends(get_clinical_note_service)],
) -> StandardSuccessResponse[ClinicalNoteResponse]:
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="clinical_note:read",
        resource_type="clinical_note",
        resource_id=note_id,
        consent_scope="clinical_records",
    )

    result = await note_service.get_note(
        patient_id=patient_id,
        note_id=note_id,
        actor_id=current_user.user_id,
    )
    return StandardSuccessResponse(data=result, request_id=_req_id(request))


@router.patch(
    "/clinical-notes/{note_id}",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[ClinicalNoteResponse],
    summary="Update clinical note",
    description=(
        "Updates a clinical note. Only the authoring clinician may update. "
        "Signed notes are immutable — create an addendum instead. "
        "Requires the current version for optimistic concurrency."
    ),
    responses={
        400: {"model": StandardErrorResponse, "description": "Invalid input"},
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied or not authoring clinician"},
        404: {"model": StandardErrorResponse, "description": "Clinical note not found"},
        409: {"model": StandardErrorResponse, "description": "Note signed or version conflict"},
    },
)
async def update_clinical_note(
    patient_id: str,
    note_id: str,
    payload: ClinicalNoteUpdate,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    note_service: Annotated[ClinicalNoteService, Depends(get_clinical_note_service)],
) -> StandardSuccessResponse[ClinicalNoteResponse]:
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="clinical_note:update",
        resource_type="clinical_note",
        resource_id=note_id,
        consent_scope="clinical_records",
    )

    result = await note_service.update_note(
        patient_id=patient_id,
        note_id=note_id,
        payload=payload,
        clinician_id=current_user.user_id,
    )
    return StandardSuccessResponse(data=result, request_id=_req_id(request))


@router.post(
    "/clinical-notes/{note_id}/sign",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[ClinicalNoteResponse],
    summary="Sign (lock) a clinical note",
    description=(
        "Signs and locks a clinical note. Once signed, the note is immutable. "
        "Only the authoring clinician may sign. "
        "Requires the current version for optimistic concurrency."
    ),
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied or not authoring clinician"},
        404: {"model": StandardErrorResponse, "description": "Clinical note not found"},
        409: {"model": StandardErrorResponse, "description": "Already signed or version conflict"},
    },
)
async def sign_clinical_note(
    patient_id: str,
    note_id: str,
    payload: ClinicalNoteSign,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    note_service: Annotated[ClinicalNoteService, Depends(get_clinical_note_service)],
) -> StandardSuccessResponse[ClinicalNoteResponse]:
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="clinical_note:sign",
        resource_type="clinical_note",
        resource_id=note_id,
        consent_scope="clinical_records",
    )

    result = await note_service.sign_note(
        patient_id=patient_id,
        note_id=note_id,
        payload=payload,
        clinician_id=current_user.user_id,
    )
    return StandardSuccessResponse(data=result, request_id=_req_id(request))


# ============================================================================
# Clinical Assessments
# ============================================================================

@router.post(
    "/clinical-assessments",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardSuccessResponse[ClinicalAssessmentResponse],
    summary="Create clinical assessment",
    description=(
        "Creates a new clinician-authored clinical assessment (DIAGNOSIS, DIFFERENTIAL, etc.). "
        "The clinician identity is sourced from the authenticated JWT."
    ),
    responses={
        400: {"model": StandardErrorResponse, "description": "Invalid input"},
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
    },
)
async def create_clinical_assessment(
    patient_id: str,
    payload: ClinicalAssessmentCreate,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    assessment_service: Annotated[ClinicalAssessmentService, Depends(get_clinical_assessment_service)],
) -> StandardSuccessResponse[ClinicalAssessmentResponse]:
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="clinical_assessment:create",
        resource_type="clinical_assessment",
        consent_scope="clinical_records",
    )

    result = await assessment_service.create_assessment(
        patient_id=patient_id,
        payload=payload,
        clinician_id=current_user.user_id,
    )
    return StandardSuccessResponse(data=result, request_id=_req_id(request))


@router.get(
    "/clinical-assessments",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[ClinicalAssessmentListResponse],
    summary="List clinical assessments",
    description="Retrieves a paginated list of clinical assessments for a patient.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
    },
)
async def list_clinical_assessments(
    patient_id: str,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    assessment_service: Annotated[ClinicalAssessmentService, Depends(get_clinical_assessment_service)],
    assessment_type: ClinicalAssessmentType | None = Query(None),
    encounter_id: str | None = Query(None),
    finalized_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> StandardSuccessResponse[ClinicalAssessmentListResponse]:
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="clinical_assessment:read",
        resource_type="clinical_assessment",
        consent_scope="clinical_records",
    )

    result = await assessment_service.list_assessments(
        patient_id=patient_id,
        actor_id=current_user.user_id,
        limit=limit,
        offset=offset,
        assessment_type=assessment_type,
        encounter_id=encounter_id,
        finalized_only=finalized_only,
    )
    return StandardSuccessResponse(data=result, request_id=_req_id(request))


@router.get(
    "/clinical-assessments/{assessment_id}",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[ClinicalAssessmentResponse],
    summary="Get clinical assessment",
    description="Retrieves a specific clinical assessment by ID.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Assessment not found"},
    },
)
async def get_clinical_assessment(
    patient_id: str,
    assessment_id: str,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    assessment_service: Annotated[ClinicalAssessmentService, Depends(get_clinical_assessment_service)],
) -> StandardSuccessResponse[ClinicalAssessmentResponse]:
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="clinical_assessment:read",
        resource_type="clinical_assessment",
        resource_id=assessment_id,
        consent_scope="clinical_records",
    )

    result = await assessment_service.get_assessment(
        patient_id=patient_id,
        assessment_id=assessment_id,
        actor_id=current_user.user_id,
    )
    return StandardSuccessResponse(data=result, request_id=_req_id(request))


@router.patch(
    "/clinical-assessments/{assessment_id}",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[ClinicalAssessmentResponse],
    summary="Update clinical assessment",
    description=(
        "Updates a clinical assessment. Non-finalized only. "
        "Only the authoring clinician may update. "
        "Requires expected_version for optimistic concurrency."
    ),
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied or not authoring clinician"},
        404: {"model": StandardErrorResponse, "description": "Assessment not found"},
        409: {"model": StandardErrorResponse, "description": "Finalized or version conflict"},
    },
)
async def update_clinical_assessment(
    patient_id: str,
    assessment_id: str,
    payload: ClinicalAssessmentUpdate,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    assessment_service: Annotated[ClinicalAssessmentService, Depends(get_clinical_assessment_service)],
) -> StandardSuccessResponse[ClinicalAssessmentResponse]:
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="clinical_assessment:update",
        resource_type="clinical_assessment",
        resource_id=assessment_id,
        consent_scope="clinical_records",
    )

    result = await assessment_service.update_assessment(
        patient_id=patient_id,
        assessment_id=assessment_id,
        payload=payload,
        clinician_id=current_user.user_id,
    )
    return StandardSuccessResponse(data=result, request_id=_req_id(request))


@router.post(
    "/clinical-assessments/{assessment_id}/finalize",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[ClinicalAssessmentResponse],
    summary="Finalize (lock) a clinical assessment",
    description=(
        "Finalizes and locks a clinical assessment. "
        "Only the authoring clinician may finalize."
    ),
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied or not authoring clinician"},
        404: {"model": StandardErrorResponse, "description": "Assessment not found"},
        409: {"model": StandardErrorResponse, "description": "Already finalized or version conflict"},
    },
)
async def finalize_clinical_assessment(
    patient_id: str,
    assessment_id: str,
    payload: ClinicalAssessmentFinalize,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    assessment_service: Annotated[ClinicalAssessmentService, Depends(get_clinical_assessment_service)],
) -> StandardSuccessResponse[ClinicalAssessmentResponse]:
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="clinical_assessment:finalize",
        resource_type="clinical_assessment",
        resource_id=assessment_id,
        consent_scope="clinical_records",
    )

    result = await assessment_service.finalize_assessment(
        patient_id=patient_id,
        assessment_id=assessment_id,
        payload=payload,
        clinician_id=current_user.user_id,
    )
    return StandardSuccessResponse(data=result, request_id=_req_id(request))


# ============================================================================
# Clinical Plans
# ============================================================================

@router.post(
    "/clinical-plans",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardSuccessResponse[ClinicalPlanResponse],
    summary="Create clinical plan",
    description=(
        "Creates a new clinician-authored clinical plan (TREATMENT, MANAGEMENT, etc.). "
        "The clinician identity is sourced from the authenticated JWT."
    ),
    responses={
        400: {"model": StandardErrorResponse, "description": "Invalid input"},
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
    },
)
async def create_clinical_plan(
    patient_id: str,
    payload: ClinicalPlanCreate,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    plan_service: Annotated[ClinicalPlanService, Depends(get_clinical_plan_service)],
) -> StandardSuccessResponse[ClinicalPlanResponse]:
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="clinical_plan:create",
        resource_type="clinical_plan",
        consent_scope="clinical_records",
    )

    result = await plan_service.create_plan(
        patient_id=patient_id,
        payload=payload,
        clinician_id=current_user.user_id,
    )
    return StandardSuccessResponse(data=result, request_id=_req_id(request))


@router.get(
    "/clinical-plans",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[ClinicalPlanListResponse],
    summary="List clinical plans",
    description="Retrieves a paginated list of clinical plans for a patient.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Patient not found"},
    },
)
async def list_clinical_plans(
    patient_id: str,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    plan_service: Annotated[ClinicalPlanService, Depends(get_clinical_plan_service)],
    plan_type: ClinicalPlanType | None = Query(None),
    plan_status: ClinicalPlanStatus | None = Query(None, alias="status"),
    encounter_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> StandardSuccessResponse[ClinicalPlanListResponse]:
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="clinical_plan:read",
        resource_type="clinical_plan",
        consent_scope="clinical_records",
    )

    result = await plan_service.list_plans(
        patient_id=patient_id,
        actor_id=current_user.user_id,
        limit=limit,
        offset=offset,
        plan_type=plan_type,
        status=plan_status,
        encounter_id=encounter_id,
    )
    return StandardSuccessResponse(data=result, request_id=_req_id(request))


@router.get(
    "/clinical-plans/{plan_id}",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[ClinicalPlanResponse],
    summary="Get clinical plan",
    description="Retrieves a specific clinical plan by ID.",
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied"},
        404: {"model": StandardErrorResponse, "description": "Plan not found"},
    },
)
async def get_clinical_plan(
    patient_id: str,
    plan_id: str,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    plan_service: Annotated[ClinicalPlanService, Depends(get_clinical_plan_service)],
) -> StandardSuccessResponse[ClinicalPlanResponse]:
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="clinical_plan:read",
        resource_type="clinical_plan",
        resource_id=plan_id,
        consent_scope="clinical_records",
    )

    result = await plan_service.get_plan(
        patient_id=patient_id,
        plan_id=plan_id,
        actor_id=current_user.user_id,
    )
    return StandardSuccessResponse(data=result, request_id=_req_id(request))


@router.patch(
    "/clinical-plans/{plan_id}",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[ClinicalPlanResponse],
    summary="Update clinical plan",
    description=(
        "Updates a clinical plan. Non-finalized only. "
        "Only the authoring clinician may update. "
        "Requires expected_version for optimistic concurrency."
    ),
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied or not authoring clinician"},
        404: {"model": StandardErrorResponse, "description": "Plan not found"},
        409: {"model": StandardErrorResponse, "description": "Finalized or version conflict"},
    },
)
async def update_clinical_plan(
    patient_id: str,
    plan_id: str,
    payload: ClinicalPlanUpdate,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    plan_service: Annotated[ClinicalPlanService, Depends(get_clinical_plan_service)],
) -> StandardSuccessResponse[ClinicalPlanResponse]:
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="clinical_plan:update",
        resource_type="clinical_plan",
        resource_id=plan_id,
        consent_scope="clinical_records",
    )

    result = await plan_service.update_plan(
        patient_id=patient_id,
        plan_id=plan_id,
        payload=payload,
        clinician_id=current_user.user_id,
    )
    return StandardSuccessResponse(data=result, request_id=_req_id(request))


@router.post(
    "/clinical-plans/{plan_id}/finalize",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[ClinicalPlanResponse],
    summary="Finalize (lock) a clinical plan",
    description=(
        "Finalizes and locks a clinical plan. "
        "Only the authoring clinician may finalize."
    ),
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Access denied or not authoring clinician"},
        404: {"model": StandardErrorResponse, "description": "Plan not found"},
        409: {"model": StandardErrorResponse, "description": "Already finalized or version conflict"},
    },
)
async def finalize_clinical_plan(
    patient_id: str,
    plan_id: str,
    payload: ClinicalPlanFinalize,
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    plan_service: Annotated[ClinicalPlanService, Depends(get_clinical_plan_service)],
) -> StandardSuccessResponse[ClinicalPlanResponse]:
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="clinical_plan:finalize",
        resource_type="clinical_plan",
        resource_id=plan_id,
        consent_scope="clinical_records",
    )

    result = await plan_service.finalize_plan(
        patient_id=patient_id,
        plan_id=plan_id,
        payload=payload,
        clinician_id=current_user.user_id,
    )
    return StandardSuccessResponse(data=result, request_id=_req_id(request))
