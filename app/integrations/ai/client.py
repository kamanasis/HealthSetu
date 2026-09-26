"""AI client factory and provider lifecycle management."""

from __future__ import annotations

from typing import Optional
from app.core.config import settings
from app.core.exceptions import AIProviderNotConfiguredException
from app.integrations.ai.base import AIProvider
from app.integrations.ai.providers.mock_provider import MockAIProvider
from app.integrations.ai.providers.openai_provider import OpenAIProvider


_provider_instance: Optional[AIProvider] = None


def get_ai_provider(provider_type: Optional[str] = None) -> AIProvider:
    """Retrieve or initialize the configured AI provider adapter."""
    global _provider_instance
    chosen = (provider_type or settings.AI_PROVIDER).lower()

    if chosen == "mock":
        return MockAIProvider()
    elif chosen in ("openai", "openai-compatible"):
        return OpenAIProvider()
    else:
        raise AIProviderNotConfiguredException(
            f"Configured AI provider '{chosen}' is not supported or not recognized."
        )


def reset_ai_provider() -> None:
    """Reset cached provider instance (useful for unit tests with simulated failures)."""
    global _provider_instance
    _provider_instance = None
