"""Healthcare Directory Integration Package (Phase 11).

Provides pluggable adapters for external healthcare registries / directories.
"""

from app.integrations.healthcare_directory.provider import (
    HealthcareDirectoryProvider,
    HealthcareDirectoryResult,
    NoneHealthcareDirectoryProvider,
    MockHealthcareDirectoryProvider,
    get_healthcare_directory_provider,
)

__all__ = [
    "HealthcareDirectoryProvider",
    "HealthcareDirectoryResult",
    "NoneHealthcareDirectoryProvider",
    "MockHealthcareDirectoryProvider",
    "get_healthcare_directory_provider",
]
