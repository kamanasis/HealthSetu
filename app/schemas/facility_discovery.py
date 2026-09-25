"""Facility Discovery Schemas (Phase 12).

Defines query parameters, filter structures, and response envelopes for facility discovery.
"""

from typing import Annotated
from pydantic import BaseModel, Field

from app.schemas.facility_result import FacilityDiscoveryResult


class FacilityDiscoveryQueryParams(BaseModel):
    """Query parameters for discovering healthcare facilities."""
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0, description="Caller latitude coordinate")
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0, description="Caller longitude coordinate")
    radius_km: float | None = Field(default=None, gt=0, description="Proximity search radius in kilometers")
    facility_type: str | None = Field(default=None, description="Filter by facility type (e.g. HOSPITAL, CLINIC)")
    required_service: str | None = Field(default=None, description="Filter by required service (e.g. EMERGENCY_CARE, CARDIOLOGY)")
    required_capability: str | None = Field(default=None, description="Filter by required capability (e.g. ICU, TRAUMA_CENTER)")
    organization_id: str | None = Field(default=None, description="Filter by parent organization ID")
    limit: int = Field(default=50, ge=1, le=100, description="Number of results to return")
    offset: int = Field(default=0, ge=0, description="Result pagination offset")


class FacilityDiscoveryResponse(BaseModel):
    """Discovery search results response envelope."""
    items: list[FacilityDiscoveryResult]
    total: int
    limit: int
    offset: int
    origin_latitude: float | None = None
    origin_longitude: float | None = None
    radius_km: float | None = None
