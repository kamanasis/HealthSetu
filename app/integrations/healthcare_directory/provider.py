"""Healthcare Directory Provider Adapter (Phase 11).

Defines the pluggable interface and default adapters for external healthcare registries.
External data does NOT overwrite internal authoritative facility data.
Provenance is preserved when directory data is processed.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.schemas.organization import DataProvenance, DataProvenanceSource

logger = get_logger("app.integrations.healthcare_directory")


class HealthcareDirectoryResult(BaseModel):
    """Normalized directory response item with full provenance."""
    identifier: str
    name: str
    entity_type: str  # ORGANIZATION or FACILITY
    address: dict[str, Any] | None = None
    phone: str | None = None
    email: str | None = None
    provenance: DataProvenance


class HealthcareDirectoryProvider(ABC):
    """Abstract interface for external healthcare directory providers."""

    @abstractmethod
    async def lookup_organization(self, identifier: str) -> HealthcareDirectoryResult | None:
        """Lookup an organization by external identifier / registry ID."""
        pass

    @abstractmethod
    async def lookup_facility(self, identifier: str) -> HealthcareDirectoryResult | None:
        """Lookup a facility by external identifier / registry ID."""
        pass

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[HealthcareDirectoryResult]:
        """Search the directory by name or query string."""
        pass


class NoneHealthcareDirectoryProvider(HealthcareDirectoryProvider):
    """Default no-op provider when directory integration is disabled or provider is 'none'."""

    async def lookup_organization(self, identifier: str) -> HealthcareDirectoryResult | None:
        return None

    async def lookup_facility(self, identifier: str) -> HealthcareDirectoryResult | None:
        return None

    async def search(self, query: str, limit: int = 10) -> list[HealthcareDirectoryResult]:
        return []


class MockHealthcareDirectoryProvider(HealthcareDirectoryProvider):
    """Mock directory provider for testing and development environments."""

    def __init__(self, provider_name: str = "mock-registry", version: str = "1.0.0") -> None:
        self.provider_name = provider_name
        self.version = version

    async def lookup_organization(self, identifier: str) -> HealthcareDirectoryResult | None:
        if identifier.startswith("ORG-"):
            return HealthcareDirectoryResult(
                identifier=identifier,
                name=f"Mock Directory Org ({identifier})",
                entity_type="ORGANIZATION",
                provenance=DataProvenance(
                    source=DataProvenanceSource.HEALTHCARE_DIRECTORY,
                    provider=self.provider_name,
                    provider_version=self.version,
                    retrieved_at=datetime.now(timezone.utc),
                ),
            )
        return None

    async def lookup_facility(self, identifier: str) -> HealthcareDirectoryResult | None:
        if identifier.startswith("FAC-"):
            return HealthcareDirectoryResult(
                identifier=identifier,
                name=f"Mock Directory Facility ({identifier})",
                entity_type="FACILITY",
                provenance=DataProvenance(
                    source=DataProvenanceSource.HEALTHCARE_DIRECTORY,
                    provider=self.provider_name,
                    provider_version=self.version,
                    retrieved_at=datetime.now(timezone.utc),
                ),
            )
        return None

    async def search(self, query: str, limit: int = 10) -> list[HealthcareDirectoryResult]:
        results: list[HealthcareDirectoryResult] = []
        if query:
            results.append(
                HealthcareDirectoryResult(
                    identifier=f"ORG-{query[:4].upper()}",
                    name=f"Directory Org matching {query}",
                    entity_type="ORGANIZATION",
                    provenance=DataProvenance(
                        source=DataProvenanceSource.HEALTHCARE_DIRECTORY,
                        provider=self.provider_name,
                        provider_version=self.version,
                        retrieved_at=datetime.now(timezone.utc),
                    ),
                )
            )
        return results[:limit]


def get_healthcare_directory_provider(settings: Settings | None = None) -> HealthcareDirectoryProvider:
    """Factory creating configured healthcare directory provider."""
    cfg = settings or get_settings()
    provider_type = (cfg.HEALTHCARE_DIRECTORY_PROVIDER or "none").lower()

    if provider_type == "mock":
        return MockHealthcareDirectoryProvider()
    elif provider_type == "none":
        return NoneHealthcareDirectoryProvider()
    else:
        logger.warning(
            f"Unknown directory provider '{provider_type}', falling back to NoneHealthcareDirectoryProvider"
        )
        return NoneHealthcareDirectoryProvider()
