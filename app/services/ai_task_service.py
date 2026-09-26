"""AI Task Service.

Manages the AI task execution lifecycle, status state transitions, and background queueing.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.core.config import settings
from app.core.exceptions import (
    AITaskFailedException,
    AITaskNotFoundException,
)
from app.repositories.ai_repository import AIRepository
from app.schemas.ai import AITaskStatus, AITaskType
from app.schemas.ai_tasks import AITaskCreateRequest, AITaskRecord

logger = logging.getLogger(__name__)


class AITaskService:
    """Manages AI task states, queueing, retries, and persistence."""

    def __init__(self, repository: AIRepository) -> None:
        self.repository = repository
        self._max_retries = settings.AI_MAX_RETRIES

    async def create_task(
        self,
        request: AITaskCreateRequest,
        creator_id: str,
        organization_id: Optional[str] = None,
        source_content: Optional[str] = None,
    ) -> AITaskRecord:
        """Initialize and persist a new AI task in QUEUED status."""
        task_id = f"ai-task-{uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        task = AITaskRecord(
            id=task_id,
            task_type=request.task_type,
            status=AITaskStatus.QUEUED,
            creator_id=creator_id,
            patient_id=request.patient_id,
            organization_id=organization_id,
            source_reference=request.source_reference,
            input_context=request.input_context,
            source_content=source_content,
            created_at=now,
            updated_at=now,
        )

        await self.repository.create_task(task)
        logger.info("AI task queued: id=%s type=%s", task.id, task.task_type.value)
        return task

    async def get_task(self, task_id: str) -> AITaskRecord:
        """Fetch AI task by ID or raise AITaskNotFoundException."""
        task = await self.repository.get_task(task_id)
        if not task:
            raise AITaskNotFoundException(f"AI task with ID '{task_id}' was not found.")
        return task

    async def mark_processing(self, task: AITaskRecord) -> AITaskRecord:
        """Transition task to PROCESSING state."""
        task.status = AITaskStatus.PROCESSING
        return await self.repository.update_task(task)

    async def mark_completed(self, task: AITaskRecord, result_id: str) -> AITaskRecord:
        """Transition task to COMPLETED state linking result record."""
        task.status = AITaskStatus.COMPLETED
        task.result_id = result_id
        task.completed_at = datetime.now(timezone.utc)
        return await self.repository.update_task(task)

    async def mark_failed(self, task: AITaskRecord, error_message: str) -> AITaskRecord:
        """Transition task to FAILED state with error message."""
        task.status = AITaskStatus.FAILED
        task.error_message = error_message
        task.completed_at = datetime.now(timezone.utc)
        return await self.repository.update_task(task)

    async def record_retry(self, task: AITaskRecord, error_message: str) -> bool:
        """Increment retry count. Returns True if task can still be retried, False if max retries exceeded."""
        task.retry_count += 1
        task.error_message = error_message
        if task.retry_count <= self._max_retries:
            task.status = AITaskStatus.QUEUED
            await self.repository.update_task(task)
            return True
        else:
            task.status = AITaskStatus.FAILED
            await self.repository.update_task(task)
            return False
