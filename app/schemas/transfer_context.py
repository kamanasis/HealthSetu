"""Transfer Clinical Context Schemas (Phase 12).

Defines structured clinical context sharing payload attached to transfer requests.
Enforces least-privilege information sharing — avoids dumping whole medical history.
"""

from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class TransferClinicalContext(BaseModel):
    """Authorized clinical context snapshot attached to a patient transfer."""
    model_config = ConfigDict(from_attributes=True)

    transfer_id: str
    patient_id: str
    encounter_id: str | None = None
    urgency_level: str | None = Field(default=None, description="Triage urgency classification if available")
    triage_notes: str | None = Field(default=None, description="Concise triage assessment summary")
    primary_symptoms: list[str] = Field(default_factory=list, description="Presenting symptoms")
    known_allergies: list[str] = Field(default_factory=list, description="Documented active allergies")
    active_medications: list[str] = Field(default_factory=list, description="Active medication summaries")
    latest_vitals: dict[str, Any] | None = Field(default=None, description="Most recent vital signs recording")
    sbar_id: str | None = Field(default=None, description="SBAR report identifier if attached")
    sbar_situation: str | None = None
    sbar_background: str | None = None
    sbar_assessment: str | None = None
    sbar_recommendation: str | None = None
    consent_id: str | None = Field(default=None, description="Consent authorization record")
    shared_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    authorized_by: str = Field(description="Clinician/actor authorizing context sharing")
