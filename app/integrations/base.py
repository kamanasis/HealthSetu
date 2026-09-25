"""Base integration adapter interface for third-party healthcare services."""

from abc import ABC, abstractmethod
from typing import Any


class BaseIntegrationAdapter(ABC):
    """Abstract base class for all external provider integrations."""

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the external provider is configured and reachable."""
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Perform provider-specific health and availability check."""
        raise NotImplementedError
