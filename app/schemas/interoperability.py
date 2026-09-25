"""Interoperability & Healthcare Data Exchange Schemas (Phase 13).

Defines standards-based data models, validation structures, and payload envelopes
for FHIR/HL7 import/export operations, external identity tracking, and clinical
verification boundaries.

Critical boundaries:
- Interoperability != Clinical Decision Support
- External Data != Verified HealthSetu Clinical Data
- Import != Overwrite Verified Clinical Records
- Patient Matching != Guessing Identity
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid
from pydantic import BaseModel, ConfigDict, Field, computed_field


# ---------------------------------------------------------------------------
# Interoperability Standards & Formats
# ---------------------------------------------------------------------------

class InteroperabilityFormat(str, Enum):
    """Supported healthcare data interoperability formats."""

    FHIR = "FHIR"
    HL7 = "HL7"


class FHIRVersion(str, Enum):
    """Supported HL7 FHIR specification versions."""

    R4 = "R4"


class SupportedFHIRResourceType(str, Enum):
    """FHIR R4 resource types safely mappable to HealthSetu domain entities."""

    PATIENT = "Patient"
    ENCOUNTER = "Encounter"
    OBSERVATION = "Observation"
    ALLERGY_INTOLERANCE = "AllergyIntolerance"
    MEDICATION_REQUEST = "MedicationRequest"
    MEDICATION = "Medication"
    DOCUMENT_REFERENCE = "DocumentReference"
    CONDITION = "Condition"


class ExportScope(str, Enum):
    """Least-privilege export scopes for patient clinical data extraction."""

    PATIENT_BASIC = "PATIENT_BASIC"
    ENCOUNTER = "ENCOUNTER"
    MEDICATIONS = "MEDICATIONS"
    ALLERGIES = "ALLERGIES"
    VITALS = "VITALS"
    DOCUMENTS = "DOCUMENTS"
    CLINICAL_SUMMARY = "CLINICAL_SUMMARY"
    FULL_AUTHORIZED_RECORD = "FULL_AUTHORIZED_RECORD"


class ImportStatus(str, Enum):
    """Lifecycle state machine for imported healthcare resources."""

    RECEIVED = "RECEIVED"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    MAPPING = "MAPPING"
    MAPPED = "MAPPED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    IMPORTED = "IMPORTED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class ExportStatus(str, Enum):
    """Lifecycle state machine for data export operations."""

    REQUESTED = "REQUESTED"
    AUTHORIZED = "AUTHORIZED"
    PREPARING = "PREPARING"
    VALIDATED = "VALIDATED"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class VerificationStatus(str, Enum):
    """Clinical verification status of imported external data."""

    UNVERIFIED = "UNVERIFIED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


# ---------------------------------------------------------------------------
# External Identifier Mapping
# ---------------------------------------------------------------------------

class ExternalIdentifierMapping(BaseModel):
    """Deterministic mapping between external healthcare system IDs and HealthSetu IDs."""

    id: str = Field(default_factory=lambda: f"map-{uuid.uuid4().hex[:12]}")
    source_system: str = Field(description="Identifier for source system (e.g. 'hospital-a', 'epic-node-1')")
    external_patient_id: str = Field(description="Patient identifier in external system")
    healthsetu_patient_id: str = Field(description="Canonical HealthSetu patient ID")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Import Request & Response Models
# ---------------------------------------------------------------------------

class InteroperabilityImportRequest(BaseModel):
    """Request payload to submit external healthcare data for import."""

    model_config = ConfigDict(extra="forbid")

    source_system: str = Field(min_length=1, max_length=100, description="Authoritative source system identifier")
    source_organization_id: str | None = Field(default=None, description="Optional Phase 11 Organization ID")
    format: InteroperabilityFormat = Field(default=InteroperabilityFormat.FHIR, description="Interoperability standard")
    format_version: str | None = Field(default="R4", description="Standard specification version")
    resource_type: str = Field(min_length=1, max_length=60, description="Resource type (e.g. 'Patient', 'Observation')")
    external_resource_id: str = Field(min_length=1, max_length=100, description="ID of resource in source system")
    external_patient_id: str | None = Field(default=None, description="Patient identifier in external system")
    healthsetu_patient_id: str | None = Field(default=None, description="Target HealthSetu patient ID if known")
    payload: dict[str, Any] = Field(description="Raw external resource JSON payload")


class InteroperabilityImportRecord(BaseModel):
    """Persisted import tracking record with source metadata and provenance."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: f"imp-{uuid.uuid4().hex[:12]}")
    source_system: str
    source_organization_id: str | None = None
    format: InteroperabilityFormat
    format_version: str
    resource_type: str
    external_resource_id: str
    external_patient_id: str | None = None
    healthsetu_patient_id: str | None = None
    status: ImportStatus
    verification_status: VerificationStatus = VerificationStatus.REVIEW_REQUIRED
    raw_payload: dict[str, Any]
    mapped_data: dict[str, Any] | None = None
    mapped_entity_type: str | None = None
    mapped_entity_id: str | None = None
    validation_errors: list[str] = Field(default_factory=list)
    imported_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @computed_field
    @property
    def provenance(self) -> dict[str, Any]:
        return {
            "source_system": self.source_system,
            "source_organization_id": self.source_organization_id,
            "external_resource_id": self.external_resource_id,
            "external_patient_id": self.external_patient_id,
        }


class InteroperabilityImportResponse(BaseModel):
    """API response for an import operation without leaking full raw payloads."""

    model_config = ConfigDict(from_attributes=True)

    import_id: str
    source_system: str
    resource_type: str
    external_resource_id: str
    healthsetu_patient_id: str | None = None
    patient_id: str | None = None
    status: ImportStatus
    verification_status: VerificationStatus
    message: str | None = None
    validation_errors: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Export Request & Response Models
# ---------------------------------------------------------------------------

class InteroperabilityExportRequest(BaseModel):
    """Request payload to initiate authorized patient data export."""

    model_config = ConfigDict(extra="forbid")

    patient_id: str = Field(description="Canonical HealthSetu patient ID")
    format: InteroperabilityFormat = Field(default=InteroperabilityFormat.FHIR, description="Export format")
    format_version: str | None = Field(default="R4", description="Specification version")
    scope: ExportScope = Field(default=ExportScope.FULL_AUTHORIZED_RECORD, description="Least-privilege export scope")
    resource_types: list[str] | None = Field(default=None, description="Optional explicit resource type filter")
    target_system: str = Field(min_length=1, max_length=100, description="Target recipient system or exchange network")
    target_organization_id: str | None = Field(default=None, description="Optional target Organization ID")
    consent_id: str | None = Field(default=None, description="Optional explicit consent authorization ID")


class PatientExportRequest(BaseModel):
    """Request payload for patient-specific export endpoint."""

    model_config = ConfigDict(extra="forbid")

    format: InteroperabilityFormat = Field(default=InteroperabilityFormat.FHIR)
    format_version: str | None = Field(default="R4")
    scope: ExportScope = Field(default=ExportScope.FULL_AUTHORIZED_RECORD)
    resource_types: list[str] | None = Field(default=None)
    target_system: str = Field(default="EXTERNAL_HEALTHCARE_SYSTEM", min_length=1, max_length=100)
    target_organization_id: str | None = None
    consent_id: str | None = None


class InteroperabilityExportRecord(BaseModel):
    """Persisted export tracking record with output payload and provenance."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: f"exp-{uuid.uuid4().hex[:12]}")
    patient_id: str
    target_system: str
    target_organization_id: str | None = None
    format: InteroperabilityFormat
    format_version: str
    scope: ExportScope
    resource_types: list[str] = Field(default_factory=list)
    status: ExportStatus
    exported_bundle: dict[str, Any]
    exported_count: int
    exported_by: str
    consent_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InteroperabilityExportResponse(BaseModel):
    """API response for a patient data export operation."""

    model_config = ConfigDict(from_attributes=True)

    export_id: str
    patient_id: str
    target_system: str
    format: InteroperabilityFormat
    format_version: str = "R4"
    scope: ExportScope
    status: ExportStatus
    resource_count: int = 0
    delivered_bundle_id: str | None = None
    message: str | None = None
    data: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
