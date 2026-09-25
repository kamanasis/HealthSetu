"""Pydantic schemas for authorization context, decisions, and request/response models.

These schemas are the API-layer contract. They NEVER expose:
- Internal policy engine details
- Database credentials or raw models
- PHI (clinical information)
- Access tokens or secrets
"""

from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Authorization Decision
# ---------------------------------------------------------------------------

class AuthorizationOutcome(str, Enum):
    """Possible outcomes from an authorization evaluation."""

    ALLOW = "ALLOW"
    DENY = "DENY"


class DenialReason(str, Enum):
    """Internal denial reasons — NOT exposed verbatim to clients.

    These are used internally for audit logging and service-layer branching.
    Client-facing responses always use generic messages to avoid leaking
    policy details or resource existence.
    """

    NO_PERMISSION = "NO_PERMISSION"
    NOT_RESOURCE_OWNER = "NOT_RESOURCE_OWNER"
    NO_RELATIONSHIP = "NO_RELATIONSHIP"
    CONSENT_REQUIRED = "CONSENT_REQUIRED"
    CONSENT_NOT_FOUND = "CONSENT_NOT_FOUND"
    CONSENT_REVOKED = "CONSENT_REVOKED"
    CONSENT_EXPIRED = "CONSENT_EXPIRED"
    CONSENT_PURPOSE_MISMATCH = "CONSENT_PURPOSE_MISMATCH"
    CONSENT_SCOPE_MISMATCH = "CONSENT_SCOPE_MISMATCH"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    ACCOUNT_NOT_ALLOWED = "ACCOUNT_NOT_ALLOWED"
    UNKNOWN_POLICY = "UNKNOWN_POLICY"


class AuthorizationDecision(BaseModel):
    """Result of an authorization evaluation.

    The 'reason' field is INTERNAL and must not be forwarded to API clients.
    Use it for audit logging and service-layer branching only.
    """

    model_config = ConfigDict(frozen=True)

    outcome: AuthorizationOutcome
    reason: DenialReason | None = Field(
        default=None,
        description="Internal denial reason code — do not expose to clients",
    )
    permission_checked: str | None = Field(
        default=None,
        description="The permission identifier that was evaluated",
    )

    @property
    def allowed(self) -> bool:
        """True if the outcome is ALLOW."""
        return self.outcome == AuthorizationOutcome.ALLOW

    @classmethod
    def allow(cls, permission_checked: str | None = None) -> "AuthorizationDecision":
        """Convenience constructor for an ALLOW decision."""
        return cls(outcome=AuthorizationOutcome.ALLOW, permission_checked=permission_checked)

    @classmethod
    def deny(
        cls,
        reason: DenialReason,
        permission_checked: str | None = None,
    ) -> "AuthorizationDecision":
        """Convenience constructor for a DENY decision."""
        return cls(
            outcome=AuthorizationOutcome.DENY,
            reason=reason,
            permission_checked=permission_checked,
        )


# ---------------------------------------------------------------------------
# Authorization Context
# ---------------------------------------------------------------------------

class AuthorizationContext(BaseModel):
    """Full authorization context assembled for a single request evaluation.

    Carries only the minimum fields needed to evaluate the authorization
    decision. Never carries clinical record content or raw token values.
    """

    model_config = ConfigDict(frozen=True)

    # Authenticated caller
    user_id: str
    role: str

    # Optional resource context (populated by routes that know the target)
    resource_type: str | None = None
    resource_id: str | None = None
    resource_owner_id: str | None = None     # patient who owns the resource

    # Relationship context (populated when a doctor–patient check is needed)
    relationship_context: dict[str, Any] | None = None

    # Consent evaluation context
    consent_purpose: str | None = None
    consent_scope: str | None = None


# ---------------------------------------------------------------------------
# Consent Schemas
# ---------------------------------------------------------------------------

class ConsentStatus(str, Enum):
    """Consent lifecycle states.

    DATABASE TEAM DEPENDENCY:
    If the database team defines a different enum name or values, update
    this mapping to stay in sync. The backend policy layer must treat
    anything other than ACTIVE as non-consenting.
    """

    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"
    PENDING = "PENDING"
    DENIED = "DENIED"


class ConsentCreateRequest(BaseModel):
    """Request body for creating a new consent grant.

    The server validates and enforces the actual scope/purpose — clients
    cannot elevate their own permissions by submitting arbitrary values.
    """

    model_config = ConfigDict(extra="forbid")

    grantee_id: str = Field(
        ...,
        description="User ID of the consent recipient (e.g., a doctor's user ID)",
        examples=["usr-doctor-001"],
    )
    purpose: str = Field(
        ...,
        description="Consent purpose from the supported set (e.g., care_delivery)",
        examples=["care_delivery"],
    )
    scope: str = Field(
        ...,
        description="Resource scope covered by this consent (e.g., clinical_records)",
        examples=["clinical_records"],
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Optional explicit expiry timestamp. Must be in the future.",
    )
    notes: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional free-text notes from the patient. Not a clinical note.",
    )


class ConsentRevokeRequest(BaseModel):
    """Request body for revoking an existing consent."""

    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(
        default=None,
        max_length=500,
        description="Optional plain-text reason for revocation",
    )


class ConsentResponse(BaseModel):
    """Public consent representation — never exposes internal IDs or PHI."""

    id: str = Field(description="Consent unique identifier")
    patient_id: str = Field(description="Patient (subject) user ID")
    grantee_id: str = Field(description="Recipient (grantee) user ID")
    purpose: str = Field(description="Consent purpose")
    scope: str = Field(description="Consent resource scope")
    status: ConsentStatus = Field(description="Current consent lifecycle status")
    granted_at: datetime = Field(description="When consent was created")
    effective_from: datetime = Field(description="When consent becomes effective")
    expires_at: datetime | None = Field(default=None, description="Consent expiry timestamp")
    revoked_at: datetime | None = Field(default=None, description="Revocation timestamp if applicable")
    version: int = Field(default=1, description="Consent version")


class ConsentListResponse(BaseModel):
    """Paginated consent list."""

    items: list[ConsentResponse]
    total: int


# ---------------------------------------------------------------------------
# Consent Check Result (internal, not returned directly to clients)
# ---------------------------------------------------------------------------

class ConsentCheckResult(BaseModel):
    """Result of a consent check operation.

    INTERNAL — never serialize this directly into an HTTP response.
    Use AuthorizationDecision for API responses.
    """

    model_config = ConfigDict(frozen=True)

    allowed: bool
    consent_id: str | None = None
    reason: DenialReason | None = None

    @classmethod
    def permitted(cls, consent_id: str) -> "ConsentCheckResult":
        return cls(allowed=True, consent_id=consent_id)

    @classmethod
    def denied(cls, reason: DenialReason) -> "ConsentCheckResult":
        return cls(allowed=False, reason=reason)
