"""Clinician Facility Context schemas (Phase 11).

Provides schemas for facility context accessible to an authenticated clinician.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.schemas.organization import OrganizationResponse
from app.schemas.facility import FacilityResponse, FacilityStatus
from app.schemas.department import DepartmentResponse


class ClinicianFacilityRelationship(BaseModel):
    """Details of clinician's affiliation with a facility."""
    model_config = ConfigDict(from_attributes=True)

    clinician_id: str
    facility_id: str
    organization_id: str
    role_title: str | None = None
    status: str = "ACTIVE"
    joined_at: datetime


class ClinicianFacilityContextResponse(BaseModel):
    """Consolidated facility context for an authenticated clinician."""
    model_config = ConfigDict(from_attributes=True)

    facility: FacilityResponse
    organization: OrganizationResponse
    departments: list[DepartmentResponse]
    clinician_relationship: ClinicianFacilityRelationship
    facility_status: FacilityStatus
