"""Geolocation Integration Package (Phase 12).

Provides pluggable adapters for distance calculations and geographic utilities.
"""

from app.integrations.geolocation.provider import (
    GeolocationProvider,
    LocalGeolocationProvider,
    get_geolocation_provider,
)

__all__ = [
    "GeolocationProvider",
    "LocalGeolocationProvider",
    "get_geolocation_provider",
]
