"""Consent management API endpoints.

All endpoints are protected and require authentication.
Authorization within each endpoint is enforced by ConsentService business rules:
  - Only the patient subject can create their own consent.
  - Only the patient subject can revoke their own consent.
  - Only the patient subject, grantee, or ADMIN can read a consent.

HTTP semantics:
  201 Created      — consent created
  200 OK           — read/revoke success
  401 Unauthorized — missing or invalid authentication
  403 Forbidden    — authenticated but not authorized for the operation
  404 Not Found    — consent not found (also used to prevent existence leakage)
  422              — validation error (invalid purpose, scope, expiry, etc.)
"""

from typing import Annotated
from fastapi import APIRouter, Depends, Request, status

from app.api.deps import (
    get_audit_service,
    get_consent_service,
    get_current_user,
)
from app.core.logging import request_id_ctx_var
from app.schemas.authorization import (
    ConsentCreateRequest,
    ConsentListResponse,
    ConsentResponse,
    ConsentRevokeRequest,
    ConsentStatus,
)
from app.schemas.response import StandardErrorResponse, StandardSuccessResponse
from app.schemas.user import AuthenticatedUserContext
from app.services.audit_service import AuditService
from app.services.consent_service import ConsentService

router = APIRouter(prefix="/consents", tags=["Consent"])


def _req_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request_id_ctx_var.get() or "unknown"


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardSuccessResponse[ConsentResponse],
    summary="Create consent grant",
    description=(
        "Creates a new consent grant from the authenticated patient to a specified recipient "
        "for a defined purpose and resource scope. Only PATIENT accounts may create consent. "
        "Purpose and scope must be from the supported sets. "
        "Consent cannot be granted to oneself."
    ),
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Only patients may create consent on their own behalf"},
        422: {"model": StandardErrorResponse, "description": "Invalid purpose, scope, or expiry"},
    },
)
async def create_consent(
    request: Request,
    body: ConsentCreateRequest,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    consent_service: Annotated[ConsentService, Depends(get_consent_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> StandardSuccessResponse[ConsentResponse]:
    """Create a new consent grant for the authenticated patient."""
    consent = await consent_service.create_consent(
        requester_id=current_user.user_id,
        requester_role=current_user.role.value,
        request=body,
    )
    await audit_service.record_consent_created(
        actor_id=current_user.user_id,
        consent_id=consent.id,
        patient_id=consent.patient_id,
        grantee_id=consent.grantee_id,
        purpose=consent.purpose,
        scope=consent.scope,
    )
    return StandardSuccessResponse(data=consent, request_id=_req_id(request))


@router.get(
    "",
    response_model=StandardSuccessResponse[ConsentListResponse],
    summary="List my consents",
    description=(
        "Returns all consent grants where the authenticated user is the patient subject. "
        "Optionally filter by status."
    ),
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
    },
)
async def list_my_consents(
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    consent_service: Annotated[ConsentService, Depends(get_consent_service)],
    status_filter: ConsentStatus | None = None,
) -> StandardSuccessResponse[ConsentListResponse]:
    """List all consents for the authenticated patient."""
    consents = await consent_service.list_my_consents(
        requester_id=current_user.user_id,
        status_filter=status_filter,
    )
    return StandardSuccessResponse(
        data=ConsentListResponse(items=consents, total=len(consents)),
        request_id=_req_id(request),
    )


@router.get(
    "/{consent_id}",
    response_model=StandardSuccessResponse[ConsentResponse],
    summary="Get consent by ID",
    description=(
        "Retrieves a specific consent by its ID. "
        "Accessible by the patient subject, the grantee, or an ADMIN. "
        "Returns 404 to avoid leaking consent existence to unauthorized callers."
    ),
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        404: {"model": StandardErrorResponse, "description": "Consent not found or access not permitted"},
    },
)
async def get_consent(
    request: Request,
    consent_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    consent_service: Annotated[ConsentService, Depends(get_consent_service)],
) -> StandardSuccessResponse[ConsentResponse]:
    """Retrieve a specific consent record."""
    consent = await consent_service.get_consent(
        requester_id=current_user.user_id,
        requester_role=current_user.role.value,
        consent_id=consent_id,
    )
    return StandardSuccessResponse(data=consent, request_id=_req_id(request))


@router.post(
    "/{consent_id}/revoke",
    response_model=StandardSuccessResponse[ConsentResponse],
    summary="Revoke consent",
    description=(
        "Revokes an existing consent grant. Only the patient subject may revoke their own consent. "
        "Revocation is effective immediately for all future authorization checks. "
        "Historical audit records are not deleted."
    ),
    responses={
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Only the patient subject may revoke this consent"},
        404: {"model": StandardErrorResponse, "description": "Consent not found"},
        422: {"model": StandardErrorResponse, "description": "Consent is already revoked"},
    },
)
async def revoke_consent(
    request: Request,
    consent_id: str,
    body: ConsentRevokeRequest,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    consent_service: Annotated[ConsentService, Depends(get_consent_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> StandardSuccessResponse[ConsentResponse]:
    """Revoke a specific consent grant."""
    consent = await consent_service.revoke_consent(
        requester_id=current_user.user_id,
        requester_role=current_user.role.value,
        consent_id=consent_id,
        reason=body.reason,
    )
    await audit_service.record_consent_revoked(
        actor_id=current_user.user_id,
        consent_id=consent_id,
        reason=body.reason,
    )
    return StandardSuccessResponse(data=consent, request_id=_req_id(request))
