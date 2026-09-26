"""AI Task Definition & Lifecycle Schemas (Phase 14).

Defines task submission parameters, task definitions, and lifecycle state tracking.
Arbitrary open-ended prompts are prohibited; only allowlisted tasks with explicit
input contracts can be created.
"""

from datetime import datetime, timezone
from typing import Any
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ai import (
    AITaskStatus,
    AITaskType,
    AIVerificationStatus,
)


# ---------------------------------------------------------------------------
# Task Submission Envelopes
# ---------------------------------------------------------------------------

class AITaskCreateRequest(BaseModel):
    """Enforce controlled task creation with source evidence and target scope."""

    model_config = ConfigDict(extra="forbid")

    task_type: AITaskType = Field(description="Must be an allowlisted task type")
    patient_id: str | None = Field(default=None, description="HealthSetu internal patient ID")
    source_reference: str | None = Field(
        default=None,
        description="Identifier of primary source record (document_id, encounter_id, etc.)",
    )
    source_content: str | None = Field(
        default=None,
        description="Sanitized source text to process. Will be delimiter-protected before model call.",
        max_length=50000,
    )
    input_context: dict[str, Any] | None = Field(
        default=None,
        description="Optional structured context data for task-specific prompting",
    )
    parameters: dict[str, Any] | None = Field(
        default=None,
        description="Optional execution parameters (reading_level, focus_area)",
    )


class AITaskResponse(BaseModel):
    """Client response for an AI task creation or status inquiry."""

    model_config = ConfigDict(from_attributes=True)

    task_id: str
    task_type: AITaskType
    status: AITaskStatus
    patient_id: str | None = None
    verification_status: AIVerificationStatus = AIVerificationStatus.REVIEW_REQUIRED
    result_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


# ---------------------------------------------------------------------------
# Specific Task Input Context Models
# ---------------------------------------------------------------------------

class DocumentExtractionInput(BaseModel):
    """Input payload for medical document extraction."""

    model_config = ConfigDict(extra="ignore")

    document_id: str
    document_text: str = Field(min_length=1)
    filename: str | None = None
    document_type_hint: str | None = None


class SummarizationInput(BaseModel):
    """Input payload for clinical record summarization."""

    model_config = ConfigDict(extra="ignore")

    patient_id: str
    clinical_history: list[dict[str, Any]] = Field(default_factory=list)
    recent_vitals: list[dict[str, Any]] = Field(default_factory=list)
    allergies: list[dict[str, Any]] = Field(default_factory=list)
    medications: list[dict[str, Any]] = Field(default_factory=list)
    recent_encounters: list[dict[str, Any]] = Field(default_factory=list)


class PatientExplanationInput(BaseModel):
    """Input payload for simplifying clinical instructions."""

    model_config = ConfigDict(extra="ignore")

    source_text: str = Field(min_length=1)
    reading_level: str = Field(default="plain_language_grade_6")
    language: str = Field(default="en")


class SBARAssistanceInput(BaseModel):
    """Input payload for drafting SBAR communication."""

    model_config = ConfigDict(extra="ignore")

    patient_id: str
    symptom_summary: str = Field(min_length=1)
    vital_signs: dict[str, Any] = Field(default_factory=dict)
    known_diagnoses: list[str] = Field(default_factory=list)
    context_notes: str | None = None


class DischargeOrganizationInput(BaseModel):
    """Input payload for organizing discharge instructions."""

    model_config = ConfigDict(extra="ignore")

    discharge_text: str = Field(min_length=1)
    admission_diagnosis: str | None = None
    discharge_medications: list[dict[str, Any]] = Field(default_factory=list)


class CarePlanOrganizationInput(BaseModel):
    """Input payload for structuring care plans."""

    model_config = ConfigDict(extra="ignore")

    patient_id: str
    diagnoses: list[str] = Field(default_factory=list)
    raw_goals: list[str] = Field(default_factory=list)
    raw_interventions: list[str] = Field(default_factory=list)


class ClinicalNoteDraftInput(BaseModel):
    """Input payload for drafting SOAP documentation."""

    model_config = ConfigDict(extra="ignore")

    encounter_id: str | None = None
    patient_id: str
    chief_complaint: str
    history_of_present_illness: str
    physical_exam_findings: str | None = None
    clinician_impressions: str | None = None


# ---------------------------------------------------------------------------
# Persisted Task Record
# ---------------------------------------------------------------------------

class AITaskRecord(BaseModel):
    """Full persistence record for an AI task including all lifecycle state."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: f"aitask-{uuid.uuid4().hex[:12]}")
    task_type: AITaskType
    task_version: str = "1.0.0"
    status: AITaskStatus = AITaskStatus.QUEUED

    # Principal
    creator_id: str
    patient_id: str | None = None
    organization_id: str | None = None

    # Source
    source_reference: str | None = None
    source_content: str | None = None  # sanitized source text passed to model
    input_context: dict[str, Any] | None = None  # structured task context

    # Provider info
    provider_name: str | None = None
    model_name: str | None = None
    prompt_version: str = "1.0.0"

    # Execution tracking
    retry_count: int = 0
    max_retries: int = 2
    result_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
