"""Abstract interface for discharge instruction extraction (Phase 9).

Contract for extractors that analyze clinical document text (from Phase 5 OCR/Extractions)
and yield structured discharge instructions.
"""

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel, Field
from app.schemas.discharge import (
    DischargeActivityInstruction,
    DischargeDietInstruction,
    DischargeFollowUpItem,
    DischargeMedicationItem,
    DischargeWarningSign,
    DischargeWoundCareInstruction,
)


class ExtractedDischargeData(BaseModel):
    """Structured extraction output from a discharge summary."""

    discharge_diagnoses: list[str] = Field(default_factory=list)
    medications: list[DischargeMedicationItem] = Field(default_factory=list)
    activity_instructions: list[DischargeActivityInstruction] = Field(default_factory=list)
    diet_instructions: list[DischargeDietInstruction] = Field(default_factory=list)
    wound_care_instructions: list[DischargeWoundCareInstruction] = Field(default_factory=list)
    warning_signs: list[DischargeWarningSign] = Field(default_factory=list)
    follow_up_instructions: list[DischargeFollowUpItem] = Field(default_factory=list)
    confidence_score: float = 1.0
    extractor_version: str = "1.0.0"


class DischargeExtractor(ABC):
    """Abstract interface for discharge summary text extractors."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the extractor provider."""
        pass

    @abstractmethod
    async def extract_discharge_instructions(self, document_text: str) -> ExtractedDischargeData:
        """Extract structured discharge instructions from document raw text."""
        pass
