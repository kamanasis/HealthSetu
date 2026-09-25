"""Pydantic schemas for patient allergy records.

IMPORTANT:
- Backend stores explicitly provided allergy information only.
- No automatic allergy inference from medications.
- No medication-interaction checking in Phase 4.
- No automatic severity scoring.

DATABASE TEAM DEPENDENCY — PHASE 4
====================================
Required allergy entity fields:
  id           : Primary Key (UUID)
  patient_id   : FOREIGN KEY → patients.id
  allergen     : VARCHAR — substance causing the reaction
  reaction     : NULLABLE VARCHAR — described reaction
  severity     : NULLABLE ENUM ('MILD', 'MODERATE', 'SEVERE', 'LIFE_THREATENING', 'UNKNOWN')
  status       : ENUM ('ACTIVE', 'INACTIVE', 'RESOLVED', 'UNKNOWN')
  source       : ENUM provenance type
  recorded_by  : NULLABLE VARCHAR (user_id)
  notes        : NULLABLE TEXT
  created_at   : TIMESTAMP WITH TIME ZONE
  updated_at   : TIMESTAMP WITH TIME ZONE
  is_archived  : BOOLEAN DEFAULT FALSE
"""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.clinical_history import ClinicalDataSource


class AllergySeverity(str, Enum):
    """Severity classification of an allergic reaction.

    DATABASE TEAM DEPENDENCY: align with actual enum values.
    Note: Severity is recorded as provided — not inferred by the backend.
    """
    MILD = "MILD"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"
    LIFE_THREATENING = "LIFE_THREATENING"
    UNKNOWN = "UNKNOWN"


class AllergyStatus(str, Enum):
    """Lifecycle status of an allergy record."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    RESOLVED = "RESOLVED"
    UNKNOWN = "UNKNOWN"


class AllergyCreateRequest(BaseModel):
    """Request body for recording a new allergy."""
    model_config = ConfigDict(extra="forbid")

    allergen: str = Field(
        ..., min_length=1, max_length=500,
        description="Substance or agent causing the allergic reaction",
        examples=["Penicillin", "Peanuts", "Latex"],
    )
    reaction: str | None = Field(
        default=None, max_length=1000,
        description="Description of the allergic reaction if known",
    )
    severity: AllergySeverity = Field(
        default=AllergySeverity.UNKNOWN,
        description="Severity of the reaction. Not inferred — must be explicitly provided.",
    )
    status: AllergyStatus = Field(
        default=AllergyStatus.ACTIVE,
        description="Current status of this allergy",
    )
    source: ClinicalDataSource = Field(
        default=ClinicalDataSource.PATIENT_ENTERED,
        description="Provenance of this allergy entry",
    )
    notes: str | None = Field(default=None, max_length=1000)


class AllergyUpdateRequest(BaseModel):
    """PATCH request for updating an allergy record."""
    model_config = ConfigDict(extra="forbid")

    reaction: str | None = Field(default=None, max_length=1000)
    severity: AllergySeverity | None = None
    status: AllergyStatus | None = None
    notes: str | None = Field(default=None, max_length=1000)


class AllergyResponse(BaseModel):
    """Public allergy record representation."""
    id: str
    patient_id: str
    allergen: str
    reaction: str | None = None
    severity: AllergySeverity
    status: AllergyStatus
    source: ClinicalDataSource
    recorded_by: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    is_archived: bool = False


class AllergyListResponse(BaseModel):
    items: list[AllergyResponse]
    total: int
