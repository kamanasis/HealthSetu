"""Internal AI Provider Transfer Models (Phase 14).

Decouples provider-specific SDK payloads from HealthSetu domain services.
"""

from typing import Any, Type
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.ai import AIModelMetadata, AITaskType, AIUsageMetadata


class AIProviderRequest(BaseModel):
    """Normalized payload sent to an AI provider adapter."""

    model_config = ConfigDict(extra="ignore")

    task_type: AITaskType
    system_prompt: str
    user_prompt: str
    response_schema: Type[BaseModel] | None = None
    temperature: float = 0.0
    max_tokens: int = 2000
    timeout_seconds: int = 30
    metadata: dict[str, Any] = Field(default_factory=dict)


class AIProviderResponse(BaseModel):
    """Normalized payload received from an AI provider adapter."""

    model_config = ConfigDict(extra="ignore")

    raw_content: str
    parsed_json: dict[str, Any] | None = None
    model_name: str
    provider_name: str
    model_version: str | None = None
    usage: AIUsageMetadata = Field(default_factory=AIUsageMetadata)
    is_mock: bool = False

    @model_validator(mode="before")
    @classmethod
    def _normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Normalize raw_content vs raw_text
            if "raw_content" not in data and "raw_text" in data:
                data["raw_content"] = data["raw_text"]
            # Normalize model_name vs model
            if "model_name" not in data and "model" in data:
                data["model_name"] = data["model"]
            # Normalize provider_name vs provider
            if "provider_name" not in data and "provider" in data:
                data["provider_name"] = data["provider"]
            # Auto-construct usage if token fields are passed at top-level
            if "usage" not in data or data["usage"] is None:
                data["usage"] = AIUsageMetadata(
                    prompt_tokens=data.get("prompt_tokens", 0),
                    completion_tokens=data.get("completion_tokens", 0),
                    total_tokens=data.get("total_tokens", 0),
                    latency_ms=data.get("latency_ms", 0.0),
                )
        return data

    @property
    def raw_text(self) -> str:
        return self.raw_content

    @property
    def model(self) -> str:
        return self.model_name

    @property
    def provider(self) -> str:
        return self.provider_name

    @property
    def prompt_tokens(self) -> int:
        return self.usage.prompt_tokens

    @property
    def completion_tokens(self) -> int:
        return self.usage.completion_tokens

    @property
    def total_tokens(self) -> int:
        return self.usage.total_tokens

    @property
    def latency_ms(self) -> float:
        return self.usage.latency_ms
