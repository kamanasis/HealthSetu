"""Geolocation Distance Calculation Providers (Phase 12).

Provides deterministic straight-line geographic distance calculation using the Haversine formula.
Replaces reliance on external maps APIs for basic radial and distance queries.
"""

from abc import ABC, abstractmethod
import math
from typing import Any

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger("app.integrations.geolocation")

# Mean Earth radius in kilometers (IUGG standard sphere)
EARTH_RADIUS_KM = 6371.0088


class GeolocationProvider(ABC):
    """Abstract interface for geographic distance calculations."""

    @abstractmethod
    def calculate_distance_km(
        self,
        origin_lat: float,
        origin_lon: float,
        destination_lat: float,
        destination_lon: float,
    ) -> float:
        """Calculate distance in kilometers between two points."""
        pass


class LocalGeolocationProvider(GeolocationProvider):
    """Deterministic local distance calculator implementing the Haversine formula."""

    def calculate_distance_km(
        self,
        origin_lat: float,
        origin_lon: float,
        destination_lat: float,
        destination_lon: float,
    ) -> float:
        # Convert degrees to radians
        lat1_rad = math.radians(origin_lat)
        lon1_rad = math.radians(origin_lon)
        lat2_rad = math.radians(destination_lat)
        lon2_rad = math.radians(destination_lon)

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = (
            math.sin(dlat / 2.0) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2.0) ** 2
        )
        # Numerical guard against float precision overshoots
        a = min(1.0, max(0.0, a))
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

        distance = EARTH_RADIUS_KM * c
        return round(distance, 2)


def get_geolocation_provider(settings: Settings | None = None) -> GeolocationProvider:
    """Factory retrieving configured geolocation provider."""
    cfg = settings or get_settings()
    provider_type = (cfg.GEOGRAPHIC_DISTANCE_PROVIDER or "local").lower()

    if provider_type in ("local", "mock"):
        return LocalGeolocationProvider()
    else:
        logger.info(f"Using default LocalGeolocationProvider (configured: '{provider_type}')")
        return LocalGeolocationProvider()
