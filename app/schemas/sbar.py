"""Pydantic schemas for SBAR clinical communication summaries (Phase 8).

SBAR (Situation, Background, Assessment, Recommendation) provides a structured,
standardized framework for clinical communication between healthcare providers.

Clinical boundary:
- Built strictly from verified structured source facts.
- No autonomous diagnosis or treatment recommendations.
- Validates that AI-generated wording does not hallucinate facts.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
import uuid
from app.schemas.triage import TriageUrgency


class SBARGenerationMode(str, Enum):
    """Method utilized to generate SBAR clinical communication text."""

    TEMPLATE = "template"  # Deterministic templating
    AI = "ai"              # AI-assisted prose generation with strict fact validation


class SBARSituation(BaseModel):
    """Situation: Current clinical urgency, immediate concern, and presenting symptoms."""

    reason_for_attention: str = Field(description="Summary of current clinical prompt or concern")
    current_urgency: TriageUrgency = Field(description="Triage urgency classification")
    presenting_symptoms: list[str] = Field(default_factory=list, description="List of active symptoms")
    summary_text: str = Field(description="Formatted narrative for Situation section")


class SBARBackground(BaseModel):
    """Background: Relevant documented clinical history, conditions, medications, and allergies."""

    known_conditions: list[str] = Field(default_factory=list)
    active_medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    recent_encounters: list[str] = Field(default_factory=list)
    summary_text: str = Field(description="Formatted narrative for Background section")


class SBARAssessment(BaseModel):
    """Assessment: Rule-based triage evaluation, triggered rules, and vital signs."""

    urgency: TriageUrgency
    triggered_rules: list[str] = Field(default_factory=list)
    evaluated_vitals: dict[str, str] = Field(default_factory=dict)
    summary_text: str = Field(description="Formatted narrative for Assessment section")


class SBARRecommendation(BaseModel):
    """Recommendation: Recommended level of care, immediate instructions, and missing information."""

    recommended_level_of_care: str
    immediate_instruction: str | None = None
    missing_information: list[str] = Field(default_factory=list)
    follow_up_recommendation: str
    summary_text: str = Field(description="Formatted narrative for Recommendation section")


class SBARFactValidationResult(BaseModel):
    """Validation report verifying SBAR facts against structured source data."""

    is_valid: bool
    validation_errors: list[str] = Field(default_factory=list)
    verified_symptoms: list[str] = Field(default_factory=list)
    verified_medications: list[str] = Field(default_factory=list)
    verified_allergies: list[str] = Field(default_factory=list)
    verified_conditions: list[str] = Field(default_factory=list)
    verified_urgency: str | None = None


class SBARCreate(BaseModel):
    """Request payload to generate an SBAR clinical summary."""

    model_config = ConfigDict(extra="forbid")

    assessment_id: str = Field(
        ...,
        description="Reference to the authoritative triage assessment",
    )
    encounter_id: str | None = Field(
        default=None,
        description="Optional encounter reference",
    )
    intake_id: str | None = Field(
        default=None,
        description="Optional intake session reference",
    )
    generation_mode: SBARGenerationMode | None = Field(
        default=None,
        description="Optional generation mode override ('template' or 'ai')",
    )


class SBARRecord(BaseModel):
    """Immutable SBAR clinical record with provenance and validation status."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    assessment_id: str
    encounter_id: str | None = None
    intake_id: str | None = None
    generation_mode: SBARGenerationMode
    situation: SBARSituation
    background: SBARBackground
    assessment: SBARAssessment
    recommendation: SBARRecommendation
    plain_text: str = Field(description="Standardized plain-text representation of SBAR")
    validation_result: SBARFactValidationResult | None = None
    generator_version: str = "1.0.0"
    model_metadata: dict[str, Any] | None = None
    created_by: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SBARResponse(BaseModel):
    """API response containing structured SBAR and plain text representation."""

    sbar_id: str
    patient_id: str
    assessment_id: str
    encounter_id: str | None = None
    intake_id: str | None = None
    generation_mode: SBARGenerationMode
    situation: SBARSituation
    background: SBARBackground
    assessment: SBARAssessment
    recommendation: SBARRecommendation
    plain_text: str
    created_at: datetime
