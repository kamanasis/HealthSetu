"""Medication terminology provider interfaces and domain data transfer models."""

from typing import Protocol, runtime_checkable
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.prescription import NormalizationStatus


class RawMedicationInput(BaseModel):
    """Raw medication information extracted from a prescription or entered by a user."""
    model_config = ConfigDict(frozen=True)

    drug_name_raw: str = Field(min_length=1, description="Raw drug name as written in prescription")
    strength_raw: str | None = Field(default=None, description="Raw strength string (e.g. '500 mg', '0.5 g')")
    dosage_form_raw: str | None = Field(default=None, description="Raw dosage form (e.g. 'tab', 'capsule')")
    route_raw: str | None = Field(default=None, description="Raw route (e.g. 'po', 'oral')")
    frequency_raw: str | None = Field(default=None, description="Raw frequency (e.g. '1-0-1', 'twice daily')")
    duration_raw: str | None = Field(default=None, description="Raw duration (e.g. '5 days')")
    instructions_raw: str | None = Field(default=None, description="Raw directions (e.g. 'after food')")


class NormalizedConcept(BaseModel):
    """Standardized medication concept returned by a terminology provider."""
    model_config = ConfigDict(frozen=True)

    canonical_name: str = Field(description="Canonical normalized medication name")
    generic_name: str | None = Field(default=None, description="Generic ingredient concept")
    brand_name: str | None = Field(default=None, description="Brand name if identified")
    terminology_system: str = Field(description="Terminology system identifier (e.g. RXNORM, LOCAL_MOCK)")
    terminology_code: str = Field(description="Terminology concept identifier/code")
    normalized_strength: str | None = Field(default=None, description="Normalized strength value with standardized unit")
    normalized_dosage_form: str | None = Field(default=None, description="Standardized dosage form")
    normalized_route: str | None = Field(default=None, description="Standardized administration route")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Terminology match confidence score")
    provider: str = Field(description="Terminology provider identifier")
    provider_version: str | None = Field(default=None, description="Provider dataset/engine version")


class TerminologyLookupResult(BaseModel):
    """Result of querying a medication terminology provider."""
    model_config = ConfigDict(frozen=True)

    status: NormalizationStatus
    concept: NormalizedConcept | None = None
    potential_matches: list[str] = Field(default_factory=list, description="Candidate matches if AMBIGUOUS")
    error_code: str | None = Field(default=None, description="Internal error code if FAILED")
    error_message: str | None = Field(default=None, description="Sanitized error description")
    disclaimer: str = (
        "Terminology lookup standardizes medication representations only. "
        "It does not evaluate drug safety, contraindications, allergies, or clinical appropriateness."
    )


@runtime_checkable
class MedicationTerminologyProvider(Protocol):
    """Abstract interface for medication terminology lookups and normalization."""

    async def normalize(self, medication_input: RawMedicationInput) -> TerminologyLookupResult:
        """Query terminology database to normalize raw medication input."""
        ...


@runtime_checkable
class MedicationSafetyProvider(Protocol):
    """Future placeholder interface for Phase 7 clinical medication safety checking.

    CRITICAL ARCHITECTURAL BOUNDARY:
    Phase 6 DOES NOT implement medication safety checks (interactions, allergies, contraindications,
    clinical dosing validation, or duplicate therapy decisions).
    This interface serves as an architectural placeholder for Phase 7 integration.
    """
    pass
