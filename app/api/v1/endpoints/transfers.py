"""Patient Transfer and Referral API Endpoints (Phase 12).

Provides routes for explicit patient transfers, status tracking,
and authorized clinical context sharing.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import (
    get_authorization_service,
    get_current_user,
    get_patient_service,
    get_transfer_service,
    require_permission,
    verify_patient_access,
)
from app.core.exceptions import TransferAccessDeniedException
from app.core.logging import request_id_ctx_var
from app.core.policies import Permission
from app.schemas.response import StandardSuccessResponse
from app.schemas.transfer import (
    TransferCreateRequest,
    TransferListResponse,
    TransferResponse,
    TransferStatus,
    TransferStatusUpdateRequest,
)
from app.schemas.user import AuthenticatedUserContext
from app.services.authorization_service import AuthorizationService
from app.services.patient_service import PatientService
from app.services.transfer_service import TransferService

router = APIRouter(prefix="/patients/{patient_id}/transfers", tags=["Patient Transfers & Referrals"])


def _req_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request_id_ctx_var.get() or "unknown"


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardSuccessResponse[TransferResponse],
    summary="Create a patient transfer or referral request",
    description="Explicitly create a transfer request to a receiving facility with optional authorized clinical context.",
)
async def create_transfer(
    request: Request,
    patient_id: str,
    payload: TransferCreateRequest,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    transfer_service: Annotated[TransferService, Depends(get_transfer_service)],
) -> StandardSuccessResponse[TransferResponse]:
    # 1. Authorize caller access to patient
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="transfer:create",
        resource_type="transfer",
        consent_scope=None,  # TransferService explicitly validates transfer consent and raises TRANSFER_CONSENT_REQUIRED
    )

    # 2. Create transfer
    transfer = await transfer_service.create_transfer(
        patient_id=patient_id,
        request_data=payload,
        user_context=current_user,
    )

    return StandardSuccessResponse(data=transfer, request_id=_req_id(request))


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[TransferListResponse],
    summary="List patient transfer history",
    description="Return all authorized transfers and referrals for the specified patient.",
)
async def list_transfers(
    request: Request,
    patient_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    transfer_service: Annotated[TransferService, Depends(get_transfer_service)],
    limit: Annotated[int, Query(ge=1, le=100, description="Page limit")] = 50,
    offset: Annotated[int, Query(ge=0, description="Page offset")] = 0,
    status: Annotated[TransferStatus | None, Query(description="Filter by transfer status")] = None,
) -> StandardSuccessResponse[TransferListResponse]:
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="transfer:read",
        resource_type="transfer",
        consent_scope="transfer",
    )

    items, total = await transfer_service.list_patient_transfers(
        patient_id=patient_id,
        user_context=current_user,
        limit=limit,
        offset=offset,
        status=status,
    )

    return StandardSuccessResponse(
        data=TransferListResponse(items=items, total=total),
        request_id=_req_id(request),
    )


@router.get(
    "/{transfer_id}",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[TransferResponse],
    summary="Get patient transfer details",
    description="Retrieve a specific transfer or referral record.",
)
async def get_transfer(
    request: Request,
    patient_id: str,
    transfer_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    transfer_service: Annotated[TransferService, Depends(get_transfer_service)],
) -> StandardSuccessResponse[TransferResponse]:
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="transfer:read",
        resource_type="transfer",
        resource_id=transfer_id,
        consent_scope="transfer",
    )

    transfer = await transfer_service.get_transfer(
        transfer_id=transfer_id,
        user_context=current_user,
    )

    # Verify patient ownership of transfer record
    if transfer.patient_id != patient_id:
        raise TransferAccessDeniedException("Transfer does not belong to the specified patient.")

    return StandardSuccessResponse(data=transfer, request_id=_req_id(request))


@router.post(
    "/{transfer_id}/status",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[TransferResponse],
    summary="Update transfer status",
    description="Advance transfer through state machine according to valid state transitions and authorization.",
)
async def update_transfer_status(
    request: Request,
    patient_id: str,
    transfer_id: str,
    payload: TransferStatusUpdateRequest,
    current_user: Annotated[AuthenticatedUserContext, Depends(require_permission(Permission.TRANSFER_UPDATE_STATUS))],
    transfer_service: Annotated[TransferService, Depends(get_transfer_service)],
) -> StandardSuccessResponse[TransferResponse]:
    # Clinician status update (e.g. ACCEPT, DECLINE, PROGRESS, COMPLETE, CANCEL)
    updated = await transfer_service.update_transfer_status(
        transfer_id=transfer_id,
        update_data=payload,
        user_context=current_user,
    )

    if updated.patient_id != patient_id:
        raise TransferAccessDeniedException("Transfer does not belong to the specified patient.")

    return StandardSuccessResponse(data=updated, request_id=_req_id(request))
