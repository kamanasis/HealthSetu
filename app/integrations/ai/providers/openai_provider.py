"""OpenAI/Compatible AI Provider Adapter with retry backoff and error normalization."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional, Type
import httpx
from pydantic import BaseModel

from app.core.config import settings
from app.core.exceptions import (
    AIConfigurationInvalidException,
    AIOutputInvalidException,
    AIOutputSchemaInvalidException,
    AIProviderAuthenticationFailedException,
    AIProviderRateLimitedException,
    AIProviderTimeoutException,
    AIProviderUnavailableException,
)
from app.integrations.ai.base import AIProvider
from app.integrations.ai.exceptions import AIAdapterExceptionNormalizer
from app.integrations.ai.models import AIProviderRequest, AIProviderResponse
from app.integrations.ai.validators import AIOutputValidator


class OpenAIProvider(AIProvider):
    """Adapter for OpenAI and OpenAI-compatible API services."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        self._api_key = api_key or settings.AI_API_KEY
        self._base_url = (base_url or settings.AI_BASE_URL).rstrip("/")
        self._model_name = model_name or settings.AI_MODEL
        self._timeout_seconds = timeout_seconds or float(settings.AI_TIMEOUT_SECONDS)
        self._max_retries = max_retries if max_retries is not None else settings.AI_MAX_RETRIES

        # SSRF Protection: enforce HTTPS unless running against localhost in development
        if not self._base_url.startswith("https://"):
            if not ("localhost" in self._base_url or "127.0.0.1" in self._base_url):
                raise AIConfigurationInvalidException(
                    "AI provider base URL must use HTTPS for non-local endpoints."
                )

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def version(self) -> str:
        return "v1"

    def _get_headers(self) -> Dict[str, str]:
        if not self._api_key:
            raise AIProviderAuthenticationFailedException("AI provider API key is not configured.")
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def _post_with_retry(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute HTTP POST with exponential backoff on transient errors."""
        url = f"{self._base_url}{endpoint}"
        retries = 0
        backoff_sec = 0.5

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            while True:
                start_time = time.monotonic()
                try:
                    response = await client.post(url, headers=self._get_headers(), json=payload)
                    
                    if response.status_code == 200:
                        return response.json()
                    elif response.status_code == 401 or response.status_code == 403:
                        raise AIProviderAuthenticationFailedException("AI provider rejected authentication credentials.")
                    elif response.status_code == 429:
                        if retries < self._max_retries:
                            retries += 1
                            time.sleep(backoff_sec)
                            backoff_sec *= 2
                            continue
                        raise AIProviderRateLimitedException("AI provider rate limit reached after retries.")
                    elif response.status_code >= 500:
                        if retries < self._max_retries:
                            retries += 1
                            time.sleep(backoff_sec)
                            backoff_sec *= 2
                            continue
                        raise AIProviderUnavailableException(f"AI provider server error: {response.status_code}")
                    else:
                        raise AIOutputInvalidException(f"AI provider returned unexpected status: {response.status_code}")

                except httpx.TimeoutException as exc:
                    if retries < self._max_retries:
                        retries += 1
                        time.sleep(backoff_sec)
                        backoff_sec *= 2
                        continue
                    raise AIProviderTimeoutException(f"AI provider timed out after {self._timeout_seconds} seconds: {exc}") from exc
                except httpx.RequestError as exc:
                    if retries < self._max_retries:
                        retries += 1
                        time.sleep(backoff_sec)
                        backoff_sec *= 2
                        continue
                    raise AIProviderUnavailableException(f"Network error communicating with AI provider: {exc}") from exc

    async def generate_text(self, request: AIProviderRequest) -> AIProviderResponse:
        start_time = time.monotonic()
        payload = {
            "model": request.model or self._model_name,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        data = await self._post_with_retry("/chat/completions", payload)
        latency_ms = (time.monotonic() - start_time) * 1000

        choices = data.get("choices", [])
        if not choices:
            raise AIOutputInvalidException("Provider returned empty choices array.")
        
        raw_text = choices[0].get("message", {}).get("content", "")
        usage = data.get("usage", {})

        return AIProviderResponse(
            raw_text=raw_text,
            model=data.get("model", self._model_name),
            provider=self.provider_name,
            model_version=self.version,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            latency_ms=latency_ms,
        )

    async def generate_structured(
        self,
        request: AIProviderRequest,
        schema: Type[BaseModel],
    ) -> AIProviderResponse:
        start_time = time.monotonic()
        # Enforce json_object response format
        payload = {
            "model": request.model or self._model_name,
            "messages": [
                {"role": "system", "content": f"{request.system_prompt}\nCRITICAL: You MUST respond ONLY with valid JSON matching the specified schema."},
                {"role": "user", "content": request.user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        data = await self._post_with_retry("/chat/completions", payload)
        latency_ms = (time.monotonic() - start_time) * 1000

        choices = data.get("choices", [])
        if not choices:
            raise AIOutputInvalidException("Provider returned empty choices.")

        raw_text = choices[0].get("message", {}).get("content", "")
        usage = data.get("usage", {})

        # Validate with the schema
        validated_obj = AIOutputValidator.validate_schema(raw_text, schema)

        return AIProviderResponse(
            raw_text=raw_text,
            parsed_json=validated_obj.model_dump(),
            model=data.get("model", self._model_name),
            provider=self.provider_name,
            model_version=self.version,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            latency_ms=latency_ms,
        )

    async def health_check(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self._base_url}/models", headers=self._get_headers())
                if res.status_code == 200:
                    return {"status": "healthy", "provider": self.provider_name, "model": self._model_name}
                return {"status": "unhealthy", "code": res.status_code}
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}

    def get_model_metadata(self) -> Dict[str, Any]:
        return {
            "provider": self.provider_name,
            "model": self._model_name,
            "version": self.version,
            "max_context_tokens": 8192,
            "max_output_tokens": settings.AI_MAX_OUTPUT_TOKENS,
            "supports_structured_output": True,
            "training_opt_in": settings.AI_TRAINING_OPT_IN,
            "retention_mode": settings.AI_DATA_RETENTION_MODE,
        }
