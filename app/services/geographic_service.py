"""Geographic Service (Phase 12).

Provides validation of geographic coordinates and deterministic straight-line distance calculation.
Handles missing coordinate states gracefully without assuming 0 or fabricating coordinates.
"""

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    IncompleteLocationException,
    InvalidLatitudeException,
    InvalidLongitudeException,
    InvalidRadiusException,
)
from app.integrations.geolocation.provider import (
    GeolocationProvider,
    get_geolocation_provider,
)


class GeographicService:
    """Service validating location parameters and computing distances."""

    def __init__(
        self,
        geo_provider: GeolocationProvider | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.geo_provider = geo_provider or get_geolocation_provider(self.settings)

    def validate_coordinates(
        self,
        latitude: float | None,
        longitude: float | None,
        radius_km: float | None = None,
    ) -> None:
        """Validate geographic inputs.

        Raises:
            IncompleteLocationException: If only one of (lat, lon) is provided.
            InvalidLatitudeException: If latitude is not in [-90, 90].
            InvalidLongitudeException: If longitude is not in [-180, 180].
            InvalidRadiusException: If radius <= 0 or exceeds configured max.
        """
        if (latitude is None and longitude is not None) or (latitude is not None and longitude is None):
            raise IncompleteLocationException(
                "Both latitude and longitude must be provided together."
            )

        if latitude is not None:
            if not (-90.0 <= latitude <= 90.0):
                raise InvalidLatitudeException(
                    f"Latitude {latitude} is outside valid range [-90.0, 90.0]."
                )

        if longitude is not None:
            if not (-180.0 <= longitude <= 180.0):
                raise InvalidLongitudeException(
                    f"Longitude {longitude} is outside valid range [-180.0, 180.0]."
                )

        if radius_km is not None:
            max_radius = self.settings.FACILITY_DISCOVERY_MAX_RADIUS_KM
            if radius_km <= 0 or radius_km > max_radius:
                raise InvalidRadiusException(
                    f"Radius {radius_km} km must be > 0 and <= maximum allowed ({max_radius} km)."
                )

    def calculate_distance_km(
        self,
        origin_lat: float | None,
        origin_lon: float | None,
        dest_lat: float | None,
        dest_lon: float | None,
    ) -> float | None:
        """Calculate distance in kilometers.

        Returns None if coordinates on either origin or destination are incomplete.
        Does NOT invent coordinates or assume zero.
        """
        if origin_lat is None or origin_lon is None or dest_lat is None or dest_lon is None:
            return None

        return self.geo_provider.calculate_distance_km(
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            destination_lat=dest_lat,
            destination_lon=dest_lon,
        )
