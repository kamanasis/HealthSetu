"""HealthSetu AI Provider & Integration Layer (Phase 14).

Decouples clinical application domains from underlying LLM vendors.
All LLM access is routed through strict provider adapters, input sanitization,
structured output validation, and safety filters.
"""

from app.integrations.ai.base import AIProvider
from app.integrations.ai.client import get_ai_provider

__all__ = ["AIProvider", "get_ai_provider"]
