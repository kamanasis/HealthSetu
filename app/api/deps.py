"""FastAPI dependency injection providers for authentication, authorization, and services."""

from typing import Annotated
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.policies import Permission
from app.core.security import decode_access_token
from app.repositories.audit_repository import AuditRepository
from app.repositories.auth_session_repository import AuthSessionRepository
from app.repositories.consent_repository import ConsentRepository
from app.repositories.permission_repository import PermissionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.authorization import AuthorizationContext
from app.schemas.user import AuthenticatedUserContext
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.authorization_service import AuthorizationService
from app.services.consent_service import ConsentService

# ---------------------------------------------------------------------------
# HTTP Bearer scheme
# ---------------------------------------------------------------------------
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Bearer access token in Authorization header (Format: Bearer <token>)",
)

# ---------------------------------------------------------------------------
# Global default repositories (in-memory fallbacks until DB team delivers schema)
# ---------------------------------------------------------------------------
_global_user_repo = UserRepository()
_global_session_repo = AuthSessionRepository()
_global_consent_repo = ConsentRepository()
_global_audit_repo = AuditRepository()
_global_permission_repo = PermissionRepository()


# ---------------------------------------------------------------------------
# Phase 1/2: Repository providers
# ---------------------------------------------------------------------------

def get_user_repository() -> UserRepository:
    """Dependency provider for UserRepository."""
    return _global_user_repo


def get_auth_session_repository() -> AuthSessionRepository:
    """Dependency provider for AuthSessionRepository."""
    return _global_session_repo


# ---------------------------------------------------------------------------
# Phase 3: Repository providers
# ---------------------------------------------------------------------------

def get_consent_repository() -> ConsentRepository:
    """Dependency provider for ConsentRepository."""
    return _global_consent_repo


def get_audit_repository() -> AuditRepository:
    """Dependency provider for AuditRepository."""
    return _global_audit_repo


def get_permission_repository() -> PermissionRepository:
    """Dependency provider for PermissionRepository."""
    return _global_permission_repo


# ---------------------------------------------------------------------------
# Phase 1/2: Service providers
# ---------------------------------------------------------------------------

def get_auth_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    session_repo: Annotated[AuthSessionRepository, Depends(get_auth_session_repository)],
) -> AuthService:
    """Dependency provider for AuthService."""
    return AuthService(user_repository=user_repo, session_repository=session_repo)


# ---------------------------------------------------------------------------
# Phase 3: Service providers
# ---------------------------------------------------------------------------

def get_audit_service(
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
) -> AuditService:
    """Dependency provider for AuditService."""
    return AuditService(audit_repository=audit_repo)


def get_consent_service(
    consent_repo: Annotated[ConsentRepository, Depends(get_consent_repository)],
) -> ConsentService:
    """Dependency provider for ConsentService."""
    return ConsentService(consent_repository=consent_repo)


def get_authorization_service(
    permission_repo: Annotated[PermissionRepository, Depends(get_permission_repository)],
    consent_service: Annotated[ConsentService, Depends(get_consent_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> AuthorizationService:
    """Dependency provider for AuthorizationService."""
    return AuthorizationService(
        permission_repository=permission_repo,
        consent_service=consent_service,
        audit_service=audit_service,
    )


# ---------------------------------------------------------------------------
# Phase 2: Authentication dependency
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthenticatedUserContext:
    """Reusable authentication dependency verifying JWT bearer tokens and caller context.

    Protected endpoints consume this dependency:
        current_user: AuthenticatedUserContext = Depends(get_current_user)
    """
    if credentials is None:
        raise UnauthorizedException("Authentication credentials were not provided.")

    if credentials.scheme.lower() != "bearer":
        raise UnauthorizedException("Invalid authentication scheme. 'Bearer' required.")

    token = credentials.credentials
    if not token or not token.strip():
        raise UnauthorizedException("Invalid token format.")

    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Token payload missing subject identifier.")

    user_context = await auth_service.get_user_context(str(user_id))
    return user_context


# ---------------------------------------------------------------------------
# Phase 3: Authorization dependencies
# ---------------------------------------------------------------------------

def require_permission(permission: Permission):
    """FastAPI dependency factory: require authenticated user to have a specific permission.

    Usage:
        @router.get("/resource")
        async def endpoint(
            _: None = Depends(require_permission(Permission.CLINICAL_RECORD_READ)),
            current_user: AuthenticatedUserContext = Depends(get_current_user),
        ):
            ...

    Note: This checks role → permission only. Ownership and consent are
    evaluated via require_resource_access() or AuthorizationService.authorize().
    """
    async def _dependency(
        current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
        authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    ) -> AuthenticatedUserContext:
        decision = await authz_service.check_permission(current_user, permission)
        if not decision.allowed:
            raise ForbiddenException("You do not have permission to perform this action.")
        return current_user

    return _dependency


def require_role(*roles: str):
    """FastAPI dependency factory: require authenticated user to have one of the given roles.

    Use sparingly. Prefer require_permission() for most authorization decisions.
    Use require_role() only when role-level gating is explicitly required by policy
    (e.g., only an ADMIN may invoke a specific management endpoint).

    Usage:
        @router.get("/admin/users")
        async def list_users(
            current_user: AuthenticatedUserContext = Depends(require_role("ADMIN")),
        ):
            ...
    """
    async def _dependency(
        current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    ) -> AuthenticatedUserContext:
        if current_user.role.value not in {r.upper() for r in roles}:
            raise ForbiddenException("Your role does not permit this action.")
        return current_user

    return _dependency


def require_resource_access(
    action: str,
    resource_type: str | None = None,
    require_ownership: bool = False,
    require_relationship: bool = False,
    consent_purpose: str | None = None,
    consent_scope: str | None = None,
):
    """FastAPI dependency factory: full authorization evaluation for resource access.

    Evaluates the complete authorization pipeline:
      1. Authentication (get_current_user)
      2. Permission check (role → permission for action)
      3. Ownership check (if require_ownership=True)
      4. Relationship check (if require_relationship=True)
      5. Consent check (if consent_purpose + consent_scope provided)

    Resource-specific IDs (resource_id, resource_owner_id) must be passed
    at the route level because they are path parameters, not injectable at
    dependency creation time.

    Example — patient accesses their own profile (no consent required):
        Depends(require_resource_access("patient:read_self", require_ownership=True))

    Example — doctor reads a patient clinical record (needs relationship + consent):
        Depends(require_resource_access(
            "clinical_record:read",
            resource_type="clinical_record",
            require_relationship=True,
            consent_purpose="care_delivery",
            consent_scope="clinical_records",
        ))

    The returned dependency provides the AuthorizationContext so routes can
    pass resource-specific IDs to the service directly for more control.
    """
    async def _dependency(
        current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
        authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    ) -> AuthenticatedUserContext:
        # Build a base context — routes that need owner/resource IDs should
        # call authz_service.authorize_or_raise() directly for full control.
        context = AuthorizationContext(
            user_id=current_user.user_id,
            role=current_user.role.value,
            resource_type=resource_type,
        )
        await authz_service.authorize_or_raise(
            user=current_user,
            action=action,
            context=context,
            require_ownership=require_ownership,
            require_relationship=require_relationship,
            consent_purpose=consent_purpose,
            consent_scope=consent_scope,
        )
        return current_user

    return _dependency
