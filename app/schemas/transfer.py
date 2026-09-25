"""Patient Transfer and Referral Schemas (Phase 12).

Defines request/response models, status state machine, and storage records
for explicit patient transfers and referrals.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class TransferStatus(str, Enum):
    """Lifecycle status states for a patient transfer or referral request."""
    REQUESTED = "REQUESTED"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


# Allowed state transitions for transfer lifecycle
VALID_TRANSFER_TRANSITIONS: dict[TransferStatus, set[TransferStatus]] = {
    TransferStatus.REQUESTED: {
        TransferStatus.ACCEPTED,
        TransferStatus.DECLINED,
        TransferStatus.CANCELLED,
    },
    TransferStatus.ACCEPTED: {
        TransferStatus.IN_PROGRESS,
        TransferStatus.CANCELLED,
    },
    TransferStatus.IN_PROGRESS: {
        TransferStatus.COMPLETED,
        TransferStatus.FAILED,
        TransferStatus.CANCELLED,
    },
    # Terminal states
    TransferStatus.DECLINED: set(),
    TransferStatus.COMPLETED: set(),
    TransferStatus.CANCELLED: set(),
    TransferStatus.FAILED: set(),
}


class TransferPriority(str, Enum):
    """Clinical priority indicator for a transfer or referral."""
    ROUTINE = "ROUTINE"
    URGENT = "URGENT"
    EMERGENCY = "EMERGENCY"


class TransferCreateRequest(BaseModel):
    """Payload to create an explicit patient transfer/referral request."""
    sending_facility_id: str = Field(description="Originating healthcare facility ID")
    receiving_facility_id: str = Field(description="Destination healthcare facility ID")
    reason: str = Field(min_length=3, description="Clinical reason or objective of transfer")
    encounter_id: str | None = Field(default=None, description="Associated encounter ID")
    priority: TransferPriority = Field(default=TransferPriority.ROUTINE, description="Transfer priority level")
    sbar_id: str | None = Field(default=None, description="Optional SBAR report reference ID")
    consent_id: str | None = Field(default=None, description="Optional patient consent record ID")
    clinical_context_reference: str | None = Field(default=None, description="Reference token for shared clinical data")
    notes: str | None = Field(default=None, description="Additional transfer coordination notes")


class TransferStatusUpdateRequest(BaseModel):
    """Payload to transition a transfer's status."""
    status: TransferStatus = Field(description="Target status state")
    reason: str | None = Field(default=None, description="Reason for status change (e.g. decline/cancel rationale)")
    notes: str | None = Field(default=None, description="Status update details")


class TransferRecord(BaseModel):
    """Database entity / domain record representation for a transfer request."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    encounter_id: str | None = None
    sending_organization_id: str
    sending_facility_id: str
    receiving_organization_id: str
    receiving_facility_id: str
    status: TransferStatus = TransferStatus.REQUESTED
    priority: TransferPriority = TransferPriority.ROUTINE
    reason: str
    sbar_id: str | None = None
    consent_id: str | None = None
    clinical_context_reference: str | None = None
    notes: str | None = None
    status_history: list[dict[str, Any]] = Field(default_factory=list)
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TransferResponse(BaseModel):
    """Public API response schema for a transfer record."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    encounter_id: str | None = None
    sending_organization_id: str
    sending_facility_id: str
    receiving_organization_id: str
    receiving_facility_id: str
    status: TransferStatus
    priority: TransferPriority
    reason: str
    sbar_id: str | None = None
    consent_id: str | None = None
    clinical_context_reference: str | None = None
    notes: str | None = None
    status_history: list[dict[str, Any]] = Field(default_factory=list)
    created_by: str
    created_at: datetime
    updated_at: datetime


class TransferListResponse(BaseModel):
    """List of transfer records."""
    items: list[TransferResponse]
    total: int
