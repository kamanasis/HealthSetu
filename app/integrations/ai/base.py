"""AI Provider and Clinical Text Generation Interfaces (Phase 8 & Phase 14).

Clinical Boundary:
- LLM text generators assist only with plain-language wording and extraction.
- Authoritative clinical facts and triage urgency originate strictly from verified sources.
- AI provider output is NOT clinical truth and must not self-verify.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, Field

from app.integrations.ai.models import AIProviderRequest, AIProviderResponse
from app.schemas.sbar import (
    SBARSituation,
    SBARBackground,
    SBARAssessment,
    SBARRecommendation,
)
from app.schemas.triage import TriageUrgency


# ---------------------------------------------------------------------------
# Phase 8: SBAR Text Generation Interface
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Phase 14: AI Orchestration Provider Interface
# ---------------------------------------------------------------------------

class AIProvider(ABC):
    """Abstract interface for AI model execution providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Configured model name."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Adapter or model deployment version."""
        pass

    @abstractmethod
    async def generate_text(self, request: AIProviderRequest) -> AIProviderResponse:
        """Generate unstructured or text-based output from the model."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        request: AIProviderRequest,
        schema: Type[BaseModel],
    ) -> AIProviderResponse:
        """Generate validated, structured JSON output conforming to target schema."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check provider connectivity, authentication, and availability."""
        pass

    @abstractmethod
    def get_model_metadata(self) -> Dict[str, Any]:
        """Return operational metadata about the configured model deployment."""
        pass
