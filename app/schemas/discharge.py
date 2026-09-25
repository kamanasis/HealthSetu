"""Pydantic schemas for Discharge Instructions and Clinical Verification (Phase 9).

Strict Clinical Boundaries:
- Distinguishes extracted instructions (unverified) from clinician-verified orders.
- Documented discharge diagnosis is attributed to the medical document/clinician,
  NOT an autonomous AI diagnosis.
- Verifications are restricted to licensed clinicians.
"""

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
import uuid


DISCHARGE_CLINICAL_DISCLAIMER: str = (
    "DISCLAIMER: Extracted discharge instructions are preliminary until reviewed and verified "
    "by an authorized clinician. In the event of acute worsening or medical emergency, "
    "seek emergency medical care immediately."
)


class DischargeVerificationStatus(str, Enum):
    """Lifecycle verification states for extracted discharge instructions."""

    EXTRACTED = "EXTRACTED"
    UNVERIFIED = "UNVERIFIED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    VERIFIED = "VERIFIED"
    CORRECTED = "CORRECTED"
    REJECTED = "REJECTED"


class DischargeMedicationItem(BaseModel):
    """Structured discharge medication instructions."""

    drug_name: str = Field(description="Name of medication")
    dosage: str | None = None
    frequency: str | None = None
    duration: str | None = None
    instructions: str | None = None
    is_new: bool = False
    is_changed: bool = False
    discontinued: bool = False


class DischargeActivityInstruction(BaseModel):
    """Physical activity restrictions and mobilization instructions."""

    category: str = Field(description="Activity category e.g., 'REST', 'MOBILIZATION', 'LIFTING_RESTRICTION'")
    description: str = Field(description="Specific instructions (e.g., 'No lifting > 5kg for 2 weeks')")
    duration_days: int | None = None


class DischargeDietInstruction(BaseModel):
    """Nutritional and dietary guidance."""

    dietary_type: str = Field(description="e.g., 'LOW_SODIUM', 'DIABETIC', 'SOFT_FOOD', 'REGULAR'")
    restrictions: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class DischargeWoundCareInstruction(BaseModel):
    """Wound management and hygiene guidance."""

    site: str | None = None
    dressing_instructions: str
    cleaning_frequency: str | None = None
    warning_signs: list[str] = Field(default_factory=list)


class DischargeWarningSign(BaseModel):
    """Red flag symptoms that require immediate clinical attention."""

    symptom: str = Field(description="Red flag symptom (e.g., 'fever > 38.5C', 'sudden wound discharge')")
    action_required: str = Field(description="Action e.g., 'Call emergency services or proceed to nearest hospital'")
    severity: str = "URGENT"


class DischargeFollowUpItem(BaseModel):
    """Follow-up appointments, lab tests, and clinical reviews."""

    provider_or_specialty: str = Field(description="Physician or clinic specialty")
    recommended_timeframe: str = Field(description="e.g., 'Within 7-10 days', '2 weeks post-discharge'")
    purpose: str = Field(description="Purpose (e.g., 'Suture removal and surgical site review')")
    scheduled_date: date | None = None


class DischargeExtractionRequest(BaseModel):
    """Request payload to extract discharge instructions from a processed document."""

    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(description="Phase 5 processed document ID containing the discharge summary")
    encounter_id: str | None = Field(default=None, description="Optional associated clinical encounter ID")


class DischargeVerificationUpdate(BaseModel):
    """Clinician verification and correction payload."""

    model_config = ConfigDict(extra="forbid")

    status: DischargeVerificationStatus = Field(
        default=DischargeVerificationStatus.VERIFIED,
        description="Verification state ('VERIFIED', 'CORRECTED', 'REJECTED')",
    )
    discharge_diagnoses: list[str] | None = None
    medications: list[DischargeMedicationItem] | None = None
    activity_instructions: list[DischargeActivityInstruction] | None = None
    diet_instructions: list[DischargeDietInstruction] | None = None
    wound_care_instructions: list[DischargeWoundCareInstruction] | None = None
    warning_signs: list[DischargeWarningSign] | None = None
    follow_up_instructions: list[DischargeFollowUpItem] | None = None
    clinician_notes: str | None = Field(default=None, max_length=1000)


class DischargeInstructionRecord(BaseModel):
    """Immutable discharge instruction record with full provenance and verification trail."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    document_id: str
    encounter_id: str | None = None
    extraction_id: str | None = None
    verification_status: DischargeVerificationStatus = DischargeVerificationStatus.EXTRACTED
    discharge_diagnoses: list[str] = Field(default_factory=list)
    medications: list[DischargeMedicationItem] = Field(default_factory=list)
    activity_instructions: list[DischargeActivityInstruction] = Field(default_factory=list)
    diet_instructions: list[DischargeDietInstruction] = Field(default_factory=list)
    wound_care_instructions: list[DischargeWoundCareInstruction] = Field(default_factory=list)
    warning_signs: list[DischargeWarningSign] = Field(default_factory=list)
    follow_up_instructions: list[DischargeFollowUpItem] = Field(default_factory=list)
    clinician_notes: str | None = None
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    extractor_version: str = "1.0.0"
    verified_by: str | None = None
    verified_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DischargeInstructionResponse(BaseModel):
    """API response for discharge instructions."""

    discharge_id: str
    patient_id: str
    document_id: str
    encounter_id: str | None = None
    verification_status: DischargeVerificationStatus
    discharge_diagnoses: list[str]
    medications: list[DischargeMedicationItem]
    activity_instructions: list[DischargeActivityInstruction]
    diet_instructions: list[DischargeDietInstruction]
    wound_care_instructions: list[DischargeWoundCareInstruction]
    warning_signs: list[DischargeWarningSign]
    follow_up_instructions: list[DischargeFollowUpItem]
    clinician_notes: str | None = None
    verified_by: str | None = None
    verified_at: datetime | None = None
    disclaimer: str = DISCHARGE_CLINICAL_DISCLAIMER
    created_at: datetime
    updated_at: datetime
