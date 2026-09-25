"""Audit event service — structured security/access event recording.

This service is the single entry point for recording audit events.
It enforces the PHI-exclusion policy before handing off to the repository.

SEPARATION OF CONCERNS
=======================
Application logging   → operational, debugging (app/core/logging.py)
Audit events          → accountability, access decisions, consent lifecycle (here)

These MUST remain separate. Application log rotation or level changes
must NOT affect the audit trail.
"""

from app.core.logging import get_logger, request_id_ctx_var
from app.repositories.audit_repository import AuditRepository
from app.schemas.audit import AuditEventRecord, AuditEventType
from app.services.base import BaseService

logger = get_logger("app.audit_service")

# Fields that must NEVER appear in audit event metadata
_FORBIDDEN_METADATA_KEYS: frozenset[str] = frozenset({
    "password", "token", "access_token", "refresh_token", "secret",
    "api_key", "authorization", "cookie",
    # Clinical PHI safeguards
    "diagnosis", "diagnoses", "prescription", "prescriptions",
    "medication", "medications", "history", "medical_history",
    "clinical_notes", "document_content", "patient_data", "symptoms",
})


def _sanitize_metadata(metadata: dict | None) -> dict | None:
    """Remove forbidden keys from audit event metadata before persisting."""
    if not metadata:
        return metadata
    return {k: v for k, v in metadata.items() if k.lower() not in _FORBIDDEN_METADATA_KEYS}


class AuditService(BaseService[AuditRepository]):
    """Service for recording immutable security and access audit events."""

    def __init__(self, audit_repository: AuditRepository) -> None:
        super().__init__(repository=audit_repository)
        self.audit_repo = audit_repository

    async def record(
        self,
        event_type: AuditEventType,
        outcome: str,
        actor_id: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        reason_code: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Record an audit event.

        PHI exclusion is enforced on metadata before persistence.
        Tokens and secrets are NEVER valid metadata fields.
        """
        clean_metadata = _sanitize_metadata(metadata)
        event = AuditEventRecord(
            event_type=event_type,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            reason_code=reason_code,
            request_id=request_id_ctx_var.get(),
            metadata=clean_metadata,
        )
        await self.audit_repo.append(event)

    async def record_access_granted(
        self,
        actor_id: str,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Record a successful authorization grant."""
        await self.record(
            event_type=AuditEventType.AUTHZ_ACCESS_GRANTED,
            outcome="ALLOW",
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata,
        )

    async def record_access_denied(
        self,
        actor_id: str | None,
        action: str,
        reason_code: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Record an authorization denial."""
        await self.record(
            event_type=AuditEventType.AUTHZ_ACCESS_DENIED,
            outcome="DENY",
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            reason_code=reason_code,
            metadata=metadata,
        )

    async def record_consent_created(
        self,
        actor_id: str,
        consent_id: str,
        patient_id: str,
        grantee_id: str,
        purpose: str,
        scope: str,
    ) -> None:
        """Record a consent creation event."""
        await self.record(
            event_type=AuditEventType.CONSENT_CREATED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="consent:create",
            resource_type="consent",
            resource_id=consent_id,
            metadata={
                "patient_id": patient_id,
                "grantee_id": grantee_id,
                "purpose": purpose,
                "scope": scope,
            },
        )

    async def record_consent_revoked(
        self,
        actor_id: str,
        consent_id: str,
        reason: str | None = None,
    ) -> None:
        """Record a consent revocation event."""
        await self.record(
            event_type=AuditEventType.CONSENT_REVOKED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="consent:revoke",
            resource_type="consent",
            resource_id=consent_id,
            metadata={"reason": reason} if reason else None,
        )

    async def record_consent_check(
        self,
        actor_id: str,
        allowed: bool,
        purpose: str,
        scope: str,
        consent_id: str | None = None,
        reason_code: str | None = None,
    ) -> None:
        """Record the result of a consent check."""
        await self.record(
            event_type=(
                AuditEventType.CONSENT_CHECK_PASSED
                if allowed
                else AuditEventType.CONSENT_CHECK_FAILED
            ),
            outcome="ALLOW" if allowed else "DENY",
            actor_id=actor_id,
            action="consent:check",
            resource_type="consent",
            resource_id=consent_id,
            reason_code=reason_code,
            metadata={"purpose": purpose, "scope": scope},
        )
