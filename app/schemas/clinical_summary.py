"""Clinical summary schema — controlled projection of patient clinical context.

The clinical summary is a deliberate, structured projection.

It intentionally includes:
  - Basic patient profile (demographics)
  - Active/known conditions from clinical history
  - Active allergies
  - Recent vitals (configurable window)
  - Active encounter context

It intentionally EXCLUDES (pending future phases):
  - Prescriptions
  - Medications
  - Documents
  - Discharge summaries
  - Care plans
  - AI/triage results

IMPORTANT: This schema must not be used in log statements. It contains PHI.
Do not auto-expand it to include every available domain as new domains are added.
Summary content should require a conscious decision per domain.
"""

from datetime import date, datetime

from app.schemas.allergy import AllergyResponse
from app.schemas.clinical_history import ClinicalHistoryResponse
from app.schemas.encounter import EncounterResponse
from app.schemas.patient import BiologicalSex, PatientStatus
from app.schemas.vital import VitalResponse
from pydantic import BaseModel, Field


class PatientDemographics(BaseModel):
    """Minimal demographics projection for clinical summary."""
    id: str
    first_name: str
    last_name: str
    date_of_birth: date
    sex: BiologicalSex
    preferred_language: str | None = None
    status: PatientStatus


class ClinicalSummaryResponse(BaseModel):
    """Controlled clinical summary of a patient's current health context.

    Only includes domains implemented in Phase 4.
    Future domains (medications, prescriptions, care plans) are NOT included
    until those domains are implemented and explicitly added here.
    """
    patient: PatientDemographics
    active_conditions: list[ClinicalHistoryResponse] = Field(
        default_factory=list,
        description="Active or unresolved clinical history entries",
    )
    known_allergies: list[AllergyResponse] = Field(
        default_factory=list,
        description="Active allergy records",
    )
    recent_vitals: list[VitalResponse] = Field(
        default_factory=list,
        description="Most recent vital measurements (one per type)",
    )
    active_encounters: list[EncounterResponse] = Field(
        default_factory=list,
        description="Encounters in PLANNED or IN_PROGRESS status",
    )
    summary_generated_at: datetime = Field(
        description="UTC timestamp when this summary was assembled"
    )

    # Explicitly declare excluded domains so API consumers understand scope
    _excluded_domains: list[str] = [
        "medications",
        "prescriptions",
        "care_plans",
        "documents",
        "discharge_summaries",
    ]
