"""Pydantic schemas for clinical encounters.

An encounter is a stable clinical interaction context.
It provides a reference anchor for other clinical domains
(history entries, vitals, documents, prescriptions).

This phase provides the minimal encounter foundation.
Full doctor/hospital workflow belongs to later phases.

DATABASE TEAM DEPENDENCY — PHASE 4
====================================
Required encounter entity fields:
  id              : Primary Key (UUID)
  patient_id      : FOREIGN KEY → patients.id
  encounter_type  : ENUM or VARCHAR
  status          : ENUM ('PLANNED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')
  start_time      : TIMESTAMP WITH TIME ZONE
  end_time        : NULLABLE TIMESTAMP WITH TIME ZONE
  provider_id     : NULLABLE VARCHAR (future: FOREIGN KEY → users.id)
  organization_id : NULLABLE VARCHAR (future: FOREIGN KEY → organizations.id)
  external_id     : NULLABLE VARCHAR (for interoperability reference)
  source          : ENUM provenance type
  notes           : NULLABLE TEXT (non-clinical operational notes)
  created_at      : TIMESTAMP WITH TIME ZONE
  updated_at      : TIMESTAMP WITH TIME ZONE
"""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.clinical_history import ClinicalDataSource


class EncounterType(str, Enum):
    """Type of clinical encounter.

    DATABASE TEAM DEPENDENCY: align with actual reference enum/table.
    """
    OUTPATIENT = "OUTPATIENT"
    INPATIENT = "INPATIENT"
    EMERGENCY = "EMERGENCY"
    TELEMEDICINE = "TELEMEDICINE"
    OTHER = "OTHER"


class EncounterStatus(str, Enum):
    """Encounter lifecycle state."""
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class EncounterCreateRequest(BaseModel):
    """Request body for creating a new encounter record."""
    model_config = ConfigDict(extra="forbid")

    encounter_type: EncounterType = Field(description="Type of this clinical encounter")
    status: EncounterStatus = Field(
        default=EncounterStatus.PLANNED,
        description="Initial lifecycle status of the encounter",
    )
    start_time: datetime = Field(
        description="Scheduled or actual start time. Must be timezone-aware.",
    )
    end_time: datetime | None = Field(
        default=None,
        description="End time if already completed. Must be after start_time.",
    )
    provider_id: str | None = Field(
        default=None, max_length=255,
        description="Provider user ID (future: validated against provider registry)",
    )
    organization_id: str | None = Field(
        default=None, max_length=255,
        description="Organization identifier (future: validated against org registry)",
    )
    external_id: str | None = Field(
        default=None, max_length=255,
        description="External identifier for interoperability (ABDM, FHIR, etc.)",
    )
    source: ClinicalDataSource = Field(
        default=ClinicalDataSource.CLINIC_ENTERED,
    )
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_times(self) -> "EncounterCreateRequest":
        if not self.start_time.tzinfo:
            raise ValueError("start_time must include timezone information (use UTC).")
        if self.end_time is not None:
            if not self.end_time.tzinfo:
                raise ValueError("end_time must include timezone information (use UTC).")
            if self.end_time < self.start_time:
                raise ValueError("end_time must be after start_time.")
        return self


class EncounterResponse(BaseModel):
    """Public encounter record representation."""
    id: str
    patient_id: str
    encounter_type: EncounterType
    status: EncounterStatus
    start_time: datetime
    end_time: datetime | None = None
    provider_id: str | None = None
    organization_id: str | None = None
    external_id: str | None = None
    source: ClinicalDataSource
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class EncounterListResponse(BaseModel):
    items: list[EncounterResponse]
    total: int
