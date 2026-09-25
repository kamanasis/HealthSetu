"""Abstract Interoperability Provider Interface (Phase 13).

Defines the pluggable adapter contract for external healthcare data exchange.
Ensures HealthSetu core services remain decoupled from vendor-specific transport protocols.
"""

from abc import ABC, abstractmethod
from typing import Any


class InteroperabilityProvider(ABC):
    """Abstract base class for healthcare interoperability provider adapters."""

    @abstractmethod
    async def import_resource(
        self,
        source_system: str,
        resource_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Receive or fetch an external healthcare resource payload."""
        pass

    @abstractmethod
    async def export_resource(
        self,
        target_system: str,
        resource_payload: dict[str, Any],
        format: str = "FHIR",
    ) -> dict[str, Any]:
        """Dispatch an authorized healthcare resource or Bundle to an external system."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check provider connectivity and service availability."""
        pass
