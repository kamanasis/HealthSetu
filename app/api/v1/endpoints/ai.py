"""AI Intelligence Layer API Endpoints (Phase 14).

Provides endpoints for:
- Task submission (POST /api/v1/ai/tasks)
- Task status retrieval (GET /api/v1/ai/tasks/{task_id})
- Task result retrieval (GET /api/v1/ai/tasks/{task_id}/result)
- Clinician result verification (POST /api/v1/ai/results/{result_id}/verify)
- Patient-scoped convenience helpers:
  - POST /api/v1/patients/{patient_id}/ai/summarize
  - POST /api/v1/patients/{patient_id}/ai/explain
  - POST /api/v1/patients/{patient_id}/ai/sbar-assist

CRITICAL ARCHITECTURAL CONSTRAINTS:
- No open-ended /chat or /generate endpoints.
- All AI results enter REVIEW_REQUIRED status.
- Only clinicians can verify AI output.
- AI output is NOT authoritative clinical truth.
"""

from typing import Annotated, Any, Dict, Optional
from fastapi import APIRouter, Depends, Path, Request, status

from app.api.deps import (
    get_ai_service,
    get_audit_service,
    get_authorization_service,
    get_current_user,
    get_patient_service,
    require_permission,
    verify_patient_access,
)
from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.logging import request_id_ctx_var
from app.core.policies import Permission
from app.schemas.auth import UserRole
from app.schemas.ai import AITaskType
from app.schemas.ai_results import AIResultRecord, AIResultResponse, AIVerificationRequest
from app.schemas.ai_tasks import AITaskCreateRequest, AITaskRecord, AITaskResponse
from app.schemas.response import StandardSuccessResponse
from app.schemas.user import AuthenticatedUserContext
from app.services.ai_service import AIService
from app.services.audit_service import AuditService
from app.services.authorization_service import AuthorizationService
from app.services.patient_service import PatientService

router = APIRouter(tags=["AI Intelligence Layer"])


def _req_id(request: Request) -> str:
    """Helper to extract request ID for correlation envelope."""
    return getattr(request.state, "request_id", None) or request_id_ctx_var.get() or "unknown"


# ---------------------------------------------------------------------------
# Core Task Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/ai/tasks",
    response_model=StandardSuccessResponse[AITaskRecord],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit an AI assistance task",
    description=(
        "Queues an approved AI task for execution. "
        "All results enter REVIEW_REQUIRED status and must be clinician-verified. "
        "AI output is never authoritative clinical truth."
    ),
    operation_id="create_ai_task",
)
async def create_ai_task(
    http_request: Request,
    request: AITaskCreateRequest,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    ai_service: Annotated[AIService, Depends(get_ai_service)],
    _: Annotated[None, Depends(require_permission(Permission.AI_EXECUTE))],
) -> StandardSuccessResponse[AITaskRecord]:
    """Submit an AI assistance task for queuing and processing."""
    task = await ai_service.submit_task(
        request=request,
        user_context=current_user,
        source_content=request.source_content,
    )
    # Execute immediately (synchronous processing for responsiveness)
    try:
        await ai_service.execute_task(task.id, user_context=current_user)
        task = await ai_service.task_service.get_task(task.id)
    except Exception:
        # Return task even if execution fails; client can inspect status
        pass

    return StandardSuccessResponse(
        success=True,
        data=task,
        request_id=_req_id(http_request),
    )


@router.get(
    "/ai/tasks/{task_id}",
    response_model=StandardSuccessResponse[AITaskRecord],
    summary="Retrieve AI task status",
    operation_id="get_ai_task",
)
async def get_ai_task(
    http_request: Request,
    task_id: Annotated[str, Path(description="AI task ID")],
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    ai_service: Annotated[AIService, Depends(get_ai_service)],
    _: Annotated[None, Depends(require_permission(Permission.AI_READ))],
) -> StandardSuccessResponse[AITaskRecord]:
    """Retrieve AI task status and metadata by task ID."""
    task = await ai_service.task_service.get_task(task_id)
    return StandardSuccessResponse(
        success=True,
        data=task,
        request_id=_req_id(http_request),
    )


@router.get(
    "/ai/tasks/{task_id}/result",
    response_model=StandardSuccessResponse[AIResultRecord],
    summary="Retrieve AI task result (REVIEW_REQUIRED)",
    description=(
        "Returns AI-generated output in REVIEW_REQUIRED state. "
        "This result is NOT authoritative until verified by a qualified clinician."
    ),
    operation_id="get_ai_task_result",
)
async def get_ai_task_result(
    http_request: Request,
    task_id: Annotated[str, Path(description="AI task ID")],
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    ai_service: Annotated[AIService, Depends(get_ai_service)],
    _: Annotated[None, Depends(require_permission(Permission.AI_READ))],
) -> StandardSuccessResponse[AIResultRecord]:
    """Retrieve structured AI output associated with a completed task."""
    result = await ai_service.repository.get_result_by_task_id(task_id)
    if not result:
        raise NotFoundException(f"No result found for AI task '{task_id}'.")
    return StandardSuccessResponse(
        success=True,
        data=result,
        request_id=_req_id(http_request),
    )


@router.post(
    "/ai/results/{result_id}/verify",
    response_model=StandardSuccessResponse[AIResultRecord],
    summary="Clinician verification of AI result",
    description=(
        "Allows an authorized clinician to VERIFY, CORRECT, or REJECT an AI-generated output. "
        "This is the mandatory clinical review gate. AI output cannot self-verify."
    ),
    operation_id="verify_ai_result",
)
async def verify_ai_result(
    http_request: Request,
    result_id: Annotated[str, Path(description="AI result ID")],
    verification_req: AIVerificationRequest,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    ai_service: Annotated[AIService, Depends(get_ai_service)],
    _: Annotated[None, Depends(require_permission(Permission.AI_VERIFY))],
) -> StandardSuccessResponse[AIResultRecord]:
    """Clinician reviews and verifies, corrects, or rejects an AI result."""
    result = await ai_service.verify_result(
        result_id=result_id,
        verification_req=verification_req,
        user_context=current_user,
    )
    return StandardSuccessResponse(
        success=True,
        data=result,
        request_id=_req_id(http_request),
    )


# ---------------------------------------------------------------------------
# Patient-Scoped AI Convenience Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/patients/{patient_id}/ai/summarize",
    response_model=StandardSuccessResponse[AIResultRecord],
    status_code=status.HTTP_200_OK,
    summary="AI clinical summary assistance (REVIEW_REQUIRED)",
    description=(
        "Generates an AI-assisted clinical summary for the patient. "
        "Result enters REVIEW_REQUIRED state and is NOT authoritative until clinician-verified."
    ),
    operation_id="patient_ai_summarize",
)
async def patient_ai_summarize(
    http_request: Request,
    patient_id: Annotated[str, Path(description="Patient ID")],
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    ai_service: Annotated[AIService, Depends(get_ai_service)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    _: Annotated[None, Depends(require_permission(Permission.AI_EXECUTE))],
    body: Optional[Dict[str, Any]] = None,
) -> StandardSuccessResponse[AIResultRecord]:
    """Generate an AI-assisted clinical summary (clinician must verify)."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action=Permission.AI_EXECUTE.value,
        resource_type="patient",
        consent_scope=None,
    )
    payload_ctx = body or {}
    source_content = payload_ctx.get("source_content") or f"Patient ID {patient_id} clinical record synthesis."
    create_req = AITaskCreateRequest(
        task_type=AITaskType.CLINICAL_SUMMARY,
        patient_id=patient_id,
        source_content=source_content,
        input_context=payload_ctx,
    )
    task = await ai_service.submit_task(request=create_req, user_context=current_user, source_content=source_content)
    result = await ai_service.execute_task(task.id, user_context=current_user)
    return StandardSuccessResponse(
        success=True,
        data=result,
        request_id=_req_id(http_request),
    )


@router.post(
    "/patients/{patient_id}/ai/explain",
    response_model=StandardSuccessResponse[AIResultRecord],
    status_code=status.HTTP_200_OK,
    summary="AI patient-friendly explanation (REVIEW_REQUIRED)",
    description=(
        "Generates a simplified patient-friendly explanation of clinical information. "
        "Result enters REVIEW_REQUIRED state. Must be reviewed before sharing with patient."
    ),
    operation_id="patient_ai_explain",
)
async def patient_ai_explain(
    http_request: Request,
    patient_id: Annotated[str, Path(description="Patient ID")],
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    ai_service: Annotated[AIService, Depends(get_ai_service)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    _: Annotated[None, Depends(require_permission(Permission.AI_EXECUTE))],
    body: Optional[Dict[str, Any]] = None,
) -> StandardSuccessResponse[AIResultRecord]:
    """Generate a patient-friendly explanation (clinician must verify before sharing)."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action=Permission.AI_EXECUTE.value,
        resource_type="patient",
        consent_scope=None,
    )
    payload_ctx = body or {}
    source_content = (
        payload_ctx.get("text_to_explain")
        or payload_ctx.get("source_content")
        or "Clinical text for explanation."
    )
    create_req = AITaskCreateRequest(
        task_type=AITaskType.PATIENT_EXPLANATION,
        patient_id=patient_id,
        source_content=source_content,
        input_context=payload_ctx,
    )
    task = await ai_service.submit_task(request=create_req, user_context=current_user, source_content=source_content)
    result = await ai_service.execute_task(task.id, user_context=current_user)
    return StandardSuccessResponse(
        success=True,
        data=result,
        request_id=_req_id(http_request),
    )


@router.post(
    "/patients/{patient_id}/ai/sbar-assist",
    response_model=StandardSuccessResponse[AIResultRecord],
    status_code=status.HTTP_200_OK,
    summary="AI SBAR wording assistance (REVIEW_REQUIRED)",
    description=(
        "Assists with wording structured SBAR clinical communications. "
        "AI generates draft language only. Clinical facts must be clinician-verified."
    ),
    operation_id="patient_ai_sbar_assist",
)
async def patient_ai_sbar_assist(
    http_request: Request,
    patient_id: Annotated[str, Path(description="Patient ID")],
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    ai_service: Annotated[AIService, Depends(get_ai_service)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    _: Annotated[None, Depends(require_permission(Permission.AI_EXECUTE))],
    body: Optional[Dict[str, Any]] = None,
) -> StandardSuccessResponse[AIResultRecord]:
    """Generate SBAR wording assistance (clinician verifies all clinical facts)."""
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action=Permission.AI_EXECUTE.value,
        resource_type="patient",
        consent_scope=None,
    )
    payload_ctx = body or {}
    source_content = payload_ctx.get("source_content") or f"Situation: {payload_ctx.get('situation', '')}. Assessment: {payload_ctx.get('assessment', '')}"
    create_req = AITaskCreateRequest(
        task_type=AITaskType.SBAR_ASSISTANCE,
        patient_id=patient_id,
        source_content=source_content,
        input_context=payload_ctx,
    )
    task = await ai_service.submit_task(request=create_req, user_context=current_user, source_content=source_content)
    result = await ai_service.execute_task(task.id, user_context=current_user)
    return StandardSuccessResponse(
        success=True,
        data=result,
        request_id=_req_id(http_request),
    )
