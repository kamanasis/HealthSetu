"""Pydantic schemas and enums for medical document handling and extraction."""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class DocumentType(str, Enum):
    """Categorization of medical documents."""
    PRESCRIPTION = "PRESCRIPTION"
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY"
    LAB_REPORT = "LAB_REPORT"
    MEDICAL_REPORT = "MEDICAL_REPORT"
    CLINICAL_NOTE = "CLINICAL_NOTE"
    IDENTITY_DOCUMENT = "IDENTITY_DOCUMENT"
    OTHER_MEDICAL_DOCUMENT = "OTHER_MEDICAL_DOCUMENT"


class DocumentSource(str, Enum):
    """Provenance and ingestion source of a document."""
    PATIENT_UPLOAD = "PATIENT_UPLOAD"
    CLINIC_UPLOAD = "CLINIC_UPLOAD"
    DOCTOR_UPLOAD = "DOCTOR_UPLOAD"
    IMPORTED = "IMPORTED"
    SYSTEM = "SYSTEM"


class DocumentLifecycleState(str, Enum):
    """Overall document lifecycle states."""
    UPLOADING = "UPLOADING"
    UPLOADED = "UPLOADED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    EXTRACTED = "EXTRACTED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class ProcessingStatus(str, Enum):
    """Status of background document processing / extraction job."""
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DocumentResponse(BaseModel):
    """Metadata response for a medical document."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique document ID (UUID)")
    patient_id: str = Field(..., description="Canonical patient ID")
    uploader_id: str = Field(..., description="User ID of the uploader")
    document_type: DocumentType = Field(..., description="Type/category of medical document")
    source: DocumentSource = Field(..., description="Provenance source of document")
    filename: str = Field(..., description="Sanitized client filename")
    mime_type: str = Field(..., description="MIME content type")
    size_bytes: int = Field(..., description="File size in bytes")
    checksum_sha256: str = Field(..., description="SHA-256 cryptographic checksum")
    lifecycle_state: DocumentLifecycleState = Field(..., description="Document lifecycle state")
    processing_status: ProcessingStatus = Field(..., description="Extraction processing status")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")
    is_archived: bool = Field(default=False, description="Archive / soft-delete flag")


class DocumentListResponse(BaseModel):
    """Paginated list of document metadata records."""
    items: list[DocumentResponse]
    total: int


class DocumentDownloadResponse(BaseModel):
    """Response containing secure, short-lived download authorization URL."""
    document_id: str
    download_url: str
    expires_in_seconds: int
    filename: str
    mime_type: str


class StructuredExtractionField(BaseModel):
    """An individual extracted structured field from document text."""
    field_name: str
    raw_value: str
    confidence: float | None = Field(default=None, description="OCR/extraction confidence score (0.0 - 1.0)")
    page_number: int | None = Field(default=None, description="Page index where field was found (1-indexed)")


class ExtractionResultResponse(BaseModel):
    """Structured extraction result and provenance metadata."""
    extraction_id: str
    document_id: str
    processor: str
    processor_version: str
    extracted_text: str
    language: str
    page_count: int
    structured_fields: list[StructuredExtractionField] = Field(default_factory=list)
    created_at: datetime
    disclaimer: str = Field(
        default="Extracted content is machine-generated for clinical review only. It does NOT constitute verified medical diagnosis or clinical verification.",
        description="Clinical safety boundary disclaimer",
    )


class DocumentRetryResponse(BaseModel):
    """Response returned upon re-enqueueing a document for processing."""
    document_id: str
    job_id: str
    processing_status: ProcessingStatus
    retry_count: int
    message: str
