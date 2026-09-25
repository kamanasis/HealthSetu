"""Pydantic schemas for patient clinical history entries.

Clinical history represents structured patient-reported or clinician-recorded
health history items (conditions, diagnoses, past events).

IMPORTANT:
- This is NOT a diagnosis system.
- Backend stores what is explicitly provided.
- No inference, no severity scoring, no medical interpretation.

DATABASE TEAM DEPENDENCY — PHASE 4
====================================
Required clinical_history entity fields:
  id           : Primary Key (UUID)
  patient_id   : FOREIGN KEY → patients.id
  description  : VARCHAR — structured description of the condition/event
  condition_status : ENUM ('ACTIVE', 'RESOLVED', 'HISTORICAL', 'UNKNOWN')
  onset_date   : NULLABLE DATE
  resolved_date: NULLABLE DATE
  source       : ENUM provenance type
  recorded_by  : NULLABLE VARCHAR (user_id of actor)
  notes        : NULLABLE TEXT (non-clinical free text notes)
  created_at   : TIMESTAMP WITH TIME ZONE
  updated_at   : TIMESTAMP WITH TIME ZONE
  is_archived  : BOOLEAN DEFAULT FALSE (soft delete only)
"""

from datetime import date, datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class ConditionStatus(str, Enum):
    """Lifecycle state of a clinical condition/history item."""
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"
    HISTORICAL = "HISTORICAL"
    UNKNOWN = "UNKNOWN"


class ClinicalDataSource(str, Enum):
    """Provenance of a clinical data entry.

    DATABASE TEAM DEPENDENCY: align with actual enum values.
    """
    PATIENT_ENTERED = "PATIENT_ENTERED"
    CLINIC_ENTERED = "CLINIC_ENTERED"
    IMPORTED = "IMPORTED"
    DOCUMENT_EXTRACTED = "DOCUMENT_EXTRACTED"
    DEVICE = "DEVICE"
    SYSTEM_GENERATED = "SYSTEM_GENERATED"
    UNKNOWN = "UNKNOWN"


class ClinicalHistoryCreateRequest(BaseModel):
    """Request body for creating a clinical history entry."""
    model_config = ConfigDict(extra="forbid")

    description: str = Field(
        ..., min_length=2, max_length=2000,
        description="Structured description of the condition or health event",
    )
    condition_status: ConditionStatus = Field(
        default=ConditionStatus.UNKNOWN,
        description="Current status of the condition",
    )
    onset_date: date | None = Field(
        default=None,
        description="Date of onset (if known). Must not be in the future.",
    )
    resolved_date: date | None = Field(
        default=None,
        description="Date resolved (if applicable). Must be >= onset_date if both provided.",
    )
    source: ClinicalDataSource = Field(
        default=ClinicalDataSource.PATIENT_ENTERED,
        description="Provenance of this entry",
    )
    notes: str | None = Field(
        default=None, max_length=2000,
        description="Optional free-text notes. Not a clinical diagnosis field.",
    )


class ClinicalHistoryUpdateRequest(BaseModel):
    """PATCH request for updating a clinical history entry."""
    model_config = ConfigDict(extra="forbid")

    condition_status: ConditionStatus | None = None
    resolved_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)


class ClinicalHistoryResponse(BaseModel):
    """Public clinical history entry representation."""
    id: str
    patient_id: str
    description: str
    condition_status: ConditionStatus
    onset_date: date | None = None
    resolved_date: date | None = None
    source: ClinicalDataSource
    recorded_by: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    is_archived: bool = False


class ClinicalHistoryListResponse(BaseModel):
    items: list[ClinicalHistoryResponse]
    total: int
