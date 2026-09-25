"""Pydantic schemas for audit events.

Audit events are separate from application logs.
They record security/access decisions and consent lifecycle events.

CRITICAL — Audit events must NEVER contain:
- Clinical record content
- Diagnosis, symptoms, prescriptions
- Medication lists or medical history
- Passwords, tokens, or secrets
- PHI beyond minimum subject/actor identifiers
"""

from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class AuditEventType(str, Enum):
    """Supported audit event type identifiers."""

    # Authorization events
    AUTHZ_ACCESS_GRANTED = "AUTHZ_ACCESS_GRANTED"
    AUTHZ_ACCESS_DENIED = "AUTHZ_ACCESS_DENIED"
    AUTHZ_PERMISSION_MISSING = "AUTHZ_PERMISSION_MISSING"
    AUTHZ_OWNERSHIP_FAILED = "AUTHZ_OWNERSHIP_FAILED"
    AUTHZ_RELATIONSHIP_FAILED = "AUTHZ_RELATIONSHIP_FAILED"

    # Consent lifecycle events
    CONSENT_CREATED = "CONSENT_CREATED"
    CONSENT_READ = "CONSENT_READ"
    CONSENT_REVOKED = "CONSENT_REVOKED"
    CONSENT_CHECK_PASSED = "CONSENT_CHECK_PASSED"
    CONSENT_CHECK_FAILED = "CONSENT_CHECK_FAILED"

    # Authentication events (mirrors Phase 2 logging for completeness)
    AUTH_LOGIN_SUCCESS = "AUTH_LOGIN_SUCCESS"
    AUTH_LOGIN_FAILURE = "AUTH_LOGIN_FAILURE"
    AUTH_REFRESH_SUCCESS = "AUTH_REFRESH_SUCCESS"
    AUTH_LOGOUT = "AUTH_LOGOUT"

    # Clinical record events (Phase 4)
    CLINICAL_RECORD_VIEWED = "CLINICAL_RECORD_VIEWED"
    PATIENT_PROFILE_UPDATED = "PATIENT_PROFILE_UPDATED"
    CLINICAL_HISTORY_CREATED = "CLINICAL_HISTORY_CREATED"
    CLINICAL_HISTORY_UPDATED = "CLINICAL_HISTORY_UPDATED"
    ALLERGY_CREATED = "ALLERGY_CREATED"
    ALLERGY_UPDATED = "ALLERGY_UPDATED"
    VITAL_RECORDED = "VITAL_RECORDED"
    ENCOUNTER_VIEWED = "ENCOUNTER_VIEWED"
    ENCOUNTER_CREATED = "ENCOUNTER_CREATED"
    CLINICAL_SUMMARY_VIEWED = "CLINICAL_SUMMARY_VIEWED"

    # Medical document events (Phase 5)
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    DOCUMENT_VIEWED = "DOCUMENT_VIEWED"
    DOCUMENT_DOWNLOAD_REQUESTED = "DOCUMENT_DOWNLOAD_REQUESTED"
    DOCUMENT_ARCHIVED = "DOCUMENT_ARCHIVED"
    DOCUMENT_PROCESSING_STARTED = "DOCUMENT_PROCESSING_STARTED"
    DOCUMENT_PROCESSING_COMPLETED = "DOCUMENT_PROCESSING_COMPLETED"
    DOCUMENT_PROCESSING_FAILED = "DOCUMENT_PROCESSING_FAILED"
    DOCUMENT_PROCESSING_RETRIED = "DOCUMENT_PROCESSING_RETRIED"
    DOCUMENT_EXTRACTION_CREATED = "DOCUMENT_EXTRACTION_CREATED"
    DOCUMENT_EXTRACTION_VIEWED = "DOCUMENT_EXTRACTION_VIEWED"

    # Prescription & Medication events (Phase 6)
    PRESCRIPTION_CREATED = "PRESCRIPTION_CREATED"
    PRESCRIPTION_VIEWED = "PRESCRIPTION_VIEWED"
    PRESCRIPTION_UPDATED = "PRESCRIPTION_UPDATED"
    PRESCRIPTION_NORMALIZATION_STARTED = "PRESCRIPTION_NORMALIZATION_STARTED"
    PRESCRIPTION_NORMALIZATION_COMPLETED = "PRESCRIPTION_NORMALIZATION_COMPLETED"
    PRESCRIPTION_NORMALIZATION_FAILED = "PRESCRIPTION_NORMALIZATION_FAILED"
    MEDICATION_CREATED = "MEDICATION_CREATED"
    MEDICATION_VIEWED = "MEDICATION_VIEWED"
    MEDICATION_UPDATED = "MEDICATION_UPDATED"
    MEDICATION_STATUS_CHANGED = "MEDICATION_STATUS_CHANGED"
    MEDICATION_CORRECTED = "MEDICATION_CORRECTED"


class AuditEventRecord(BaseModel):
    """Immutable audit event record for persistence and structured logging.

    Contains only the minimum metadata for accountability.
    Clinical payload content is NEVER included.
    """

    model_config = ConfigDict(frozen=True)

    event_type: AuditEventType
    actor_id: str | None = Field(
        default=None,
        description="User ID of the requester/actor. None for unauthenticated requests.",
    )
    action: str | None = Field(
        default=None,
        description="The action attempted (e.g., 'clinical_record:read')",
    )
    resource_type: str | None = Field(
        default=None,
        description="Type of resource targeted (e.g., 'clinical_record')",
    )
    resource_id: str | None = Field(
        default=None,
        description="Identifier of the targeted resource (non-clinical ID only)",
    )
    outcome: str = Field(description="'ALLOW' or 'DENY'")
    reason_code: str | None = Field(
        default=None,
        description="Internal reason code for denials (e.g., 'CONSENT_REVOKED')",
    )
    request_id: str | None = Field(
        default=None,
        description="Correlation request ID from middleware",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the event",
    )
    metadata: dict | None = Field(
        default=None,
        description="Optional minimal supplementary metadata. Must not contain PHI.",
    )
