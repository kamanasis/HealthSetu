"""Medication Safety Repository.

DATABASE TEAM DEPENDENCY — PHASE 7
===================================
In-memory repository implementing the data contract for medication safety
evaluations and alerts.
Expected PostgreSQL tables:
- medication_safety_evaluations
- medication_safety_alerts
- medication_safety_check_summaries
"""

import asyncio
from datetime import datetime, timezone
import uuid
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.repositories.base import BaseRepository
from app.schemas.medication_safety import (
    CLINICAL_SAFETY_DISCLAIMER,
    MedicationContextSource,
    SafetyAlertSeverity,
    SafetyCheckType,
    SafetyEvaluationStatus,
)


class SafetyEvaluationRecord(BaseModel):
    """Database record representation of a safety evaluation run."""
    model_config = ConfigDict(frozen=True)

    id: str
    patient_id: str
    medication_context: MedicationContextSource
    status: SafetyEvaluationStatus
    provider: str
    provider_version: str
    ruleset_version: str | None = None
    medications_evaluated_count: int = 0
    patient_context_used: dict[str, int] = Field(default_factory=dict)
    disclaimer: str = CLINICAL_SAFETY_DISCLAIMER
    checked_at: datetime
    created_at: datetime


class SafetyAlertRecord(BaseModel):
    """Database record representation of a single clinical safety alert."""
    model_config = ConfigDict(frozen=True)

    id: str
    evaluation_id: str
    check_type: SafetyCheckType
    severity: SafetyAlertSeverity
    title: str
    description: str
    medications_involved: list[dict[str, str]] = Field(default_factory=list)
    clinical_context_involved: list[dict[str, str]] = Field(default_factory=list)
    evidence: str | None = None
    source: str
    provider_rule_id: str | None = None
    created_at: datetime


class CheckSummaryRecord(BaseModel):
    """Database record representation of check execution status."""
    model_config = ConfigDict(frozen=True)

    id: str
    evaluation_id: str
    check_type: SafetyCheckType
    supported: bool
    status: SafetyEvaluationStatus
    alert_count: int = 0
    note: str | None = None
    created_at: datetime


class MedicationSafetyRepository(BaseRepository[SafetyEvaluationRecord]):
    """Thread-safe in-memory store for safety evaluations and findings."""

    def __init__(self, session: Any = None) -> None:
        super().__init__(session=session)
        self._evaluations: dict[str, SafetyEvaluationRecord] = {}
        self._alerts: dict[str, list[SafetyAlertRecord]] = {}
        self._summaries: dict[str, list[CheckSummaryRecord]] = {}
        self._patient_evaluations: dict[str, list[str]] = {}
        self._lock = asyncio.Lock()

    async def get_by_id(self, record_id: str) -> SafetyEvaluationRecord | None:
        async with self._lock:
            return self._evaluations.get(record_id)

    async def create(self, record: SafetyEvaluationRecord) -> SafetyEvaluationRecord:
        async with self._lock:
            self._evaluations[record.id] = record
            if record.patient_id not in self._patient_evaluations:
                self._patient_evaluations[record.patient_id] = []
            self._patient_evaluations[record.patient_id].append(record.id)
            return record

    async def update(self, record: SafetyEvaluationRecord) -> SafetyEvaluationRecord:
        async with self._lock:
            self._evaluations[record.id] = record
            return record

    async def delete(self, record_id: str) -> bool:
        async with self._lock:
            if record_id in self._evaluations:
                eval_record = self._evaluations.pop(record_id)
                self._alerts.pop(record_id, None)
                self._summaries.pop(record_id, None)
                if eval_record.patient_id in self._patient_evaluations:
                    self._patient_evaluations[eval_record.patient_id] = [
                        eid for eid in self._patient_evaluations[eval_record.patient_id] if eid != record_id
                    ]
                return True
            return False

    async def save_evaluation(
        self,
        evaluation: SafetyEvaluationRecord,
        alerts: list[SafetyAlertRecord],
        summaries: list[CheckSummaryRecord],
    ) -> SafetyEvaluationRecord:
        """Atomically persist an evaluation with its alerts and check summaries."""
        async with self._lock:
            self._evaluations[evaluation.id] = evaluation
            self._alerts[evaluation.id] = list(alerts)
            self._summaries[evaluation.id] = list(summaries)
            if evaluation.patient_id not in self._patient_evaluations:
                self._patient_evaluations[evaluation.patient_id] = []
            self._patient_evaluations[evaluation.patient_id].append(evaluation.id)
            return evaluation

    async def get_evaluation(self, evaluation_id: str) -> SafetyEvaluationRecord | None:
        async with self._lock:
            return self._evaluations.get(evaluation_id)

    async def get_alerts_for_evaluation(self, evaluation_id: str) -> list[SafetyAlertRecord]:
        async with self._lock:
            return list(self._alerts.get(evaluation_id, []))

    async def get_summaries_for_evaluation(self, evaluation_id: str) -> list[CheckSummaryRecord]:
        async with self._lock:
            return list(self._summaries.get(evaluation_id, []))

    async def list_evaluations_for_patient(
        self,
        patient_id: str,
        status: SafetyEvaluationStatus | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[SafetyEvaluationRecord], int]:
        """List historical evaluations for a patient with optional filtering and pagination."""
        async with self._lock:
            eval_ids = self._patient_evaluations.get(patient_id, [])
            records: list[SafetyEvaluationRecord] = []
            for eid in eval_ids:
                rec = self._evaluations.get(eid)
                if not rec:
                    continue
                if status and rec.status != status:
                    continue
                if start_date and rec.checked_at < start_date:
                    continue
                if end_date and rec.checked_at > end_date:
                    continue
                records.append(rec)

            # Sort by checked_at desc
            records.sort(key=lambda r: r.checked_at, reverse=True)
            total = len(records)
            offset = (page - 1) * page_size
            paginated = records[offset : offset + page_size]
            return paginated, total

    def clear(self) -> None:
        """Clear all records for testing isolation."""
        self._evaluations.clear()
        self._alerts.clear()
        self._summaries.clear()
        self._patient_evaluations.clear()
