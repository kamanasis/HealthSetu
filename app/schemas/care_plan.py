"""Pydantic schemas for Personalized Patient Care Plans (Phase 9).

Orchestrates post-discharge clinical coordination, actionable task schedules
(medication, activity, diet, wound care, follow-up calendar), and patient safety guidance.
"""

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
import uuid


CARE_PLAN_CLINICAL_DISCLAIMER: str = (
    "DISCLAIMER: This personalized care plan translates your clinical discharge instructions "
    "into actionable daily guidance. It does not replace medical advice or emergency medical care. "
    "If you experience severe or sudden worsening symptoms, seek emergency medical care immediately."
)


class CarePlanStatus(str, Enum):
    """Lifecycle status of a patient care plan."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    DISCONTINUED = "DISCONTINUED"


class CarePlanTaskCategory(str, Enum):
    """Domain category for care plan action items."""

    MEDICATION = "MEDICATION"
    ACTIVITY = "ACTIVITY"
    DIET = "DIET"
    WOUND_CARE = "WOUND_CARE"
    VITALS_MONITORING = "VITALS_MONITORING"
    FOLLOW_UP_APPOINTMENT = "FOLLOW_UP_APPOINTMENT"
    FOLLOW_UP = "FOLLOW_UP"


class CarePlanTaskStatus(str, Enum):
    """Execution status of an individual care plan task."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"


class CarePlanGoal(BaseModel):
    """Clinical or recovery goal for the care plan period."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str = Field(description="Goal description e.g., 'Maintain resting BP < 130/80', 'Ambulate 20 min daily'")
    target_date: date | None = None
    status: str = "IN_PROGRESS"


class CarePlanTask(BaseModel):
    """Actionable daily or periodic task item in the personalized schedule."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: CarePlanTaskCategory
    title: str = Field(description="Short task title e.g., 'Take Morning Medication', 'Check Temperature'")
    instructions: str = Field(description="Specific directions or dose")
    frequency: str = Field(default="DAILY", description="e.g. 'DAILY', 'TWICE_DAILY', 'WEEKLY', 'ONCE'")
    day_offset: int = Field(default=0, description="Day offset relative to care plan start date (0 = start day)")
    due_date: date | None = None
    status: CarePlanTaskStatus = CarePlanTaskStatus.PENDING
    completed_at: datetime | None = None
    notes: str | None = None


class CarePlanWarningSignGuidance(BaseModel):
    """Safety-netting warning signs and escalation instructions."""

    red_flag: str = Field(description="Symptom or sign to watch for")
    immediate_instruction: str = Field(description="Immediate patient action")


class CarePlanCreate(BaseModel):
    """Input payload to create a new personalized care plan."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=200, description="Care plan title")
    discharge_id: str | None = Field(default=None, description="Optional source discharge instruction record ID")
    encounter_id: str | None = Field(default=None, description="Optional clinical encounter reference")
    horizon_days: int = Field(default=30, ge=1, le=365, description="Care plan horizon in days")
    goals: list[CarePlanGoal] = Field(default_factory=list)
    tasks: list[CarePlanTask] = Field(default_factory=list)
    warning_signs: list[CarePlanWarningSignGuidance] = Field(default_factory=list)
    notes: str | None = None


class CarePlanGenerateFromDischargeRequest(BaseModel):
    """Request payload to synthesize a personalized care plan from verified discharge instructions."""

    model_config = ConfigDict(extra="forbid")

    discharge_id: str = Field(description="ID of verified discharge instructions")
    horizon_days: int | None = Field(default=30, ge=1, le=180)
    title: str | None = None
    require_verified: bool = Field(
        default=True,
        description="Whether to require clinician verification before generating active care plan",
    )


class CarePlanUpdate(BaseModel):
    """Payload to update an active care plan."""

    model_config = ConfigDict(extra="forbid")

    status: CarePlanStatus | None = None
    complete_task_ids: list[str] = Field(default_factory=list, description="IDs of tasks to mark COMPLETED")
    notes: str | None = None


class CarePlanRecord(BaseModel):
    """Complete persisted personalized care plan record."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    discharge_id: str | None = None
    encounter_id: str | None = None
    title: str
    status: CarePlanStatus = CarePlanStatus.ACTIVE
    start_date: date = Field(default_factory=lambda: datetime.now(timezone.utc).date())
    end_date: date
    goals: list[CarePlanGoal] = Field(default_factory=list)
    tasks: list[CarePlanTask] = Field(default_factory=list)
    warning_signs: list[CarePlanWarningSignGuidance] = Field(default_factory=list)
    notes: str | None = None
    version: int = 1
    created_by: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CarePlanResponse(BaseModel):
    """API response for a patient care plan."""

    care_plan_id: str
    patient_id: str
    discharge_id: str | None = None
    encounter_id: str | None = None
    title: str
    status: CarePlanStatus
    start_date: date
    end_date: date
    goals: list[CarePlanGoal]
    tasks: list[CarePlanTask]
    warning_signs: list[CarePlanWarningSignGuidance]
    notes: str | None = None
    version: int
    disclaimer: str = CARE_PLAN_CLINICAL_DISCLAIMER
    created_at: datetime
    updated_at: datetime

    @property
    def id(self) -> str:
        return self.care_plan_id


class CarePlanListResponse(BaseModel):
    """Paginated list of patient care plans."""

    items: list[CarePlanRecord]
    total: int
    limit: int
    offset: int
