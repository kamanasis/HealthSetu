"""Abstract base classes and interfaces for clinical triage rule engines.

Defines the contract for deterministic clinical triage rule providers.
Primary rule engines evaluate structured patient observations and return
traceable urgency classifications.
"""

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel, Field
from app.schemas.symptom import SymptomItemCreate
from app.schemas.triage import (
    TriageUrgency,
    TriageStatus,
    TriageReason,
    MissingInformationItem,
    TriageExplanation,
)


class TriageEvaluationContext(BaseModel):
    """Normalized structured clinical context passed to triage rule engine."""

    patient_id: str
    age: int | None = None
    biological_sex: str | None = None
    symptoms: list[SymptomItemCreate] = Field(default_factory=list)
    vitals: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured vitals dictionary e.g. {'heart_rate': 110, 'oxygen_saturation': 96, 'systolic_bp': 140, 'diastolic_bp': 90, 'respiratory_rate': 20, 'temperature_c': 38.5}",
    )
    vitals_recorded_at: dict[str, str] = Field(
        default_factory=dict,
        description="Timestamps for vitals to verify freshness",
    )
    known_conditions: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    current_medications: list[str] = Field(default_factory=list)
    recent_encounters: list[str] = Field(default_factory=list)


class TriageEngineResult(BaseModel):
    """Output produced by a deterministic triage rule engine."""

    urgency: TriageUrgency
    status: TriageStatus
    reasons: list[TriageReason] = Field(default_factory=list)
    missing_information: list[MissingInformationItem] = Field(default_factory=list)
    factors_considered: list[str] = Field(default_factory=list)
    urgency_rationale: str
    recommended_level_of_care: str
    immediate_instruction: str | None = None
    rule_set: str
    rule_set_version: str


class TriageRuleEngine(ABC):
    """Abstract interface for clinical triage evaluation."""

    @property
    @abstractmethod
    def rule_set_name(self) -> str:
        """Name of the triage rule protocol."""
        pass

    @property
    @abstractmethod
    def rule_set_version(self) -> str:
        """Version string of the triage rule protocol."""
        pass

    @abstractmethod
    async def evaluate(self, context: TriageEvaluationContext) -> TriageEngineResult:
        """Evaluate patient context against clinical protocol rules deterministically."""
        pass
