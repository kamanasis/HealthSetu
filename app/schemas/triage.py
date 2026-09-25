"""Pydantic schemas for clinical triage assessment (Phase 8).

Enforces strict clinical boundaries:
- Triage produces an urgency category, NOT a medical diagnosis.
- Deterministic rule evaluations are traceable and versioned.
- Missing information is explicitly tracked and never guessed.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
import uuid
from app.schemas.symptom import SymptomItemCreate


TRIAGE_CLINICAL_DISCLAIMER: str = (
    "DISCLAIMER: Triage assessment determines clinical urgency classification based on "
    "configured clinical rule protocols. It does NOT constitute a medical diagnosis, treatment plan, "
    "or prescription, and does not replace in-person physician evaluation. If you believe you are "
    "experiencing a medical emergency, seek emergency medical care immediately."
)


class TriageUrgency(str, Enum):
    """Authoritative urgency classifications derived from clinical rules."""

    EMERGENCY = "EMERGENCY"      # Immediate emergency medical assessment required
    URGENT = "URGENT"            # Prompt clinical evaluation required (within hours)
    SAME_DAY = "SAME_DAY"        # Clinician assessment recommended within 24 hours
    ROUTINE = "ROUTINE"          # Standard non-urgent outpatient evaluation
    SELF_CARE = "SELF_CARE"      # Self-care / monitoring with safety-net guidance


class TriageStatus(str, Enum):
    """Execution status of a triage evaluation."""

    COMPLETED = "COMPLETED"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    FAILED = "FAILED"


class TriageReason(BaseModel):
    """Traceable reason and rule triggering a triage classification."""

    rule_id: str = Field(description="Unique identifier of the rule triggered")
    reason_code: str = Field(description="Structured clinical reason code (e.g. 'RULE_RED_CARDIO')")
    description: str = Field(description="Human-readable explanation of rule criteria met")
    source: str = Field(description="Clinical protocol / standard source")
    urgency_assigned: TriageUrgency = Field(description="Urgency category dictated by this rule")


class MissingInformationItem(BaseModel):
    """Explicitly tracked missing clinical data to avoid guessing."""

    field: str = Field(description="Clinical observation name (e.g., 'oxygen_saturation')")
    importance: str = Field(
        default="REQUIRED",
        description="'REQUIRED' (blocks assessment) or 'RECOMMENDED' (improves specificity)",
    )
    description: str = Field(description="Explanation of why this vital or observation is needed")


class TriageExplanation(BaseModel):
    """Structured, controlled explanation of the triage result without diagnostic claims."""

    summary: str = Field(description="High-level overview of triage evaluation")
    factors_considered: list[str] = Field(
        default_factory=list,
        description="Structured list of symptoms, vitals, or clinical context evaluated",
    )
    urgency_rationale: str = Field(description="Why the rule engine assigned this urgency level")
    missing_data_summary: list[str] = Field(
        default_factory=list,
        description="Any missing clinical data identified during evaluation",
    )
    recommended_level_of_care: str = Field(
        description="Recommended clinical care setting (e.g., 'Emergency Department', 'Urgent Care', 'Primary Care')",
    )
    disclaimer: str = Field(
        default=TRIAGE_CLINICAL_DISCLAIMER,
        description="Mandatory clinical boundary disclaimer",
    )


class TriageAssessmentCreate(BaseModel):
    """Request payload to initiate a clinical triage assessment."""

    model_config = ConfigDict(extra="forbid")

    intake_id: str | None = Field(
        default=None,
        description="Optional reference to an existing symptom intake session",
    )
    symptom_ids: list[str] = Field(
        default_factory=list,
        description="List of existing symptom IDs to evaluate",
    )
    symptoms: list[SymptomItemCreate] = Field(
        default_factory=list,
        description="Newly supplied symptoms to include in this triage assessment",
    )
    vital_ids: list[str] = Field(
        default_factory=list,
        description="Phase 4 vital measurement record IDs to evaluate",
    )
    encounter_id: str | None = Field(
        default=None,
        description="Optional encounter association",
    )
    assessment_type: str = Field(
        default="INITIAL",
        description="'INITIAL' or 'REASSESSMENT'",
    )
    previous_assessment_id: str | None = Field(
        default=None,
        description="If this is a reassessment, the ID of the assessment being re-evaluated",
    )
    idempotency_key: str | None = Field(
        default=None,
        description="Optional client-supplied idempotency key to prevent accidental duplicate assessments",
    )


class TriageAssessmentRecord(BaseModel):
    """Immutable clinical triage assessment record with full provenance."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    encounter_id: str | None = None
    intake_id: str | None = None
    urgency: TriageUrgency
    status: TriageStatus
    reasons: list[TriageReason] = Field(default_factory=list)
    missing_information: list[MissingInformationItem] = Field(default_factory=list)
    rule_set: str = Field(description="Name of the clinical triage protocol evaluated")
    rule_set_version: str = Field(description="Version of the clinical triage protocol")
    explanation: TriageExplanation
    immediate_instruction: str | None = Field(
        default=None,
        description="Crucial immediate action instruction (e.g., 'Seek emergency medical care now.')",
    )
    previous_assessment_id: str | None = None
    sbar_id: str | None = None
    idempotency_key: str | None = None
    assessed_by: str | None = None
    assessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TriageAssessmentResponse(BaseModel):
    """API response for a triage assessment."""

    assessment_id: str
    patient_id: str
    urgency: TriageUrgency
    status: TriageStatus
    reasons: list[TriageReason]
    missing_information: list[MissingInformationItem]
    explanation: TriageExplanation
    immediate_instruction: str | None = None
    rule_set: str
    rule_set_version: str
    previous_assessment_id: str | None = None
    sbar_id: str | None = None
    assessed_at: datetime


class TriageListResponse(BaseModel):
    """Paginated list of triage assessments."""

    items: list[TriageAssessmentRecord]
    total: int
    limit: int
    offset: int
