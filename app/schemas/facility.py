"""Healthcare Facility schemas (Phase 11).

Pydantic v2 domain schemas and response envelopes for healthcare facilities.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.organization import DataProvenance


class FacilityType(str, Enum):
    """Healthcare facility classification types."""
    HOSPITAL = "HOSPITAL"
    CLINIC = "CLINIC"
    URGENT_CARE = "URGENT_CARE"
    EMERGENCY_DEPARTMENT = "EMERGENCY_DEPARTMENT"
    DIAGNOSTIC_CENTER = "DIAGNOSTIC_CENTER"
    LABORATORY = "LABORATORY"
    PHARMACY = "PHARMACY"
    SPECIALTY_CENTER = "SPECIALTY_CENTER"
    OTHER = "OTHER"


class FacilityStatus(str, Enum):
    """Operational status of a healthcare facility."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    PENDING = "PENDING"
    ARCHIVED = "ARCHIVED"


class FacilityRecord(BaseModel):
    """Domain model / database contract representation for a facility."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    facility_type: FacilityType = FacilityType.HOSPITAL
    status: FacilityStatus = FacilityStatus.ACTIVE
    identifier: str | None = None
    description: str | None = None
    email: str | None = None
    phone: str | None = None
    address: dict[str, Any] | None = None
    operational_metadata: dict[str, Any] | None = None
    provenance: DataProvenance = Field(default_factory=DataProvenance)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FacilityResponse(BaseModel):
    """Public API response schema for a healthcare facility."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    facility_type: FacilityType
    status: FacilityStatus
    identifier: str | None = None
    description: str | None = None
    email: str | None = None
    phone: str | None = None
    address: dict[str, Any] | None = None
    operational_metadata: dict[str, Any] | None = None
    provenance: DataProvenance | None = None
    created_at: datetime
    updated_at: datetime


class FacilityListResponse(BaseModel):
    """Paginated facility list response."""
    items: list[FacilityResponse]
    total: int
    limit: int
    offset: int


class ClinicianFacilityMembershipRecord(BaseModel):
    """Domain record representing a clinician's membership/privilege in a facility."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    clinician_id: str
    facility_id: str
    organization_id: str
    role_title: str | None = "Physician"
    status: str = "ACTIVE"
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
