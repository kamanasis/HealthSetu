"""Healthcare Organization schemas (Phase 11).

Pydantic v2 domain schemas and response envelopes for healthcare organizations.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class OrganizationType(str, Enum):
    """Healthcare organization classification types."""
    HOSPITAL = "HOSPITAL"
    CLINIC = "CLINIC"
    DIAGNOSTIC_CENTER = "DIAGNOSTIC_CENTER"
    PHARMACY = "PHARMACY"
    LABORATORY = "LABORATORY"
    HEALTHCARE_NETWORK = "HEALTHCARE_NETWORK"
    OTHER = "OTHER"


class OrganizationStatus(str, Enum):
    """Operational status of a healthcare organization."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    PENDING = "PENDING"
    ARCHIVED = "ARCHIVED"


class DataProvenanceSource(str, Enum):
    """Data provenance origin of organization/facility records."""
    INTERNAL_DATABASE = "INTERNAL_DATABASE"
    HEALTHCARE_DIRECTORY = "HEALTHCARE_DIRECTORY"
    IMPORTED = "IMPORTED"
    MANUAL = "MANUAL"


class DataProvenance(BaseModel):
    """Provenance tracking metadata for organizational data."""
    model_config = ConfigDict(from_attributes=True)

    source: DataProvenanceSource = DataProvenanceSource.INTERNAL_DATABASE
    provider: str | None = None
    provider_version: str | None = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OrganizationRecord(BaseModel):
    """Domain model / database contract representation for an organization."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    organization_type: OrganizationType = OrganizationType.HOSPITAL
    status: OrganizationStatus = OrganizationStatus.ACTIVE
    identifier: str | None = None
    description: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    address: dict[str, Any] | None = None
    provenance: DataProvenance = Field(default_factory=DataProvenance)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OrganizationResponse(BaseModel):
    """Public API response schema for a healthcare organization."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    organization_type: OrganizationType
    status: OrganizationStatus
    identifier: str | None = None
    description: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    address: dict[str, Any] | None = None
    provenance: DataProvenance | None = None
    created_at: datetime
    updated_at: datetime


class OrganizationListResponse(BaseModel):
    """Paginated organization list response."""
    items: list[OrganizationResponse]
    total: int
    limit: int
    offset: int


class ClinicianOrganizationMembershipRecord(BaseModel):
    """Domain record representing a clinician's membership in an organization."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    clinician_id: str
    organization_id: str
    role_title: str | None = "Physician"
    status: str = "ACTIVE"
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
