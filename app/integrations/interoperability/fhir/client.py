"""FHIR HTTP Client Wrapper (Phase 13).

Provides outbound transport handling for external FHIR R4 servers with
timeout, retry limits, and safe exception mapping.
"""

from typing import Any
import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    ExternalProviderAuthenticationFailedException,
    ExternalProviderTimeoutException,
    ExternalProviderUnavailableException,
)
from app.core.logging import get_logger

logger = get_logger("app.interoperability.fhir.client")


class FHIRClient:
    """Client for dispatching FHIR requests to external endpoints."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def send_bundle(self, endpoint_url: str, bundle: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
        """Send a FHIR Bundle to an external FHIR endpoint."""
        req_headers = {
            "Content-Type": "application/fhir+json",
            "Accept": "application/fhir+json",
        }
        if headers:
            req_headers.update(headers)

        if self.settings.INTEROPERABILITY_API_KEY:
            req_headers["Authorization"] = f"Bearer {self.settings.INTEROPERABILITY_API_KEY}"

        timeout = self.settings.INTEROPERABILITY_TIMEOUT_SECONDS

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(endpoint_url, json=bundle, headers=req_headers)

                if resp.status_code in (401, 403):
                    raise ExternalProviderAuthenticationFailedException(
                        f"External FHIR provider authentication failed (HTTP {resp.status_code})."
                    )
                if resp.status_code >= 500:
                    raise ExternalProviderUnavailableException(
                        f"External FHIR provider returned server error (HTTP {resp.status_code})."
                    )
                resp.raise_for_status()
                return resp.json() if resp.content else {"status": "success"}

        except httpx.TimeoutException as exc:
            logger.warning(f"External FHIR provider timeout: {exc}")
            raise ExternalProviderTimeoutException(
                "External FHIR provider request timed out."
            ) from exc
        except (ExternalProviderAuthenticationFailedException, ExternalProviderUnavailableException):
            raise
        except httpx.RequestError as exc:
            logger.warning(f"External FHIR provider transport error: {exc}")
            raise ExternalProviderUnavailableException(
                f"External FHIR provider communication failed: {exc}"
            ) from exc
