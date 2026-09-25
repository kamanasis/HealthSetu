"""Clinician Organization Context schemas (Phase 11).

Provides schemas for organization context accessible to an authenticated clinician.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.schemas.organization import OrganizationResponse, OrganizationStatus
from app.schemas.facility import FacilityResponse


class ClinicianOrganizationRelationship(BaseModel):
    """Details of clinician's affiliation with an organization."""
    model_config = ConfigDict(from_attributes=True)

    clinician_id: str
    organization_id: str
    role_title: str | None = None
    status: str = "ACTIVE"
    joined_at: datetime


class ClinicianOrganizationContextResponse(BaseModel):
    """Consolidated organization context for an authenticated clinician."""
    model_config = ConfigDict(from_attributes=True)

    organization: OrganizationResponse
    organization_status: OrganizationStatus
    clinician_relationship: ClinicianOrganizationRelationship
    accessible_facilities: list[FacilityResponse]
