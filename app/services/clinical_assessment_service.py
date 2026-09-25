"""Clinical Assessment Service (Phase 10).

Manages clinician-authored clinical assessment lifecycle:
  - DIAGNOSIS, DIFFERENTIAL, FUNCTIONAL, RISK, PROGNOSIS, OTHER assessments
  - Optimistic concurrency on updates
  - Finalize/lock workflow

SECURITY:
  - clinician_id is ALWAYS sourced from the authenticated JWT subject.
"""

from datetime import datetime, timezone
import uuid

from app.core.exceptions import AppException, ConflictException, ErrorCode, ForbiddenException
from app.repositories.clinical_assessment_repository import ClinicalAssessmentRepository
from app.schemas.clinical_workflow import (
    ClinicalAssessmentCreate,
    ClinicalAssessmentFinalize,
    ClinicalAssessmentListResponse,
    ClinicalAssessmentRecord,
    ClinicalAssessmentResponse,
    ClinicalAssessmentType,
    ClinicalAssessmentUpdate,
)
from app.services.audit_service import AuditService


class ClinicalAssessmentService:
    """Service for clinician-authored clinical assessments."""

    def __init__(
        self,
        assessment_repo: ClinicalAssessmentRepository,
        audit_service: AuditService,
    ) -> None:
        self.assessment_repo = assessment_repo
        self.audit_service = audit_service

    async def create_assessment(
        self,
        patient_id: str,
        payload: ClinicalAssessmentCreate,
        clinician_id: str,
    ) -> ClinicalAssessmentResponse:
        """Create a new clinical assessment. clinician_id is from JWT."""
        assessment_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        record = ClinicalAssessmentRecord(
            id=assessment_id,
            patient_id=patient_id,
            encounter_id=payload.encounter_id,
            clinician_id=clinician_id,
            assessment_type=payload.assessment_type,
            title=payload.title,
            summary=payload.summary,
            findings=payload.findings,
            icd_codes=payload.icd_codes,
            severity=payload.severity,
            confidence=payload.confidence,
            created_at=now,
            updated_at=now,
        )
        await self.assessment_repo.create(record)

        await self.audit_service.record_clinical_assessment_created(
            actor_id=clinician_id,
            patient_id=patient_id,
            assessment_id=assessment_id,
            assessment_type=payload.assessment_type.value,
        )
        return self._to_response(record)

    async def get_assessment(
        self,
        patient_id: str,
        assessment_id: str,
        actor_id: str,
    ) -> ClinicalAssessmentResponse:
        """Retrieve a specific clinical assessment."""
        record = await self._get_and_validate(patient_id, assessment_id)
        await self.audit_service.record_clinical_assessment_viewed(
            actor_id=actor_id,
            patient_id=patient_id,
            assessment_id=assessment_id,
        )
        return self._to_response(record)

    async def list_assessments(
        self,
        patient_id: str,
        actor_id: str,
        limit: int = 50,
        offset: int = 0,
        assessment_type: ClinicalAssessmentType | None = None,
        encounter_id: str | None = None,
        clinician_id: str | None = None,
        finalized_only: bool = False,
    ) -> ClinicalAssessmentListResponse:
        """List paginated clinical assessments for a patient."""
        records, total = await self.assessment_repo.list_by_patient(
            patient_id=patient_id,
            limit=limit,
            offset=offset,
            assessment_type=assessment_type,
            encounter_id=encounter_id,
            clinician_id=clinician_id,
            finalized_only=finalized_only,
        )
        return ClinicalAssessmentListResponse(
            items=[self._to_response(r) for r in records],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def update_assessment(
        self,
        patient_id: str,
        assessment_id: str,
        payload: ClinicalAssessmentUpdate,
        clinician_id: str,
    ) -> ClinicalAssessmentResponse:
        """Update a clinical assessment. Non-finalized only; authorship enforced."""
        record = await self._get_and_validate(patient_id, assessment_id)

        if record.is_finalized:
            raise AppException(
                code=ErrorCode.CONFLICT,
                message="Finalized clinical assessments are immutable.",
                status_code=409,
            )
        if record.clinician_id != clinician_id:
            raise ForbiddenException("Only the authoring clinician may modify this assessment.")

        if record.version != payload.expected_version:
            raise ConflictException(
                f"Version conflict: expected {payload.expected_version}, current is {record.version}."
            )

        now = datetime.now(timezone.utc)
        updated_fields: list[str] = []
        updates: dict = {}

        if payload.summary is not None and payload.summary != record.summary:
            updates["summary"] = payload.summary
            updated_fields.append("summary")
        if payload.findings is not None:
            updates["findings"] = payload.findings
            updated_fields.append("findings")
        if payload.icd_codes is not None:
            updates["icd_codes"] = payload.icd_codes
            updated_fields.append("icd_codes")
        if payload.severity is not None:
            updates["severity"] = payload.severity
            updated_fields.append("severity")
        if payload.confidence is not None:
            updates["confidence"] = payload.confidence
            updated_fields.append("confidence")

        updates.update({"version": record.version + 1, "updated_at": now})
        updated = record.model_copy(update=updates)
        await self.assessment_repo.update(assessment_id, updated)

        if updated_fields:
            await self.audit_service.record_clinical_assessment_updated(
                actor_id=clinician_id,
                patient_id=patient_id,
                assessment_id=assessment_id,
                updated_fields=updated_fields,
            )
        return self._to_response(updated)

    async def finalize_assessment(
        self,
        patient_id: str,
        assessment_id: str,
        payload: ClinicalAssessmentFinalize,
        clinician_id: str,
    ) -> ClinicalAssessmentResponse:
        """Finalize/lock a clinical assessment."""
        record = await self._get_and_validate(patient_id, assessment_id)

        if record.is_finalized:
            raise AppException(
                code=ErrorCode.CONFLICT,
                message="Clinical assessment is already finalized.",
                status_code=409,
            )
        if record.clinician_id != clinician_id:
            raise ForbiddenException("Only the authoring clinician may finalize this assessment.")

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
        await self.assessment_repo.update(assessment_id, finalized)

        await self.audit_service.record_clinical_assessment_finalized(
            actor_id=clinician_id,
            patient_id=patient_id,
            assessment_id=assessment_id,
        )
        return self._to_response(finalized)

    async def _get_and_validate(
        self,
        patient_id: str,
        assessment_id: str,
    ) -> ClinicalAssessmentRecord:
        record = await self.assessment_repo.get_by_id(assessment_id)
        if not record or record.patient_id != patient_id:
            raise AppException(
                code=ErrorCode.NOT_FOUND,
                message=f"Clinical assessment '{assessment_id}' not found for patient.",
                status_code=404,
            )
        return record

    def _to_response(self, record: ClinicalAssessmentRecord) -> ClinicalAssessmentResponse:
        return ClinicalAssessmentResponse(
            assessment_id=record.id,
            patient_id=record.patient_id,
            encounter_id=record.encounter_id,
            clinician_id=record.clinician_id,
            assessment_type=record.assessment_type,
            title=record.title,
            summary=record.summary,
            findings=record.findings,
            icd_codes=record.icd_codes,
            severity=record.severity,
            confidence=record.confidence,
            is_finalized=record.is_finalized,
            finalized_at=record.finalized_at,
            version=record.version,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
