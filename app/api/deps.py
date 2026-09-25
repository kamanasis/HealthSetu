"""FastAPI dependency injection providers for authentication and services."""

from typing import Annotated
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import UnauthorizedException
from app.core.security import decode_access_token
from app.repositories.auth_session_repository import AuthSessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import AuthenticatedUserContext
from app.services.auth_service import AuthService

# HTTP Bearer scheme with OpenAPI integration
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Bearer access token in Authorization header (Format: Bearer <token>)",
)

# Global default repositories (in-memory fallbacks until DB team models are plugged in)
_global_user_repo = UserRepository()
_global_session_repo = AuthSessionRepository()


def get_user_repository() -> UserRepository:
    """Dependency provider for UserRepository."""
    return _global_user_repo


def get_auth_session_repository() -> AuthSessionRepository:
    """Dependency provider for AuthSessionRepository."""
    return _global_session_repo


def get_auth_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    session_repo: Annotated[AuthSessionRepository, Depends(get_auth_session_repository)],
) -> AuthService:
    """Dependency provider for AuthService."""
    return AuthService(user_repository=user_repo, session_repository=session_repo)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthenticatedUserContext:
    """Reusable authentication dependency verifying JWT bearer tokens and caller context.

    Future protected endpoints consume this dependency:
        current_user: AuthenticatedUserContext = Depends(get_current_user)
    """
    if credentials is None:
        raise UnauthorizedException("Authentication credentials were not provided.")

    if credentials.scheme.lower() != "bearer":
        raise UnauthorizedException("Invalid authentication scheme. 'Bearer' required.")

    token = credentials.credentials
    if not token or not token.strip():
        raise UnauthorizedException("Invalid token format.")

    # Validate and decode access token
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Token payload missing subject identifier.")

    # Retrieve user and verify account status is ACTIVE
    user_context = await auth_service.get_user_context(str(user_id))
    return user_context
