"""AI Repository (Phase 14).

DATABASE TEAM DEPENDENCY — PHASE 14
===================================
In-memory repository implementing the data contract for AI tasks, AI results,
AI provenance, and AI token/usage metadata collection.

Expected PostgreSQL tables:
- ai_tasks
- ai_results
- ai_usage_records
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.repositories.base import BaseRepository
from app.schemas.ai import AITaskStatus, AITaskType, AIUsageMetadata, AIVerificationStatus
from app.schemas.ai_results import AIResultRecord
from app.schemas.ai_tasks import AITaskRecord


class AIRepository(BaseRepository[Any]):
    """Thread-safe repository managing AI tasks, results, and usage operational records."""

    def __init__(self, session: Any = None) -> None:
        super().__init__(session=session)
        self._tasks: Dict[str, AITaskRecord] = {}
        self._results: Dict[str, AIResultRecord] = {}
        self._usage_records: List[AIUsageMetadata] = []
        self._lock = asyncio.Lock()

    async def create_task(self, task: AITaskRecord) -> AITaskRecord:
        """Persist a newly queued or created AI task."""
        async with self._lock:
            self._tasks[task.id] = task
            return task

    async def get_task(self, task_id: str) -> Optional[AITaskRecord]:
        """Fetch AI task record by ID."""
        async with self._lock:
            return self._tasks.get(task_id)

    async def update_task(self, task: AITaskRecord) -> AITaskRecord:
        """Update task status, retry counts, or error logs."""
        async with self._lock:
            task.updated_at = datetime.now(timezone.utc)
            self._tasks[task.id] = task
            return task

    async def list_tasks_by_patient(self, patient_id: str) -> List[AITaskRecord]:
        """List tasks created for a given patient."""
        async with self._lock:
            return [t for t in self._tasks.values() if t.patient_id == patient_id]

    async def create_result(self, result: AIResultRecord) -> AIResultRecord:
        """Persist an AI output result record."""
        async with self._lock:
            self._results[result.id] = result
            return result

    async def get_result(self, result_id: str) -> Optional[AIResultRecord]:
        """Fetch AI result record by ID."""
        async with self._lock:
            return self._results.get(result_id)

    async def get_result_by_task_id(self, task_id: str) -> Optional[AIResultRecord]:
        """Fetch result associated with an AI task ID."""
        async with self._lock:
            for res in self._results.values():
                if res.task_id == task_id:
                    return res
            return None

    async def update_result(self, result: AIResultRecord) -> AIResultRecord:
        """Update result verification or status."""
        async with self._lock:
            result.updated_at = datetime.now(timezone.utc)
            self._results[result.id] = result
            return result

    async def record_usage(self, usage: AIUsageMetadata) -> AIUsageMetadata:
        """Record usage and cost tracking entry without PHI."""
        async with self._lock:
            self._usage_records.append(usage)
            return usage

    async def list_usage_records(self, limit: int = 100) -> List[AIUsageMetadata]:
        """Retrieve operational usage logs."""
        async with self._lock:
            return list(self._usage_records[-limit:])

    def clear(self) -> None:
        """Clear all in-memory AI state for tests."""
        self._tasks.clear()
        self._results.clear()
        self._usage_records.clear()

