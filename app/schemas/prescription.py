"""Pydantic schemas for prescription entities, items, and normalization."""

from datetime import date, datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.medication import NormalizedMedicationInfo


class PrescriptionSource(str, Enum):
    """Source origin of the prescription."""
    PATIENT_UPLOAD = "PATIENT_UPLOAD"
    DOCTOR_UPLOAD = "DOCTOR_UPLOAD"
    CLINIC_UPLOAD = "CLINIC_UPLOAD"
    IMPORTED = "IMPORTED"
    SYSTEM = "SYSTEM"


class PrescriptionStatus(str, Enum):
    """Lifecycle state of the prescription."""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    DISCONTINUED = "DISCONTINUED"
    CANCELLED = "CANCELLED"


class NormalizationStatus(str, Enum):
    """Terminology normalization outcome states."""
    PENDING = "PENDING"
    MATCHED = "MATCHED"
    AMBIGUOUS = "AMBIGUOUS"
    UNMATCHED = "UNMATCHED"
    FAILED = "FAILED"


class PrescriptionItemCreate(BaseModel):
    """Payload to add a medication item to a prescription."""
    drug_name_raw: str = Field(min_length=1, max_length=255, description="Raw medication name as extracted or entered")
    strength_raw: str | None = Field(default=None, max_length=100, description="Raw strength (e.g. '500 mg', '0.5 g')")
    dosage_form_raw: str | None = Field(default=None, max_length=100, description="Raw dosage form (e.g. 'tablet', 'cap')")
    dose_raw: str | None = Field(default=None, max_length=100, description="Raw dose (e.g. '1 tablet')")
    route_raw: str | None = Field(default=None, max_length=100, description="Raw administration route (e.g. 'oral')")
    frequency_raw: str | None = Field(default=None, max_length=100, description="Raw frequency (e.g. 'twice daily', '1-0-1')")
    duration_raw: str | None = Field(default=None, max_length=100, description="Raw duration (e.g. '5 days')")
    quantity_raw: str | None = Field(default=None, max_length=100, description="Raw quantity (e.g. '10 tablets')")
    instructions_raw: str | None = Field(default=None, max_length=500, description="Raw instructions (e.g. 'after food')")
    extraction_reference: str | None = Field(default=None, description="Optional reference to Phase 5 extraction field")


class PrescriptionItemResponse(BaseModel):
    """Prescription item output including normalization results."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    prescription_id: str
    drug_name_raw: str
    strength_raw: str | None = None
    dosage_form_raw: str | None = None
    dose_raw: str | None = None
    route_raw: str | None = None
    frequency_raw: str | None = None
    duration_raw: str | None = None
    quantity_raw: str | None = None
    instructions_raw: str | None = None
    normalized_medication_id: str | None = None
    normalization_status: NormalizationStatus = NormalizationStatus.PENDING
    normalized_concept: NormalizedMedicationInfo | None = None
    extraction_reference: str | None = None
    created_at: datetime
    updated_at: datetime


class PrescriptionCreate(BaseModel):
    """Payload to create a prescription."""
    document_id: str | None = Field(default=None, description="Optional Phase 5 medical document ID")
    extraction_id: str | None = Field(default=None, description="Optional Phase 5 document extraction ID")
    prescriber_reference: str | None = Field(default=None, max_length=255, description="Prescriber name or identifier")
    prescription_date: datetime | date | None = Field(default=None, description="Date prescription was written")
    source: PrescriptionSource = Field(default=PrescriptionSource.PATIENT_UPLOAD)
    items: list[PrescriptionItemCreate] = Field(default_factory=list, description="Prescription medication items")


class PrescriptionResponse(BaseModel):
    """Prescription output with items and metadata."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    document_id: str | None = None
    extraction_id: str | None = None
    prescriber_reference: str | None = None
    prescription_date: datetime | None = None
    source: PrescriptionSource
    status: PrescriptionStatus
    items: list[PrescriptionItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class PrescriptionListResponse(BaseModel):
    """Paginated list of prescriptions."""
    items: list[PrescriptionResponse]
    total: int
    skip: int
    limit: int


class PrescriptionNormalizeResponse(BaseModel):
    """Result of normalizing a prescription's items."""
    prescription_id: str
    normalized_items_count: int
    matched_count: int
    ambiguous_count: int
    unmatched_count: int
    failed_count: int
    items: list[PrescriptionItemResponse]
    disclaimer: str = (
        "Medication normalization standardizes terminology concepts. "
        "It does not constitute medication safety validation, dosing appropriateness, "
        "allergy conflict evaluation, or clinical decision support."
    )
