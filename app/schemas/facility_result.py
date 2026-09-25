"""Facility Result Schema (Phase 12).

Defines structured discovery results suitable for patient-facing facility discovery.
Critical boundary: No real-time bed availability claims, quality rankings, or diagnostic claims.
"""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.organization import DataProvenance


class FacilityDiscoveryResult(BaseModel):
    """Structured facility discovery item."""
    model_config = ConfigDict(from_attributes=True)

    facility_id: str
    organization_id: str
    name: str
    facility_type: str
    status: str
    address: dict[str, Any] | None = None
    phone: str | None = None
    email: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    distance_km: float | None = Field(
        default=None,
        description="Straight-line distance in kilometers from search origin. None if distance is unavailable.",
    )
    services: list[str] = Field(default_factory=list, description="Authoritative supported services")
    capabilities: list[str] = Field(default_factory=list, description="Authoritative supported capabilities")
    departments: list[str] = Field(default_factory=list, description="Registered departments")
    provenance: DataProvenance | None = None
