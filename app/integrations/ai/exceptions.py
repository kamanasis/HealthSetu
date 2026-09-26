"""AI Provider Exception Normalization (Phase 14).

Ensures vendor-specific exceptions (OpenAI, HTTPX, Azure) are intercepted
and mapped cleanly into HealthSetu application exceptions without leaking SDK internals.
"""

from typing import Any
import httpx
from app.core.exceptions import (
    AIDisabledException,
    AIGroundingFailedException,
    AIOutputInvalidException,
    AIOutputSchemaInvalidException,
    AIProviderAuthenticationException,
    AIProviderNotConfiguredException,
    AIProviderRateLimitedException,
    AIProviderTimeoutException,
    AIProviderUnavailableException,
    AITaskFailedException,
    AITaskNotSupportedException,
    AppException,
    PromptInjectionDetectedException,
)


class AIAdapterExceptionNormalizer:
    """Normalizes third-party client and HTTP errors into domain AppExceptions."""

    @staticmethod
    def normalize(exc: Exception) -> AppException:
        if isinstance(exc, AppException):
            return exc
        elif isinstance(exc, httpx.TimeoutException):
            return AIProviderTimeoutException(f"AI provider request timed out: {exc}")
        elif isinstance(exc, httpx.HTTPStatusError):
            code = exc.response.status_code
            if code in (401, 403):
                return AIProviderAuthenticationException("AI provider rejected authentication credentials.")
            elif code == 429:
                return AIProviderRateLimitedException("AI provider rate limit reached.")
            elif code >= 500:
                return AIProviderUnavailableException(f"AI provider service error ({code}).")
            else:
                return AIOutputInvalidException(f"AI provider HTTP error: {code}")
        elif isinstance(exc, httpx.RequestError):
            return AIProviderUnavailableException(f"Network error connecting to AI provider: {exc}")
        else:
            return AITaskFailedException(f"Unexpected AI execution failure: {exc}")


__all__ = [
    "AIAdapterExceptionNormalizer",
    "AIDisabledException",
    "AIGroundingFailedException",
    "AIOutputInvalidException",
    "AIOutputSchemaInvalidException",
    "AIProviderAuthenticationException",
    "AIProviderNotConfiguredException",
    "AIProviderRateLimitedException",
    "AIProviderTimeoutException",
    "AIProviderUnavailableException",
    "AITaskFailedException",
    "AITaskNotSupportedException",
    "PromptInjectionDetectedException",
]
