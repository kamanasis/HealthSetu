"""Registry and factory for medication safety providers."""

from app.core.config import Settings, get_settings
from app.integrations.medication_safety.base import MedicationSafetyProvider
from app.integrations.medication_safety.providers.mock import MockMedicationSafetyProvider
from app.integrations.medication_safety.providers.licensed_provider import LicensedMedicationSafetyProvider
from app.schemas.medication_safety import SafetyProviderCapabilities


def get_medication_safety_provider(
    provider_name: str | None = None,
    settings: Settings | None = None,
) -> MedicationSafetyProvider:
    """Factory creating the appropriate MedicationSafetyProvider instance.

    Defaults to settings.MEDICATION_SAFETY_PROVIDER if not specified.
    """
    cfg = settings or get_settings()
    name = (provider_name or cfg.MEDICATION_SAFETY_PROVIDER or "mock").lower()

    if name in ("mock", "fake", "dev", "test"):
        return MockMedicationSafetyProvider()

    if name in ("licensed_provider", "licensed", "fdb", "drugbank"):
        return LicensedMedicationSafetyProvider(
            base_url=cfg.MEDICATION_SAFETY_BASE_URL,
            api_key=cfg.MEDICATION_SAFETY_API_KEY,
            timeout_seconds=cfg.MEDICATION_SAFETY_TIMEOUT_SECONDS,
            max_retries=cfg.MEDICATION_SAFETY_MAX_RETRIES,
        )

    # Fallback to mock for unknown provider in dev
    return MockMedicationSafetyProvider()


def get_safety_capabilities(provider: MedicationSafetyProvider) -> SafetyProviderCapabilities:
    """Return capability metadata for the given provider."""
    return SafetyProviderCapabilities(
        provider_name=provider.provider_name,
        provider_version=provider.provider_version,
        capabilities={k.value: v for k, v in provider.capabilities.items()},
    )
