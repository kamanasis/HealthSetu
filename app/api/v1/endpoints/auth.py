"""Authentication API endpoints for HealthSetu Phase 2."""

from datetime import datetime, timezone
import random
from typing import Annotated
from fastapi import APIRouter, Depends, Request, status

from app.api.deps import get_auth_service, get_current_user
from app.core.logging import request_id_ctx_var
from app.core.security import hash_password
from app.repositories.user_repository import UserRecord
from app.schemas.auth import (
    AccountStatus,
    LoginRequest,
    LogoutRequest,
    LogoutResponseData,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponseData,
)
from app.schemas.response import StandardErrorResponse, StandardSuccessResponse
from app.schemas.user import AuthenticatedUserContext, UserIdentityResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])


def _extract_request_id(request: Request) -> str:
    """Extract request correlation ID from request state or context variable."""
    return getattr(request.state, "request_id", None) or request_id_ctx_var.get() or "unknown"


@router.post(
    "/login",
    response_model=StandardSuccessResponse[TokenResponseData],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": StandardErrorResponse,
            "description": "Invalid credentials or account inactive",
        },
        422: {
            "model": StandardErrorResponse,
            "description": "Request validation failed",
        },
    },
    summary="Authenticate with credentials",
    description=(
        "Authenticates a user using their identifier (email/username/phone) and password. "
        "Returns a short-lived access token and a rotatable refresh token."
    ),
)
async def login(
    request: Request,
    payload: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> StandardSuccessResponse[TokenResponseData]:
    """Verify credentials and issue access and refresh tokens."""
    token_data = await auth_service.authenticate(
        identifier=payload.identifier,
        password=payload.password,
    )
    req_id = _extract_request_id(request)
    return StandardSuccessResponse(data=token_data, request_id=req_id)


@router.post(
    "/register",
    response_model=StandardSuccessResponse[TokenResponseData],
    status_code=status.HTTP_201_CREATED,
    summary="Register user profile and mint unique HealthSetu ID",
    description="Registers a new Patient, Doctor, or Hospital Org identity, issuing a sovereign HealthSetu unique ID and session tokens.",
)
async def register(
    request: Request,
    payload: RegisterRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> StandardSuccessResponse[TokenResponseData]:
    """Register identity, store in repository with unique ID, and return active tokens."""
    prefix_map = {
        "PATIENT": "HS-PAT",
        "DOCTOR": "HS-DOC",
        "ADMIN": "HS-HOSP",
    }
    role_key = payload.role.value if hasattr(payload.role, "value") else str(payload.role)
    unique_id = payload.unique_id or f"{prefix_map.get(role_key, 'HS-ID')}-{random.randint(1000, 9999)}"

    # Create user record
    user_record = UserRecord(
        id=unique_id,
        identifier=payload.identifier,
        password_hash=hash_password(payload.password),
        role=payload.role,
        status=AccountStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    auth_service.user_repo.register_in_memory_user(user_record)
    # Also register the unique ID as a valid login alias
    auth_service.user_repo._local_users[unique_id.lower()] = user_record

    # Authenticate and issue token
    token_data = await auth_service.authenticate(
        identifier=payload.identifier,
        password=payload.password,
    )
    req_id = _extract_request_id(request)
    return StandardSuccessResponse(data=token_data, request_id=req_id)



@router.post(
    "/refresh",
    response_model=StandardSuccessResponse[TokenResponseData],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": StandardErrorResponse,
            "description": "Invalid, expired, or revoked refresh token",
        },
        422: {
            "model": StandardErrorResponse,
            "description": "Request validation failed",
        },
    },
    summary="Refresh access token",
    description=(
        "Validates the refresh token, executes token rotation, and issues a new access token "
        "and replacement refresh token."
    ),
)
async def refresh_token(
    request: Request,
    payload: RefreshTokenRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> StandardSuccessResponse[TokenResponseData]:
    """Rotate refresh token and issue new access token."""
    token_data = await auth_service.refresh_tokens(payload.refresh_token)
    req_id = _extract_request_id(request)
    return StandardSuccessResponse(data=token_data, request_id=req_id)


@router.post(
    "/logout",
    response_model=StandardSuccessResponse[LogoutResponseData],
    status_code=status.HTTP_200_OK,
    summary="Terminate session / logout",
    description="Revokes the specified refresh token session. Operation is idempotent.",
)
async def logout(
    request: Request,
    payload: LogoutRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> StandardSuccessResponse[LogoutResponseData]:
    """Terminate the authenticated session and invalidate refresh token."""
    logout_data = await auth_service.logout(refresh_token=payload.refresh_token)
    req_id = _extract_request_id(request)
    return StandardSuccessResponse(data=logout_data, request_id=req_id)


@router.get(
    "/me",
    response_model=StandardSuccessResponse[UserIdentityResponse],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": StandardErrorResponse,
            "description": "Missing, invalid, or expired Bearer token",
        },
    },
    summary="Get current user identity",
    description="Returns the authenticated caller's identity, role, and operational account status.",
)
async def get_me(
    request: Request,
    current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
) -> StandardSuccessResponse[UserIdentityResponse]:
    """Return identity summary for the authenticated user."""
    identity = UserIdentityResponse(
        id=current_user.user_id,
        role=current_user.role,
        status=current_user.account_status,
    )
    req_id = _extract_request_id(request)
    return StandardSuccessResponse(data=identity, request_id=req_id)
