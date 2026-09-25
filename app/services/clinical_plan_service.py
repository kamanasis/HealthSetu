"""Clinical Plan Service (Phase 10).

Manages clinician-authored clinical plan lifecycle:
  - TREATMENT, MANAGEMENT, DIAGNOSTIC, PREVENTIVE, PALLIATIVE, OTHER plans
  - Optimistic concurrency on updates
  - Finalize/lock workflow

SECURITY:
  - clinician_id is ALWAYS sourced from the authenticated JWT subject.
"""

from datetime import datetime, timezone
import uuid

from app.core.exceptions import AppException, ConflictException, ErrorCode, ForbiddenException
from app.repositories.clinical_plan_repository import ClinicalPlanRepository
from app.schemas.clinical_workflow import (
    ClinicalPlanCreate,
    ClinicalPlanFinalize,
    ClinicalPlanListResponse,
    ClinicalPlanRecord,
    ClinicalPlanResponse,
    ClinicalPlanStatus,
    ClinicalPlanType,
    ClinicalPlanUpdate,
)
from app.services.audit_service import AuditService


class ClinicalPlanService:
    """Service for clinician-authored clinical plans."""

    def __init__(
        self,
        plan_repo: ClinicalPlanRepository,
        audit_service: AuditService,
    ) -> None:
        self.plan_repo = plan_repo
        self.audit_service = audit_service

    async def create_plan(
        self,
        patient_id: str,
        payload: ClinicalPlanCreate,
        clinician_id: str,
    ) -> ClinicalPlanResponse:
        """Create a new clinical plan. clinician_id is from JWT."""
        plan_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        record = ClinicalPlanRecord(
            id=plan_id,
            patient_id=patient_id,
            encounter_id=payload.encounter_id,
            clinician_id=clinician_id,
            plan_type=payload.plan_type,
            title=payload.title,
            objectives=payload.objectives,
            interventions=payload.interventions,
            investigations=payload.investigations,
            follow_up_instructions=payload.follow_up_instructions,
            status=payload.status,
            created_at=now,
            updated_at=now,
        )
        await self.plan_repo.create(record)

        await self.audit_service.record_clinical_plan_created(
            actor_id=clinician_id,
            patient_id=patient_id,
            plan_id=plan_id,
            plan_type=payload.plan_type.value,
        )
        return self._to_response(record)

    async def get_plan(
        self,
        patient_id: str,
        plan_id: str,
        actor_id: str,
    ) -> ClinicalPlanResponse:
        """Retrieve a specific clinical plan."""
        record = await self._get_and_validate(patient_id, plan_id)
        await self.audit_service.record_clinical_plan_viewed(
            actor_id=actor_id,
            patient_id=patient_id,
            plan_id=plan_id,
        )
        return self._to_response(record)

    async def list_plans(
        self,
        patient_id: str,
        actor_id: str,
        limit: int = 50,
        offset: int = 0,
        plan_type: ClinicalPlanType | None = None,
        status: ClinicalPlanStatus | None = None,
        encounter_id: str | None = None,
        clinician_id: str | None = None,
    ) -> ClinicalPlanListResponse:
        """List paginated clinical plans for a patient."""
        records, total = await self.plan_repo.list_by_patient(
            patient_id=patient_id,
            limit=limit,
            offset=offset,
            plan_type=plan_type,
            status=status,
            encounter_id=encounter_id,
            clinician_id=clinician_id,
        )
        return ClinicalPlanListResponse(
            items=[self._to_response(r) for r in records],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def update_plan(
        self,
        patient_id: str,
        plan_id: str,
        payload: ClinicalPlanUpdate,
        clinician_id: str,
    ) -> ClinicalPlanResponse:
        """Update a clinical plan. Non-finalized only; authorship enforced."""
        record = await self._get_and_validate(patient_id, plan_id)

        if record.is_finalized:
            raise AppException(
                code=ErrorCode.CONFLICT,
                message="Finalized clinical plans are immutable.",
                status_code=409,
            )
        if record.clinician_id != clinician_id:
            raise ForbiddenException("Only the authoring clinician may modify this plan.")

        if record.version != payload.expected_version:
            raise ConflictException(
                f"Version conflict: expected {payload.expected_version}, current is {record.version}."
            )

        now = datetime.now(timezone.utc)
        updated_fields: list[str] = []
        updates: dict = {}

        if payload.title is not None and payload.title != record.title:
            updates["title"] = payload.title
            updated_fields.append("title")
        if payload.objectives is not None:
            updates["objectives"] = payload.objectives
            updated_fields.append("objectives")
        if payload.interventions is not None:
            updates["interventions"] = payload.interventions
            updated_fields.append("interventions")
        if payload.investigations is not None:
            updates["investigations"] = payload.investigations
            updated_fields.append("investigations")
        if payload.follow_up_instructions is not None:
            updates["follow_up_instructions"] = payload.follow_up_instructions
            updated_fields.append("follow_up_instructions")
        if payload.status is not None and payload.status != record.status:
            updates["status"] = payload.status
            updated_fields.append("status")

        updates.update({"version": record.version + 1, "updated_at": now})
        updated = record.model_copy(update=updates)
        await self.plan_repo.update(plan_id, updated)

        if updated_fields:
            await self.audit_service.record_clinical_plan_updated(
                actor_id=clinician_id,
                patient_id=patient_id,
                plan_id=plan_id,
                updated_fields=updated_fields,
            )
        return self._to_response(updated)

    async def finalize_plan(
        self,
        patient_id: str,
        plan_id: str,
        payload: ClinicalPlanFinalize,
        clinician_id: str,
    ) -> ClinicalPlanResponse:
        """Finalize/lock a clinical plan."""
        record = await self._get_and_validate(patient_id, plan_id)

        if record.is_finalized:
            raise AppException(
                code=ErrorCode.CONFLICT,
                message="Clinical plan is already finalized.",
                status_code=409,
            )
        if record.clinician_id != clinician_id:
            raise ForbiddenException("Only the authoring clinician may finalize this plan.")

        if record.version != payload.expected_version:
            raise ConflictException(
                f"Version conflict: expected {payload.expected_version}, current is {record.version}."
            )

        now = datetime.now(timezone.utc)
        finalized = record.model_copy(
            update={
                "is_finalized": True,
                "finalized_at": now,
                "version": record.version + 1,
                "updated_at": now,
            }
        )
        await self.plan_repo.update(plan_id, finalized)

        await self.audit_service.record_clinical_plan_finalized(
            actor_id=clinician_id,
            patient_id=patient_id,
            plan_id=plan_id,
        )
        return self._to_response(finalized)

    async def _get_and_validate(
        self,
        patient_id: str,
        plan_id: str,
    ) -> ClinicalPlanRecord:
        record = await self.plan_repo.get_by_id(plan_id)
        if not record or record.patient_id != patient_id:
            raise AppException(
                code=ErrorCode.NOT_FOUND,
                message=f"Clinical plan '{plan_id}' not found for patient.",
                status_code=404,
            )
        return record

    def _to_response(self, record: ClinicalPlanRecord) -> ClinicalPlanResponse:
        return ClinicalPlanResponse(
            plan_id=record.id,
            patient_id=record.patient_id,
            encounter_id=record.encounter_id,
            clinician_id=record.clinician_id,
            plan_type=record.plan_type,
            title=record.title,
            objectives=record.objectives,
            interventions=record.interventions,
            investigations=record.investigations,
            follow_up_instructions=record.follow_up_instructions,
            status=record.status,
            is_finalized=record.is_finalized,
            finalized_at=record.finalized_at,
            version=record.version,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
