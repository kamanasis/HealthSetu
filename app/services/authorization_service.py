"""Authorization service — centralized access control evaluation engine.

SECURITY PRINCIPLES
====================
- authenticated ≠ authorized
  A valid JWT only proves identity. Every protected resource still requires
  an explicit authorization check through this service.

- Deny by default
  Unknown policy state ALWAYS results in DENY.
  Never default to ALLOW when policy is ambiguous.

- Least privilege
  Roles receive only the permissions explicitly listed in ROLE_PERMISSIONS.
  ADMIN does NOT automatically have clinical data access.
  DOCTOR does NOT automatically have access to every patient.

- Purpose and scope limitation
  Consent for one purpose does not authorize another purpose.
  Consent for one scope does not authorize another scope.

AUTHORIZATION FLOW
==================
Request
  └─ Authentication (Phase 2) → AuthenticatedUserContext
       └─ Authorization (this service)
            ├─ 1. Permission check (role → permission)
            ├─ 2. Resource ownership check (patient self-access)
            ├─ 3. Relationship check (doctor–patient relationship)
            │     └─ DATABASE TEAM DEPENDENCY: provider_patient_relationship table
            └─ 4. Consent check (via ConsentService)
                   └─ ALLOW | DENY + audit event

DATABASE TEAM DEPENDENCIES
===========================
- provider_patient_relationship table: required for relationship-based access
  (doctor access to a specific patient's resources)
- role_permissions table: if dynamic permissions are needed beyond static policy
- audit_events table: for persisted audit trail (interim: structured log)
"""

from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.logging import get_logger
from app.core.policies import Permission, get_required_permission, role_has_permission
from app.repositories.permission_repository import PermissionRepository
from app.schemas.authorization import (
    AuthorizationContext,
    AuthorizationDecision,
    ConsentCheckResult,
    DenialReason,
)
from app.schemas.user import AuthenticatedUserContext
from app.services.audit_service import AuditService
from app.services.base import BaseService
from app.services.consent_service import ConsentService

logger = get_logger("app.authorization")


class AuthorizationService(BaseService[PermissionRepository]):
    """Centralized authorization engine for HealthSetu.

    Routes and dependencies call this service — authorization logic must
    NOT be duplicated inside route handlers.
    """

    def __init__(
        self,
        permission_repository: PermissionRepository,
        consent_service: ConsentService,
        audit_service: AuditService,
    ) -> None:
        super().__init__(repository=permission_repository)
        self.permission_repo = permission_repository
        self.consent_service = consent_service
        self.audit_service = audit_service

    # -----------------------------------------------------------------------
    # 1. Permission Check
    # -----------------------------------------------------------------------

    async def check_permission(
        self,
        user: AuthenticatedUserContext,
        permission: Permission,
    ) -> AuthorizationDecision:
        """Evaluate whether the user's role includes the required permission.

        This is a NECESSARY but not SUFFICIENT condition for resource access.
        Always combine with ownership/relationship checks for clinical resources.
        """
        has_it = await self.permission_repo.role_has_permission(user.role.value, permission)
        if has_it:
            return AuthorizationDecision.allow(permission_checked=permission.value)
        return AuthorizationDecision.deny(
            reason=DenialReason.NO_PERMISSION,
            permission_checked=permission.value,
        )

    # -----------------------------------------------------------------------
    # 2. Resource Ownership Check
    # -----------------------------------------------------------------------

    def check_resource_ownership(
        self,
        user: AuthenticatedUserContext,
        resource_owner_id: str,
    ) -> AuthorizationDecision:
        """Evaluate whether the user is the owner of the target resource.

        This enforces patient self-access: a patient may access their own
        resources; they may NOT access another patient's resources through
        this path.

        DOCTOR and ADMIN roles are not considered owners here.
        Relationship-based access for non-owners uses check_relationship().
        """
        if user.user_id == resource_owner_id:
            return AuthorizationDecision.allow()
        return AuthorizationDecision.deny(reason=DenialReason.NOT_RESOURCE_OWNER)

    # -----------------------------------------------------------------------
    # 3. Relationship Check
    # -----------------------------------------------------------------------

    async def check_relationship(
        self,
        requester_id: str,
        patient_id: str,
        context: AuthorizationContext | None = None,
    ) -> AuthorizationDecision:
        """Evaluate whether a valid provider–patient relationship exists.

        DATABASE TEAM DEPENDENCY
        ========================
        A provider_patient_relationship table is required for this check to
        return ALLOW for doctor access. Until delivered, this method always
        returns DENY for non-self access, preserving the deny-by-default rule.

        Required entity fields:
          id              : Primary Key (UUID)
          provider_id     : FOREIGN KEY → users.id (doctor)
          patient_id      : FOREIGN KEY → users.id (patient)
          relationship_type : VARCHAR ('treating', 'consulting', 'emergency', ...)
          is_active       : BOOLEAN
          established_at  : TIMESTAMP WITH TIME ZONE
          ended_at        : NULLABLE TIMESTAMP WITH TIME ZONE

        When the database team delivers this entity, replace the stub below
        with an actual repository call.
        """
        if requester_id == patient_id:
            # Self-access — always counts as a valid "relationship"
            return AuthorizationDecision.allow()

        # NOTE FOR DATABASE TEAM: replace this stub with real relationship lookup
        # relationship = await self.relationship_repo.get_active_relationship(
        #     provider_id=requester_id,
        #     patient_id=patient_id,
        # )
        # if relationship:
        #     return AuthorizationDecision.allow()

        logger.info(
            "Relationship check: no active relationship found (DB dependency pending)",
            extra={
                "requester_id": requester_id,
                "patient_id": patient_id,
                "event_type": "AUTHZ_RELATIONSHIP_FAILED",
            },
        )
        return AuthorizationDecision.deny(reason=DenialReason.NO_RELATIONSHIP)

    # -----------------------------------------------------------------------
    # 4. Consent Check (delegated to ConsentService)
    # -----------------------------------------------------------------------

    async def require_consent(
        self,
        patient_id: str,
        requester_id: str,
        purpose: str,
        scope: str,
    ) -> ConsentCheckResult:
        """Evaluate consent using the ConsentService.

        Returns a ConsentCheckResult — internal; do not forward to clients.
        """
        return await self.consent_service.check_consent(
            patient_id=patient_id,
            requester_id=requester_id,
            purpose=purpose,
            scope=scope,
        )

    # -----------------------------------------------------------------------
    # Full Authorization Evaluation
    # -----------------------------------------------------------------------

    async def authorize(
        self,
        user: AuthenticatedUserContext,
        action: str,
        context: AuthorizationContext,
        require_ownership: bool = False,
        require_relationship: bool = False,
        consent_purpose: str | None = None,
        consent_scope: str | None = None,
    ) -> AuthorizationDecision:
        """Full authorization evaluation pipeline.

        Steps executed in order:
          1. Resolve the required permission for the action.
          2. Check role → permission.
          3. If require_ownership=True: check resource ownership.
          4. If require_relationship=True: check provider–patient relationship.
          5. If consent_purpose + consent_scope provided: check consent.
          6. ALLOW if all passing checks satisfied, otherwise DENY.

        Audit events are emitted for both ALLOW and DENY outcomes.

        Args:
            user: Authenticated caller context (from get_current_user).
            action: Permission action string (e.g., "clinical_record:read").
            context: AuthorizationContext with resource and relationship details.
            require_ownership: If True, caller must own the resource.
            require_relationship: If True, a provider–patient relationship is required.
            consent_purpose: If set, consent is evaluated for this purpose.
            consent_scope: If set, consent is evaluated for this scope.

        Returns:
            AuthorizationDecision (ALLOW or DENY with internal reason code).

        Raises:
            ForbiddenException if access is denied (use this in route handlers).
        """
        resource_type = context.resource_type
        resource_id = context.resource_id

        # Step 1: Resolve required permission
        # Parse "resource_type:action" format first, then fall back to direct lookup
        permission: Permission | None = None
        parts = action.split(":", 1)
        if len(parts) == 2:
            permission = get_required_permission(parts[0], parts[1])
        # If not in map, try direct match as a Permission enum value
        if permission is None:
            try:
                permission = Permission(action)
            except ValueError:
                pass

        if permission is None:
            await self.audit_service.record_access_denied(
                actor_id=user.user_id,
                action=action,
                reason_code=DenialReason.UNKNOWN_POLICY.value,
                resource_type=resource_type,
                resource_id=resource_id,
            )
            return AuthorizationDecision.deny(reason=DenialReason.UNKNOWN_POLICY)

        # Step 2: Permission check
        perm_decision = await self.check_permission(user, permission)
        if not perm_decision.allowed:
            await self.audit_service.record_access_denied(
                actor_id=user.user_id,
                action=action,
                reason_code=DenialReason.NO_PERMISSION.value,
                resource_type=resource_type,
                resource_id=resource_id,
            )
            return perm_decision

        # Step 3: Resource ownership check (if required)
        if require_ownership and context.resource_owner_id:
            own_decision = self.check_resource_ownership(user, context.resource_owner_id)
            if not own_decision.allowed:
                await self.audit_service.record_access_denied(
                    actor_id=user.user_id,
                    action=action,
                    reason_code=DenialReason.NOT_RESOURCE_OWNER.value,
                    resource_type=resource_type,
                    resource_id=resource_id,
                )
                return own_decision

        # Step 4: Relationship check (if required)
        if require_relationship and context.resource_owner_id:
            rel_decision = await self.check_relationship(
                requester_id=user.user_id,
                patient_id=context.resource_owner_id,
                context=context,
            )
            if not rel_decision.allowed:
                await self.audit_service.record_access_denied(
                    actor_id=user.user_id,
                    action=action,
                    reason_code=DenialReason.NO_RELATIONSHIP.value,
                    resource_type=resource_type,
                    resource_id=resource_id,
                )
                return rel_decision

        # Step 5: Consent check (if purpose + scope are specified)
        if consent_purpose and consent_scope and context.resource_owner_id:
            patient_id = context.resource_owner_id
            consent_result = await self.require_consent(
                patient_id=patient_id,
                requester_id=user.user_id,
                purpose=consent_purpose,
                scope=consent_scope,
            )
            await self.audit_service.record_consent_check(
                actor_id=user.user_id,
                allowed=consent_result.allowed,
                purpose=consent_purpose,
                scope=consent_scope,
                consent_id=consent_result.consent_id,
                reason_code=consent_result.reason.value if consent_result.reason else None,
            )
            if not consent_result.allowed:
                denial_reason = consent_result.reason or DenialReason.CONSENT_NOT_FOUND
                await self.audit_service.record_access_denied(
                    actor_id=user.user_id,
                    action=action,
                    reason_code=denial_reason.value,
                    resource_type=resource_type,
                    resource_id=resource_id,
                )
                return AuthorizationDecision.deny(
                    reason=denial_reason,
                    permission_checked=permission.value,
                )

        # Step 6: All checks passed — ALLOW
        await self.audit_service.record_access_granted(
            actor_id=user.user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        return AuthorizationDecision.allow(permission_checked=permission.value)

    # -----------------------------------------------------------------------
    # Convenience: authorize or raise
    # -----------------------------------------------------------------------

    async def authorize_or_raise(
        self,
        user: AuthenticatedUserContext,
        action: str,
        context: AuthorizationContext,
        require_ownership: bool = False,
        require_relationship: bool = False,
        consent_purpose: str | None = None,
        consent_scope: str | None = None,
    ) -> AuthorizationDecision:
        """Evaluate authorization and raise ForbiddenException if denied.

        Use this in route handlers for clean, one-line authorization:

            await authz_service.authorize_or_raise(
                user=current_user,
                action="clinical_record:read",
                context=AuthorizationContext(
                    user_id=current_user.user_id,
                    role=current_user.role.value,
                    resource_owner_id=patient_id,
                ),
            )
        """
        decision = await self.authorize(
            user=user,
            action=action,
            context=context,
            require_ownership=require_ownership,
            require_relationship=require_relationship,
            consent_purpose=consent_purpose,
            consent_scope=consent_scope,
        )
        if not decision.allowed:
            # Do NOT expose the internal denial reason to the client
            raise ForbiddenException("Access denied.")
        return decision
