"""AI Structured Output Schemas & Result Models (Phase 14).

Defines strongly-typed Pydantic result structures for each allowlisted AI task.
Every model output must validate against these explicit schemas.

Strict clinical boundaries:
- Formats are validated before domain ingestion.
- Missing information and uncertainties are surfaced explicitly.
- Results require clinical verification (`REVIEW_REQUIRED`) for patient data.
"""

from datetime import datetime, timezone
from typing import Any
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ai import (
    AIConfidenceLevel,
    AIGroundingStatus,
    AIProvenanceRecord,
    AISourceReference,
    AITaskType,
    AIUsageMetadata,
    AIVerificationStatus,
)


# ---------------------------------------------------------------------------
# Base Structured Result
# ---------------------------------------------------------------------------

class AIBaseStructuredResult(BaseModel):
    """Base payload for all validated AI task outputs."""

    model_config = ConfigDict(extra="ignore")

    confidence_level: AIConfidenceLevel = Field(
        default=AIConfidenceLevel.UNKNOWN,
        description="System confidence indicator. Not clinical certainty.",
    )
    source_citations: list[AISourceReference] = Field(
        default_factory=list,
        description="Traceable citations linking claims to source document/facts",
    )
    uncertainties: list[str] = Field(
        default_factory=list,
        description="Ambiguities or unconfirmed details explicitly identified",
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="Expected clinical details that were absent in source data",
    )


# ---------------------------------------------------------------------------
# Specific Task Output Schemas
# ---------------------------------------------------------------------------

class DocumentExtractionResult(AIBaseStructuredResult):
    """Structured extraction of clinical facts from medical documents."""

    document_type: str = Field(default="Unknown", description="Detected document classification")
    patient_name: str | None = None
    extracted_allergies: list[dict[str, Any]] = Field(default_factory=list)
    extracted_vitals: list[dict[str, Any]] = Field(default_factory=list)
    extracted_medications: list[dict[str, Any]] = Field(default_factory=list)
    extracted_diagnoses: list[dict[str, Any]] = Field(default_factory=list)
    extracted_procedures: list[dict[str, Any]] = Field(default_factory=list)
    encounter_date: str | None = None


class ClinicalSummaryResult(AIBaseStructuredResult):
    """Factual clinical summary assembled strictly from known patient data."""

    summary_narrative: str = Field(default="", description="Concise clinical narrative")
    key_findings: list[str] = Field(default_factory=list)
    active_problems: list[str] = Field(default_factory=list)
    current_medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    recent_vital_trends: list[str] = Field(default_factory=list)


class PatientExplanationResult(AIBaseStructuredResult):
    """Patient-friendly simplification of medical terminology and instructions."""

    simplified_explanation: str = Field(default="", description="Plain language translation")
    reading_level: str = Field(default="plain_language_grade_6")
    action_items: list[str] = Field(default_factory=list, description="Clear, non-prescriptive actions for the patient")
    questions_to_ask_doctor: list[str] = Field(default_factory=list)
    medical_terms_glossary: dict[str, str] = Field(default_factory=dict)


class SBARAssistanceResult(AIBaseStructuredResult):
    """Drafted SBAR communication language grounded in verified clinical observations."""

    situation: str = Field(default="")
    background: str = Field(default="")
    assessment: str = Field(default="")
    recommendation: str = Field(default="")
    clinical_facts_used: list[str] = Field(default_factory=list)


class DischargeOrganizationResult(AIBaseStructuredResult):
    """Organized presentation of source discharge instructions."""

    organized_instructions: list[str] = Field(default_factory=list)
    medication_changes: list[str] = Field(default_factory=list)
    follow_up_appointments: list[str] = Field(default_factory=list)
    warning_signs_red_flags: list[str] = Field(default_factory=list)
    activity_and_diet_restrictions: list[str] = Field(default_factory=list)


class CarePlanOrganizationResult(AIBaseStructuredResult):
    """Organized care plan components structured from clinician inputs."""

    patient_goals: list[dict[str, Any]] = Field(default_factory=list)
    planned_interventions: list[dict[str, Any]] = Field(default_factory=list)
    monitoring_schedule: list[dict[str, Any]] = Field(default_factory=list)
    barriers_to_adherence: list[str] = Field(default_factory=list)


class ClinicalNoteDraftResult(AIBaseStructuredResult):
    """Clinician documentation draft adhering to SOAP conventions."""

    subjective: str = Field(default="")
    objective: str = Field(default="")
    assessment: str = Field(default="")
    plan: str = Field(default="")
    full_draft_text: str = Field(default="")


class StructuredClassificationResult(AIBaseStructuredResult):
    """Non-authoritative classification or categorization of text."""

    category: str = Field(default="UNKNOWN")
    subcategories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    rationale: str | None = None


# ---------------------------------------------------------------------------
# Persisted Record & API Responses
# ---------------------------------------------------------------------------

class AIResultRecord(BaseModel):
    """Persisted AI output record with full audit metadata and mandatory review gate."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: f"aires-{uuid.uuid4().hex[:12]}")
    task_id: str
    task_type: AITaskType

    # Verification boundary — ALWAYS starts as REVIEW_REQUIRED
    verification_status: AIVerificationStatus = AIVerificationStatus.REVIEW_REQUIRED
    verified_by: str | None = None
    verified_at: datetime | None = None
    verification_notes: str | None = None
    corrected_output: dict[str, Any] | None = None

    # Grounding & confidence
    grounding_status: AIGroundingStatus = AIGroundingStatus.GROUNDED
    confidence: AIConfidenceLevel = AIConfidenceLevel.UNKNOWN
    unsupported_claims: list[str] = Field(default_factory=list)

    # Structured output (validated AI payload)
    structured_output: dict[str, Any] = Field(default_factory=dict)

    # Provenance & usage tracking
    provenance: AIProvenanceRecord | None = None
    usage: AIUsageMetadata | None = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AIResultResponse(BaseModel):
    """API response model for AI execution result."""

    model_config = ConfigDict(from_attributes=True)

    result_id: str
    task_id: str
    task_type: AITaskType
    status: str
    verification_status: AIVerificationStatus
    confidence_level: AIConfidenceLevel
    grounding_status: AIGroundingStatus
    data: dict[str, Any]
    source_citations: list[dict[str, Any]] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    verified_by: str | None = None
    verified_at: datetime | None = None
    created_at: datetime


class AIVerificationRequest(BaseModel):
    """Clinician action to review, verify, correct, or reject AI result."""

    model_config = ConfigDict(extra="forbid")

    verification_status: AIVerificationStatus = Field(
        description="VERIFIED or REJECTED (cannot reset to REVIEW_REQUIRED)"
    )
    notes: str | None = Field(default=None, max_length=1000, alias="verification_notes")
    corrected_output: dict[str, Any] | None = Field(
        default=None,
        description="Optional clinician-corrected fields",
    )

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
