"""Healthcare Department schemas (Phase 11).

Pydantic v2 domain schemas and response envelopes for hospital/clinic departments.
"""

from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class DepartmentStatus(str, Enum):
    """Operational status of a healthcare department."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class DepartmentRecord(BaseModel):
    """Domain model / database contract representation for a department."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    facility_id: str
    organization_id: str
    name: str
    code: str | None = None
    status: DepartmentStatus = DepartmentStatus.ACTIVE
    description: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DepartmentResponse(BaseModel):
    """Public API response schema for a department."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    facility_id: str
    organization_id: str
    name: str
    code: str | None = None
    status: DepartmentStatus
    description: str | None = None
    created_at: datetime
    updated_at: datetime


class DepartmentListResponse(BaseModel):
    """Department list response for a facility."""
    items: list[DepartmentResponse]
    total: int
