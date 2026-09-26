"""AI Usage and Operational Cost Tracking Service.

Logs token usage, provider latencies, and execution status without PHI.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from app.repositories.ai_repository import AIRepository
from app.schemas.ai import AITaskType, AIUsageMetadata

logger = logging.getLogger(__name__)


class AIUsageService:
    """Tracks token consumption, latency, and operational health metrics strictly free of PHI."""

    def __init__(self, repository: AIRepository) -> None:
        self.repository = repository

    async def record_usage(
        self,
        task_id: str,
        task_type: AITaskType,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        latency_ms: float,
        success: bool = True,
        error_code: Optional[str] = None,
        estimated_cost_usd: Optional[float] = None,
    ) -> AIUsageMetadata:
        """Create and persist an operational usage record."""
        # Simple cost heuristic if not explicitly provided (e.g. $0.0015 / 1K tokens for mock/standard)
        if estimated_cost_usd is None and total_tokens > 0:
            estimated_cost_usd = round((total_tokens / 1000.0) * 0.0015, 6)

        metadata = AIUsageMetadata(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            estimated_cost_usd=estimated_cost_usd,
        )

        await self.repository.record_usage(metadata)
        logger.info(
            "AI Usage recorded: task_id=%s task_type=%s provider=%s model=%s tokens=%d latency=%.1fms success=%s",
            task_id,
            task_type.value,
            provider,
            model,
            total_tokens,
            latency_ms,
            success,
        )
        return metadata

    async def get_usage_summary(self, limit: int = 100) -> List[AIUsageMetadata]:
        """Fetch recent operational usage records."""
        return await self.repository.list_usage_records(limit=limit)
