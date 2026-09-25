"""Pydantic schemas for medication domain, normalization results, and patient medication records."""

from datetime import date, datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class PatientMedicationStatus(str, Enum):
    """Lifecycle / clinical states for patient medications."""
    PRESCRIBED = "PRESCRIBED"
    REPORTED = "REPORTED"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    HISTORICAL = "HISTORICAL"
    UNKNOWN = "UNKNOWN"


class VerificationStatus(str, Enum):
    """Human and clinical verification states."""
    EXTRACTED = "EXTRACTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    VERIFIED = "VERIFIED"
    CORRECTED = "CORRECTED"
    REJECTED = "REJECTED"


class MedicationSource(str, Enum):
    """Origin of the patient medication entry."""
    PRESCRIPTION = "PRESCRIPTION"
    PATIENT_REPORTED = "PATIENT_REPORTED"
    DOCTOR_ENTERED = "DOCTOR_ENTERED"
    CLINIC_ENTERED = "CLINIC_ENTERED"
    IMPORTED = "IMPORTED"
    SYSTEM = "SYSTEM"


class NormalizedMedicationInfo(BaseModel):
    """Structured terminology lookup and canonical representation."""
    model_config = ConfigDict(frozen=True)

    medication_id: str | None = Field(default=None, description="Internal medication record ID")
    canonical_name: str = Field(description="Canonical normalized medication name")
    generic_name: str | None = Field(default=None, description="Generic ingredient name")
    brand_name: str | None = Field(default=None, description="Brand name if specified in source")
    terminology_system: str = Field(description="Terminology system (e.g. RXNORM, LOCAL_MOCK)")
    terminology_code: str = Field(description="Terminology concept identifier/code")
    normalized_strength: str | None = Field(default=None, description="Standardized strength unit")
    normalized_dosage_form: str | None = Field(default=None, description="Standardized dosage form")
    normalized_route: str | None = Field(default=None, description="Standardized administration route")
    provider: str = Field(description="Terminology provider name")
    provider_version: str | None = Field(default=None, description="Terminology provider version")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Terminology match confidence")


class PatientMedicationResponse(BaseModel):
    """Complete patient medication record with provenance and status."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    status: PatientMedicationStatus
    verification_status: VerificationStatus
    drug_name_raw: str
    strength_raw: str | None = None
    dosage_form_raw: str | None = None
    route_raw: str | None = None
    frequency_raw: str | None = None
    duration_raw: str | None = None
    instructions_raw: str | None = None
    normalized_medication_id: str | None = None
    normalized_info: NormalizedMedicationInfo | None = None
    source: MedicationSource
    # Provenance chain
    document_id: str | None = None
    extraction_id: str | None = None
    prescription_id: str | None = None
    prescription_item_id: str | None = None
    # Duplicate flagging (data level only)
    potential_duplicate: bool = False
    # Correction history
    is_corrected: bool = False
    original_raw_value: str | None = None
    corrected_raw_value: str | None = None
    corrected_by: str | None = None
    corrected_at: datetime | None = None
    # Timing
    start_date: datetime | date | None = None
    end_date: datetime | date | None = None
    created_at: datetime
    updated_at: datetime
    disclaimer: str = (
        "Patient medication records represent recorded or reported medication data. "
        "They do not constitute clinical safety verification, dosing appropriateness, "
        "or active compliance assurance."
    )


class PatientMedicationListResponse(BaseModel):
    """Paginated list of patient medications."""
    items: list[PatientMedicationResponse]
    total: int
    skip: int
    limit: int


class MedicationStatusUpdateRequest(BaseModel):
    """Request payload for updating medication status (e.g. PRESCRIBED -> ACTIVE / INACTIVE)."""
    status: PatientMedicationStatus
    reason: str | None = Field(default=None, max_length=500)


class MedicationCorrectionRequest(BaseModel):
    """Request payload for correcting raw extracted medication data."""
    drug_name: str = Field(min_length=1, max_length=255, description="Corrected drug name")
    strength: str | None = Field(default=None, max_length=100)
    dosage_form: str | None = Field(default=None, max_length=100)
    route: str | None = Field(default=None, max_length=100)
    frequency: str | None = Field(default=None, max_length=100)
    duration: str | None = Field(default=None, max_length=100)
    instructions: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=500)
