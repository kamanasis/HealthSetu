"""Abstract interface for clinical text generation (Phase 8).

Defines the contract for SBAR clinical summary generators.
Clinical Boundary:
- LLM text generators assist only with plain-language wording.
- Authoritative clinical facts and triage urgency originate strictly from verified sources.
"""

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel, Field
from app.schemas.sbar import (
    SBARSituation,
    SBARBackground,
    SBARAssessment,
    SBARRecommendation,
)
from app.schemas.triage import TriageUrgency


class SBARInputFacts(BaseModel):
    """Structured clinical facts provided as authoritative input to the SBAR generator."""

    patient_id: str
    urgency: TriageUrgency
    reason_for_attention: str
    presenting_symptoms: list[str] = Field(default_factory=list)
    known_conditions: list[str] = Field(default_factory=list)
    active_medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    recent_encounters: list[str] = Field(default_factory=list)
    triggered_rules: list[str] = Field(default_factory=list)
    vitals: dict[str, str] = Field(default_factory=dict)
    recommended_level_of_care: str
    immediate_instruction: str | None = None
    missing_information: list[str] = Field(default_factory=list)
    follow_up_recommendation: str


class SBARGeneratedOutput(BaseModel):
    """Generated SBAR narrative sections and plain text."""

    situation: SBARSituation
    background: SBARBackground
    assessment: SBARAssessment
    recommendation: SBARRecommendation
    plain_text: str
    model_metadata: dict[str, Any] = Field(default_factory=dict)


class ClinicalTextGenerator(ABC):
    """Abstract provider for clinical text synthesis."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the text generation provider."""
        pass

    @abstractmethod
    async def generate_sbar(self, facts: SBARInputFacts) -> SBARGeneratedOutput:
        """Generate structured SBAR clinical communication from structured facts."""
        pass
