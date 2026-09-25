"""Consent service — consent lifecycle management business logic.

SEPARATION OF CONCERNS
=======================
Authentication  → "Who is the user?"        (Phase 2 AuthService)
Authorization   → "Is the action permitted?" (Phase 3 AuthorizationService)
Consent         → "Has consent been granted for this purpose/scope?" (here)

Consent is NOT a universal permission.

A patient granting consent for 'care_delivery' does NOT implicitly authorize:
- 'research' purposes
- unrelated providers
- unrelated resource scopes

Revoked consent is IMMEDIATELY rejected on the next check.
Expired consent is IMMEDIATELY rejected on the next check.

DATABASE TEAM DEPENDENCIES
===========================
All database persistence delegates to ConsentRepository.
See app/repositories/consent_repository.py for full schema contract.
"""

import uuid
from datetime import datetime, timezone

from app.core.exceptions import ForbiddenException, NotFoundException, ValidationException
from app.core.logging import get_logger
from app.core.policies import (
    ConsentPurpose,
    ConsentScope,
    is_valid_consent_purpose,
    is_valid_consent_scope,
)
from app.repositories.consent_repository import ConsentRecord, ConsentRepository
from app.schemas.authorization import (
    ConsentCheckResult,
    ConsentCreateRequest,
    ConsentResponse,
    ConsentStatus,
    DenialReason,
)
from app.services.base import BaseService

logger = get_logger("app.consent")


def _map_record_to_response(record: ConsentRecord) -> ConsentResponse:
    """Convert an internal ConsentRecord to the public ConsentResponse schema."""
    return ConsentResponse(
        id=record.id,
        patient_id=record.patient_id,
        grantee_id=record.grantee_id,
        purpose=record.purpose,
        scope=record.scope,
        status=record.status,
        granted_at=record.granted_at,
        effective_from=record.effective_from,
        expires_at=record.expires_at,
        revoked_at=record.revoked_at,
        version=record.version,
    )


class ConsentService(BaseService[ConsentRepository]):
    """Service managing consent creation, lookup, evaluation, and revocation."""

    def __init__(self, consent_repository: ConsentRepository) -> None:
        super().__init__(repository=consent_repository)
        self.consent_repo = consent_repository

    # -----------------------------------------------------------------------
    # Consent Creation
    # -----------------------------------------------------------------------

    async def create_consent(
        self,
        requester_id: str,
        requester_role: str,
        request: ConsentCreateRequest,
    ) -> ConsentResponse:
        """Create a new consent grant.

        Authorization rules enforced here:
        1. Only a PATIENT may grant consent on their own behalf.
           (Delegated consent is NOT implemented in Phase 3.)
        2. Purpose must be in the supported set.
        3. Scope must be in the supported set.
        4. Expiry, if provided, must be in the future.
        5. Grantee must not be the same user as the granting patient.
        """
        # Only patients grant consent on their own behalf in Phase 3
        if requester_role.upper() != "PATIENT":
            raise ForbiddenException(
                "Only a patient may create consent on their own behalf. "
                "Delegated consent is not supported in this version."
            )

        # Validate purpose
        if not is_valid_consent_purpose(request.purpose):
            valid = [p.value for p in ConsentPurpose]
            raise ValidationException(
                f"Unsupported consent purpose '{request.purpose}'. "
                f"Supported purposes: {valid}"
            )

        # Validate scope
        if not is_valid_consent_scope(request.scope):
            valid = [s.value for s in ConsentScope]
            raise ValidationException(
                f"Unsupported consent scope '{request.scope}'. "
                f"Supported scopes: {valid}"
            )

        # Prevent self-grant
        if request.grantee_id == requester_id:
            raise ValidationException("Cannot create consent with yourself as the grantee.")

        # Validate expiry if provided
        now = datetime.now(timezone.utc)
        if request.expires_at is not None and request.expires_at <= now:
            raise ValidationException("Consent expiry must be in the future.")

        consent_id = str(uuid.uuid4())
        record = ConsentRecord(
            id=consent_id,
            patient_id=requester_id,       # consent subject is always the authenticated patient
            grantee_id=request.grantee_id,
            purpose=request.purpose,
            scope=request.scope,
            status=ConsentStatus.ACTIVE,
            granted_at=now,
            effective_from=now,
            expires_at=request.expires_at,
            notes=request.notes,
            version=1,
        )

        created = await self.consent_repo.create_consent(record)
        logger.info(
            f"Consent created: id={consent_id}",
            extra={
                "event_type": "CONSENT_CREATED",
                "actor_id": requester_id,
                "consent_id": consent_id,
                "purpose": request.purpose,
                "scope": request.scope,
            },
        )
        return _map_record_to_response(created)

    # -----------------------------------------------------------------------
    # Consent Revocation
    # -----------------------------------------------------------------------

    async def revoke_consent(
        self,
        requester_id: str,
        requester_role: str,
        consent_id: str,
        reason: str | None = None,
    ) -> ConsentResponse:
        """Revoke an existing consent grant.

        Authorization rules enforced here:
        1. Only the patient subject of the consent may revoke it.
           (Admin override is NOT implemented in Phase 3 without explicit policy.)
        2. Already-revoked consent cannot be revoked again (idempotent error).
        3. Revocation is effective immediately for all future consent checks.
        4. Historical audit records are NOT deleted (compliance requirement).
        """
        record = await self.consent_repo.get_by_id(consent_id)

        if record is None:
            # Use 404 to avoid confirming whether a consent exists to unauthorized callers
            raise NotFoundException("Consent not found.")

        # Only the patient subject may revoke their own consent in Phase 3
        if record.patient_id != requester_id:
            raise ForbiddenException("You are not authorized to revoke this consent.")

        if record.status == ConsentStatus.REVOKED:
            raise ValidationException("Consent has already been revoked.")

        now = datetime.now(timezone.utc)
        updated = await self.consent_repo.update_consent_status(
            consent_id=consent_id,
            new_status=ConsentStatus.REVOKED,
            revoked_at=now,
            revoked_by=requester_id,
        )

        if updated is None:
            raise NotFoundException("Consent not found after revocation attempt.")

        logger.info(
            f"Consent revoked: id={consent_id}",
            extra={
                "event_type": "CONSENT_REVOKED",
                "actor_id": requester_id,
                "consent_id": consent_id,
            },
        )
        return _map_record_to_response(updated)

    # -----------------------------------------------------------------------
    # Consent Retrieval
    # -----------------------------------------------------------------------

    async def get_consent(
        self,
        requester_id: str,
        requester_role: str,
        consent_id: str,
    ) -> ConsentResponse:
        """Retrieve a single consent record.

        Access rules:
        - Patient can read their own consents (patient_id == requester_id).
        - Grantee can read consents where they are the grantee.
        - ADMIN with ADMIN_AUDIT_READ permission may read any consent.
          (Permission check is performed in the authorization service / dep layer.)
        """
        record = await self.consent_repo.get_by_id(consent_id)

        if record is None:
            raise NotFoundException("Consent not found.")

        is_subject = record.patient_id == requester_id
        is_grantee = record.grantee_id == requester_id
        is_admin = requester_role.upper() == "ADMIN"

        if not (is_subject or is_grantee or is_admin):
            # Generic 404 to avoid leaking whether the consent exists
            raise NotFoundException("Consent not found.")

        return _map_record_to_response(record)

    async def list_my_consents(
        self,
        requester_id: str,
        status_filter: ConsentStatus | None = None,
    ) -> list[ConsentResponse]:
        """List all consents where the requester is the patient subject."""
        records = await self.consent_repo.list_by_patient(
            patient_id=requester_id,
            status_filter=status_filter,
        )
        return [_map_record_to_response(r) for r in records]

    # -----------------------------------------------------------------------
    # Consent Check (used by AuthorizationService)
    # -----------------------------------------------------------------------

    async def check_consent(
        self,
        patient_id: str,
        requester_id: str,
        purpose: str,
        scope: str,
    ) -> ConsentCheckResult:
        """Evaluate whether valid, active, in-scope consent exists.

        Returns ConsentCheckResult — INTERNAL, not sent directly to clients.

        Evaluation rules (all must pass):
        1. A consent record matching (patient, grantee, purpose, scope) must exist.
        2. Status must be ACTIVE.
        3. effective_from must be ≤ now.
        4. expires_at must be None or > now.
        5. Revoked consent ALWAYS fails regardless of other fields.

        Purpose limitation: a consent for 'care_delivery' does NOT satisfy
        a check for 'research'. Purposes must match exactly.

        Scope limitation: a consent for 'clinical_records' does NOT satisfy
        a check for 'prescriptions'. Scopes must match exactly.
        """
        record = await self.consent_repo.get_active_consent(
            patient_id=patient_id,
            grantee_id=requester_id,
            purpose=purpose,
            scope=scope,
        )

        if record is None:
            # Could be: not found, wrong purpose, wrong scope, revoked, expired
            # We do not distinguish externally — all map to CONSENT_NOT_FOUND
            # for the caller. Internal reason is set for audit.
            return ConsentCheckResult.denied(DenialReason.CONSENT_NOT_FOUND)

        # Final status double-check (the repository query already filters, but be explicit)
        if record.status == ConsentStatus.REVOKED:
            return ConsentCheckResult.denied(DenialReason.CONSENT_REVOKED)

        if record.status == ConsentStatus.EXPIRED:
            return ConsentCheckResult.denied(DenialReason.CONSENT_EXPIRED)

        if not record.is_active:
            return ConsentCheckResult.denied(DenialReason.CONSENT_EXPIRED)

        return ConsentCheckResult.permitted(consent_id=record.id)
