"""Authentication and token lifecycle service."""

from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedException
from app.core.logging import get_logger, request_id_ctx_var
from app.core.security import (
    create_access_token,
    generate_secure_token,
    hash_token,
    verify_password,
)
from app.repositories.auth_session_repository import AuthSessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    AccountStatus,
    LogoutResponseData,
    TokenResponseData,
    UserIdentitySummary,
)
from app.schemas.user import AuthenticatedUserContext
from app.services.base import BaseService

logger = get_logger("app.auth")

# A dummy Argon2id hash used to mitigate timing attacks when a user identifier does not exist
DUMMY_ARGON2ID_HASH = (
    "$argon2id$v=19$m=65536,t=2,p=1$ZHVtbXlzYWx0MTIzNDU2Nw$qO8V4qKjO9XbH9l5YV0p7a3Zf4g5H6j7K8l9M0n1O2A"
)


class AuthService(BaseService[UserRepository]):
    """Service orchestrating credential verification, token issuance, rotation, and logout."""

    def __init__(
        self,
        user_repository: UserRepository,
        session_repository: AuthSessionRepository,
    ) -> None:
        super().__init__(repository=user_repository)
        self.user_repo = user_repository
        self.session_repo = session_repository

    def _log_security_event(
        self,
        event_type: str,
        outcome: str,
        user_id: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Log privacy-conscious security event with correlation ID and metadata.

        CRITICAL: Tokens and passwords MUST NOT be passed to this method.
        """
        payload = {
            "event_type": event_type,
            "outcome": outcome,
            "request_id": request_id_ctx_var.get(),
        }
        if user_id:
            payload["user_id"] = user_id
        if extra:
            payload.update(extra)

        logger.info(
            f"Security Event: {event_type} - Outcome: {outcome}",
            extra=payload,
        )

    async def authenticate(self, identifier: str, password: str) -> TokenResponseData:
        """Authenticate user by identifier and password.

        Employs constant-time dummy verification and generic error responses
        to prevent timing attacks and account enumeration.
        """
        settings = get_settings()
        user = await self.user_repo.get_by_identifier(identifier)

        if user is None:
            # Timing attack mitigation: verify dummy hash
            verify_password(password, DUMMY_ARGON2ID_HASH)
            self._log_security_event("AUTH_LOGIN_FAILURE", "rejected_unknown_identifier")
            raise UnauthorizedException("Invalid credentials.")

        if not verify_password(password, user.password_hash):
            self._log_security_event(
                "AUTH_LOGIN_FAILURE", "rejected_invalid_password", user_id=user.id
            )
            raise UnauthorizedException("Invalid credentials.")

        # Account status check
        if user.status != AccountStatus.ACTIVE:
            self._log_security_event(
                "AUTH_ACCOUNT_BLOCKED",
                f"rejected_{user.status.value.lower()}",
                user_id=user.id,
            )
            # Return generic error to prevent account status enumeration
            raise UnauthorizedException("Invalid credentials.")

        # Issue tokens
        access_token, expires_in = create_access_token(user.id, user.role.value)
        raw_refresh = generate_secure_token(32)
        refresh_hash = hash_token(raw_refresh)
        refresh_expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        await self.session_repo.create_session(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=refresh_expires_at,
        )

        self._log_security_event("AUTH_LOGIN_SUCCESS", "success", user_id=user.id)

        return TokenResponseData(
            access_token=access_token,
            refresh_token=raw_refresh,
            token_type="bearer",
            expires_in=expires_in,
            user=UserIdentitySummary(
                id=user.id,
                role=user.role,
            ),
        )

    async def refresh_tokens(self, refresh_token: str) -> TokenResponseData:
        """Validate refresh token and perform token rotation.

        Detects token reuse and revokes all user sessions if a compromised token is reused.
        """
        settings = get_settings()
        token_hash = hash_token(refresh_token)
        session = await self.session_repo.get_session_by_token_hash(token_hash)

        if session is None:
            self._log_security_event("AUTH_REFRESH_FAILURE", "session_not_found")
            raise UnauthorizedException("Invalid or expired refresh token.")

        # Token Reuse Detection (Compromised token scenario)
        if session.is_revoked:
            self._log_security_event(
                "AUTH_REFRESH_REUSE_DETECTED",
                "revoked_token_reused_all_sessions_terminated",
                user_id=session.user_id,
            )
            # Revoke all sessions for this user to halt potential account takeover
            await self.session_repo.revoke_all_user_sessions(session.user_id)
            raise UnauthorizedException("Invalid or expired refresh token.")

        # Expiry check
        if session.is_expired:
            self._log_security_event(
                "AUTH_REFRESH_FAILURE", "token_expired", user_id=session.user_id
            )
            raise UnauthorizedException("Invalid or expired refresh token.")

        # Retrieve user and verify account remains active
        user = await self.user_repo.get_by_id(session.user_id)
        if user is None or user.status != AccountStatus.ACTIVE:
            self._log_security_event(
                "AUTH_ACCOUNT_BLOCKED",
                "account_inactive_during_refresh",
                user_id=session.user_id,
            )
            raise UnauthorizedException("Account is not active.")

        # Issue new access token & rotate refresh token
        new_access_token, expires_in = create_access_token(user.id, user.role.value)
        new_raw_refresh = generate_secure_token(32)
        new_refresh_hash = hash_token(new_raw_refresh)
        new_expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        await self.session_repo.rotate_session(
            old_session_id=session.id,
            user_id=user.id,
            new_token_hash=new_refresh_hash,
            new_expires_at=new_expires_at,
        )

        self._log_security_event("AUTH_REFRESH_SUCCESS", "rotated_success", user_id=user.id)

        return TokenResponseData(
            access_token=new_access_token,
            refresh_token=new_raw_refresh,
            token_type="bearer",
            expires_in=expires_in,
            user=UserIdentitySummary(
                id=user.id,
                role=user.role,
            ),
        )

    async def logout(self, refresh_token: str | None = None) -> LogoutResponseData:
        """Idempotent logout and session revocation."""
        if refresh_token:
            token_hash = hash_token(refresh_token)
            session = await self.session_repo.get_session_by_token_hash(token_hash)
            if session:
                await self.session_repo.revoke_session(session.id)
                self._log_security_event("AUTH_LOGOUT", "session_revoked", user_id=session.user_id)
            else:
                self._log_security_event("AUTH_LOGOUT", "session_not_found_idempotent")
        else:
            self._log_security_event("AUTH_LOGOUT", "no_token_supplied_idempotent")

        return LogoutResponseData(message="Logged out successfully.")

    async def get_user_context(self, user_id: str) -> AuthenticatedUserContext:
        """Build and validate authenticated caller context for protected endpoints."""
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise UnauthorizedException("User not found.")

        if user.status != AccountStatus.ACTIVE:
            raise UnauthorizedException(f"Account is {user.status.value.lower()}.")

        return AuthenticatedUserContext(
            user_id=user.id,
            role=user.role,
            account_status=user.status,
        )
