"""Pydantic schemas for structured symptom intake (Phase 8).

Defines schema models for symptom intake, normalization tracking,
provenance preservation, and intake sessions.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
import uuid


class SymptomSource(str, Enum):
    """Provenance sources for symptom intake."""

    PATIENT_REPORTED = "PATIENT_REPORTED"
    CAREGIVER_REPORTED = "CAREGIVER_REPORTED"
    DOCTOR_ENTERED = "DOCTOR_ENTERED"
    CLINIC_ENTERED = "CLINIC_ENTERED"
    DOCUMENT_EXTRACTED = "DOCUMENT_EXTRACTED"
    IMPORTED = "IMPORTED"


class SymptomSeverity(str, Enum):
    """Clinical severity grading for patient-reported symptoms."""

    MILD = "MILD"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"
    CRITICAL = "CRITICAL"


class SymptomItemCreate(BaseModel):
    """Input payload for a single structured symptom."""

    model_config = ConfigDict(extra="forbid")

    symptom: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Reported symptom description (e.g., 'chest pain', 'fever')",
    )
    severity: SymptomSeverity | None = Field(
        default=None,
        description="Reported severity of the symptom",
    )
    onset: str | None = Field(
        default=None,
        max_length=100,
        description="Approximate onset (e.g., '2 hours ago', 'yesterday morning')",
    )
    duration: str | None = Field(
        default=None,
        max_length=100,
        description="Duration of symptom (e.g., 'continuous for 30 minutes', 'intermittent 3 days')",
    )
    location: str | None = Field(
        default=None,
        max_length=150,
        description="Anatomical location (e.g., 'substernal', 'left shoulder', 'bilateral legs')",
    )
    character: str | None = Field(
        default=None,
        max_length=150,
        description="Quality or character (e.g., 'sharp', 'pressure-like', 'throbbing', 'burning')",
    )
    frequency: str | None = Field(
        default=None,
        max_length=100,
        description="Frequency pattern (e.g., 'constant', 'intermittent', 'worsening with exertion')",
    )
    progression: str | None = Field(
        default=None,
        max_length=100,
        description="Progression over time (e.g., 'worsening', 'improving', 'unchanged')",
    )
    associated_symptoms: list[str] = Field(
        default_factory=list,
        description="Associated symptoms (e.g., ['nausea', 'diaphoresis', 'lightheadedness'])",
    )
    aggravating_factors: list[str] = Field(
        default_factory=list,
        description="Factors aggravating the symptom (e.g., ['walking up stairs', 'deep breath'])",
    )
    relieving_factors: list[str] = Field(
        default_factory=list,
        description="Factors relieving the symptom (e.g., ['rest', 'nitroglycerin', 'sitting up'])",
    )
    patient_reported_context: str | None = Field(
        default=None,
        max_length=500,
        description="Direct narrative context reported by patient/caregiver",
    )


class SymptomRecord(BaseModel):
    """Complete persisted symptom record with provenance and normalization."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    intake_id: str | None = None
    encounter_id: str | None = None
    symptom_raw: str = Field(description="Exact raw symptom description as reported")
    symptom_normalized: str | None = Field(
        default=None,
        description="Standardized clinical term (if normalized). NOTE: Normalization is NOT diagnosis.",
    )
    severity: SymptomSeverity | None = None
    onset: str | None = None
    duration: str | None = None
    location: str | None = None
    character: str | None = None
    frequency: str | None = None
    progression: str | None = None
    associated_symptoms: list[str] = Field(default_factory=list)
    aggravating_factors: list[str] = Field(default_factory=list)
    relieving_factors: list[str] = Field(default_factory=list)
    patient_reported_context: str | None = None
    source: SymptomSource = SymptomSource.PATIENT_REPORTED
    recorded_by: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SymptomIntakeCreate(BaseModel):
    """Input payload to record a structured symptom intake batch or session."""

    model_config = ConfigDict(extra="forbid")

    encounter_id: str | None = Field(
        default=None,
        description="Optional encounter reference associated with this intake session",
    )
    source: SymptomSource = Field(
        default=SymptomSource.PATIENT_REPORTED,
        description="Provenance of the intake entry",
    )
    symptoms: list[SymptomItemCreate] = Field(
        ...,
        min_length=1,
        description="List of one or more symptoms to record",
    )
    notes: str | None = Field(
        default=None,
        max_length=500,
        description="Optional intake session notes",
    )


class SymptomIntakeResponse(BaseModel):
    """API response for a created symptom intake session."""

    intake_id: str
    patient_id: str
    encounter_id: str | None = None
    source: SymptomSource
    symptoms: list[SymptomRecord]
    notes: str | None = None
    created_at: datetime


class SymptomListResponse(BaseModel):
    """Paginated list of patient symptoms."""

    items: list[SymptomRecord]
    total: int
    limit: int
    offset: int
