"""Personalized Care Plan Service (Phase 9).

Orchestrates post-discharge care coordination, actionable daily schedules,
goal tracking, task status updates, and safety netting guidance.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any
import uuid

from app.core.config import Settings, get_settings
from app.core.exceptions import AppException, ErrorCode
from app.repositories.care_plan_repository import CarePlanRepository
from app.repositories.discharge_repository import DischargeRepository
from app.schemas.care_plan import (
    CARE_PLAN_CLINICAL_DISCLAIMER,
    CarePlanCreate,
    CarePlanGenerateFromDischargeRequest,
    CarePlanGoal,
    CarePlanListResponse,
    CarePlanRecord,
    CarePlanResponse,
    CarePlanStatus,
    CarePlanTask,
    CarePlanTaskCategory,
    CarePlanTaskStatus,
    CarePlanUpdate,
    CarePlanWarningSignGuidance,
)
from app.schemas.discharge import DischargeVerificationStatus
from app.services.audit_service import AuditService


class CarePlanService:
    """Service managing personalized patient care plans and recovery schedules."""

    def __init__(
        self,
        care_plan_repo: CarePlanRepository,
        discharge_repo: DischargeRepository,
        audit_service: AuditService,
        settings: Settings | None = None,
    ) -> None:
        self.care_plan_repo = care_plan_repo
        self.discharge_repo = discharge_repo
        self.audit_service = audit_service
        self.settings = settings or get_settings()

    async def create_care_plan(
        self,
        patient_id: str,
        payload: CarePlanCreate,
        actor_id: str,
    ) -> CarePlanResponse:
        """Create a new personalized care plan directly."""
        start_date = datetime.now(timezone.utc).date()
        end_date = start_date + timedelta(days=payload.horizon_days)
        plan_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        record = CarePlanRecord(
            id=plan_id,
            patient_id=patient_id,
            discharge_id=payload.discharge_id,
            encounter_id=payload.encounter_id,
            title=payload.title,
            status=CarePlanStatus.ACTIVE,
            start_date=start_date,
            end_date=end_date,
            goals=payload.goals,
            tasks=payload.tasks,
            warning_signs=payload.warning_signs,
            notes=payload.notes,
            version=1,
            created_by=actor_id,
            created_at=now,
            updated_at=now,
        )

        await self.care_plan_repo.create(record)

        await self.audit_service.record_care_plan_created(
            actor_id=actor_id,
            patient_id=patient_id,
            care_plan_id=plan_id,
            source="CLINICIAN_CREATED",
        )

        return self._to_response(record)

    async def generate_from_discharge(
        self,
        patient_id: str,
        payload: CarePlanGenerateFromDischargeRequest,
        actor_id: str,
    ) -> CarePlanResponse:
        """Synthesize an actionable care plan from verified discharge instructions."""
        discharge = await self.discharge_repo.get_by_id(payload.discharge_id)
        if not discharge or discharge.patient_id != patient_id:
            raise AppException(
                code=ErrorCode.DISCHARGE_NOT_FOUND,
                message=f"Discharge instructions '{payload.discharge_id}' not found for patient.",
                status_code=404,
            )

        # Enforce clinical verification boundary
        if payload.require_verified and discharge.verification_status not in (
            DischargeVerificationStatus.VERIFIED,
            DischargeVerificationStatus.CORRECTED,
        ):
            raise AppException(
                code=ErrorCode.CARE_PLAN_UNVERIFIED_DISCHARGE,
                message=(
                    f"Discharge instructions '{payload.discharge_id}' have status '{discharge.verification_status.value}'. "
                    f"Clinical verification by an authorized clinician is required before generating an active care plan."
                ),
                status_code=400,
            )

        horizon = payload.horizon_days or self.settings.CARE_PLAN_DEFAULT_HORIZON_DAYS
        start_date = datetime.now(timezone.utc).date()
        end_date = start_date + timedelta(days=horizon)

        title = payload.title or (
            f"Recovery Care Plan - {discharge.discharge_diagnoses[0]}"
            if discharge.discharge_diagnoses
            else "Post-Discharge Recovery Care Plan"
        )

        tasks: list[CarePlanTask] = []
        # 1. Map medications into daily schedule tasks
        for m in discharge.medications:
            if not m.discontinued:
                tasks.append(
                    CarePlanTask(
                        id=str(uuid.uuid4()),
                        category=CarePlanTaskCategory.MEDICATION,
                        title=f"Take {m.drug_name}",
                        instructions=f"{m.dosage or ''} {m.frequency or ''} - {m.instructions or ''}".strip(),
                        frequency=m.frequency or "DAILY",
                        due_date=start_date,
                    )
                )

        # 2. Map activity instructions
        for a in discharge.activity_instructions:
            tasks.append(
                CarePlanTask(
                    id=str(uuid.uuid4()),
                    category=CarePlanTaskCategory.ACTIVITY,
                    title=f"Activity Guidance: {a.category}",
                    instructions=a.description,
                    frequency="DAILY",
                    due_date=start_date,
                )
            )

        # 3. Map diet instructions
        for d in discharge.diet_instructions:
            inst = ", ".join(d.recommendations + d.restrictions)
            tasks.append(
                CarePlanTask(
                    id=str(uuid.uuid4()),
                    category=CarePlanTaskCategory.DIET,
                    title=f"Diet Regimen: {d.dietary_type}",
                    instructions=inst or "Follow dietary directions as advised",
                    frequency="DAILY",
                    due_date=start_date,
                )
            )

        # 4. Map wound care
        for w in discharge.wound_care_instructions:
            tasks.append(
                CarePlanTask(
                    id=str(uuid.uuid4()),
                    category=CarePlanTaskCategory.WOUND_CARE,
                    title="Wound & Dressing Care",
                    instructions=w.dressing_instructions,
                    frequency=w.cleaning_frequency or "DAILY",
                    due_date=start_date,
                )
            )

        # 5. Map follow-up appointments
        for f in discharge.follow_up_instructions:
            tasks.append(
                CarePlanTask(
                    id=str(uuid.uuid4()),
                    category=CarePlanTaskCategory.FOLLOW_UP_APPOINTMENT,
                    title=f"Follow-up: {f.provider_or_specialty}",
                    instructions=f"Purpose: {f.purpose}. Timing: {f.recommended_timeframe}",
                    frequency="ONCE",
                    due_date=f.scheduled_date or (start_date + timedelta(days=14)),
                )
            )

        # 6. Map warning signs
        warning_guidance = [
            CarePlanWarningSignGuidance(red_flag=ws.symptom, immediate_instruction=ws.action_required)
            for ws in discharge.warning_signs
        ]

        goals = [
            CarePlanGoal(
                id=str(uuid.uuid4()),
                description="Complete prescribed post-discharge medication course and attend scheduled follow-up.",
                target_date=end_date,
                status="IN_PROGRESS",
            )
        ]

        plan_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        record = CarePlanRecord(
            id=plan_id,
            patient_id=patient_id,
            discharge_id=discharge.id,
            encounter_id=discharge.encounter_id,
            title=title,
            status=CarePlanStatus.ACTIVE,
            start_date=start_date,
            end_date=end_date,
            goals=goals,
            tasks=tasks,
            warning_signs=warning_guidance,
            notes=discharge.clinician_notes,
            version=1,
            created_by=actor_id,
            created_at=now,
            updated_at=now,
        )

        await self.care_plan_repo.create(record)

        await self.audit_service.record_care_plan_created(
            actor_id=actor_id,
            patient_id=patient_id,
            care_plan_id=plan_id,
            source=f"DISCHARGE_EXTRACTED:{discharge.id}",
        )

        return self._to_response(record)

    async def get_care_plan(
        self,
        patient_id: str,
        care_plan_id: str,
        actor_id: str,
    ) -> CarePlanResponse:
        """Retrieve a specific care plan by ID."""
        record = await self.care_plan_repo.get_by_id(care_plan_id)
        if not record or record.patient_id != patient_id:
            raise AppException(
                code=ErrorCode.CARE_PLAN_NOT_FOUND,
                message=f"Care plan '{care_plan_id}' not found for patient.",
                status_code=404,
            )

        await self.audit_service.record_care_plan_viewed(
            actor_id=actor_id,
            patient_id=patient_id,
            care_plan_id=care_plan_id,
        )
        return self._to_response(record)

    async def update_care_plan(
        self,
        patient_id: str,
        care_plan_id: str,
        payload: CarePlanUpdate,
        actor_id: str,
    ) -> CarePlanResponse:
        """Update care plan status or mark tasks completed."""
        record = await self.care_plan_repo.get_by_id(care_plan_id)
        if not record or record.patient_id != patient_id:
            raise AppException(
                code=ErrorCode.CARE_PLAN_NOT_FOUND,
                message=f"Care plan '{care_plan_id}' not found for patient.",
                status_code=404,
            )

        now = datetime.now(timezone.utc)
        updated_fields: list[str] = []
        old_status = record.status

        new_status = record.status
        if payload.status is not None and payload.status != record.status:
            new_status = payload.status
            updated_fields.append("status")

        # Mark completed tasks
        tasks = list(record.tasks)
        if payload.complete_task_ids:
            updated_fields.append("tasks")
            id_set = set(payload.complete_task_ids)
            for t in tasks:
                if t.id in id_set:
                    t.status = CarePlanTaskStatus.COMPLETED
                    t.completed_at = now

        new_notes = record.notes
        if payload.notes is not None:
            new_notes = payload.notes
            updated_fields.append("notes")

        updated_record = record.model_copy(
            update={
                "status": new_status,
                "tasks": tasks,
                "notes": new_notes,
                "version": record.version + 1,
                "updated_at": now,
            }
        )
        await self.care_plan_repo.update(care_plan_id, updated_record)

        if "status" in updated_fields:
            await self.audit_service.record_care_plan_status_changed(
                actor_id=actor_id,
                patient_id=patient_id,
                care_plan_id=care_plan_id,
                old_status=old_status.value,
                new_status=new_status.value,
            )

        if updated_fields:
            await self.audit_service.record_care_plan_updated(
                actor_id=actor_id,
                patient_id=patient_id,
                care_plan_id=care_plan_id,
                updated_fields=updated_fields,
            )

        return self._to_response(updated_record)

    async def list_patient_care_plans(
        self,
        patient_id: str,
        actor_id: str,
        limit: int = 50,
        offset: int = 0,
        status: CarePlanStatus | None = None,
    ) -> CarePlanListResponse:
        """List paginated care plans for a patient."""
        items, total = await self.care_plan_repo.list_by_patient(
            patient_id=patient_id,
            limit=limit,
            offset=offset,
            status=status,
        )
        return CarePlanListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    def _to_response(self, record: CarePlanRecord) -> CarePlanResponse:
        return CarePlanResponse(
            care_plan_id=record.id,
            patient_id=record.patient_id,
            discharge_id=record.discharge_id,
            encounter_id=record.encounter_id,
            title=record.title,
            status=record.status,
            start_date=record.start_date,
            end_date=record.end_date,
            goals=record.goals,
            tasks=record.tasks,
            warning_signs=record.warning_signs,
            notes=record.notes,
            version=record.version,
            disclaimer=CARE_PLAN_CLINICAL_DISCLAIMER,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
