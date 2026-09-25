"""Clinical Note Service (Phase 10).

Manages clinician-authored clinical notes lifecycle:
  - SOAP, Progress, Consultation, Discharge, Referral, Procedure notes
  - Optimistic concurrency on updates (version-checked)
  - Sign/lock workflow (signed notes are immutable)
  - Addendum creation workflow

SECURITY:
  - clinician_id is ALWAYS sourced from the authenticated JWT subject.
  - The service never accepts clinician_id from the client payload.
"""

from datetime import datetime, timezone
from typing import Any
import uuid

from app.core.exceptions import AppException, ConflictException, ErrorCode, ForbiddenException
from app.repositories.clinical_note_repository import ClinicalNoteRepository
from app.schemas.clinical_workflow import (
    ClinicalNoteCreate,
    ClinicalNoteListResponse,
    ClinicalNoteRecord,
    ClinicalNoteResponse,
    ClinicalNoteSign,
    ClinicalNoteType,
    ClinicalNoteUpdate,
)
from app.services.audit_service import AuditService


class ClinicalNoteService:
    """Service for clinician-authored clinical notes."""

    def __init__(
        self,
        note_repo: ClinicalNoteRepository,
        audit_service: AuditService,
    ) -> None:
        self.note_repo = note_repo
        self.audit_service = audit_service

    # -----------------------------------------------------------------------
    # Create
    # -----------------------------------------------------------------------

    async def create_note(
        self,
        patient_id: str,
        payload: ClinicalNoteCreate,
        clinician_id: str,
    ) -> ClinicalNoteResponse:
        """Create a new clinical note.

        clinician_id is sourced from the authenticated JWT — never from client.
        """
        # Validate addendum chain
        if payload.is_addendum:
            if not payload.parent_note_id:
                raise AppException(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="An addendum note must reference a parent_note_id.",
                    status_code=400,
                )
            parent = await self.note_repo.get_by_id(payload.parent_note_id)
            if not parent or parent.patient_id != patient_id:
                raise AppException(
                    code=ErrorCode.NOT_FOUND,
                    message=f"Parent note '{payload.parent_note_id}' not found for patient.",
                    status_code=404,
                )

        note_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        record = ClinicalNoteRecord(
            id=note_id,
            patient_id=patient_id,
            encounter_id=payload.encounter_id,
            clinician_id=clinician_id,
            note_type=payload.note_type,
            title=payload.title,
            content=payload.content,
            is_addendum=payload.is_addendum,
            parent_note_id=payload.parent_note_id,
            created_at=now,
            updated_at=now,
        )
        await self.note_repo.create(record)

        await self.audit_service.record_clinical_note_created(
            actor_id=clinician_id,
            patient_id=patient_id,
            note_id=note_id,
            note_type=payload.note_type.value,
        )

        return self._to_response(record)

    # -----------------------------------------------------------------------
    # Read
    # -----------------------------------------------------------------------

    async def get_note(
        self,
        patient_id: str,
        note_id: str,
        actor_id: str,
    ) -> ClinicalNoteResponse:
        """Retrieve a specific clinical note."""
        record = await self._get_and_validate(patient_id, note_id)

        await self.audit_service.record_clinical_note_viewed(
            actor_id=actor_id,
            patient_id=patient_id,
            note_id=note_id,
        )
        return self._to_response(record)

    async def list_notes(
        self,
        patient_id: str,
        actor_id: str,
        limit: int = 50,
        offset: int = 0,
        note_type: ClinicalNoteType | None = None,
        encounter_id: str | None = None,
        clinician_id: str | None = None,
        signed_only: bool = False,
    ) -> ClinicalNoteListResponse:
        """List paginated clinical notes for a patient."""
        records, total = await self.note_repo.list_by_patient(
            patient_id=patient_id,
            limit=limit,
            offset=offset,
            note_type=note_type,
            encounter_id=encounter_id,
            clinician_id=clinician_id,
            signed_only=signed_only,
        )
        return ClinicalNoteListResponse(
            items=[self._to_response(r) for r in records],
            total=total,
            limit=limit,
            offset=offset,
        )

    # -----------------------------------------------------------------------
    # Update
    # -----------------------------------------------------------------------

    async def update_note(
        self,
        patient_id: str,
        note_id: str,
        payload: ClinicalNoteUpdate,
        clinician_id: str,
    ) -> ClinicalNoteResponse:
        """Update a clinical note. Only the authoring clinician may update.
        Signed notes are immutable.
        """
        record = await self._get_and_validate(patient_id, note_id)

        # Immutability: signed notes cannot be edited
        if record.is_signed:
            raise AppException(
                code=ErrorCode.CONFLICT,
                message="Signed clinical notes are immutable. Create an addendum instead.",
                status_code=409,
            )

        # Authorship enforcement: only the authoring clinician can update
        if record.clinician_id != clinician_id:
            raise ForbiddenException(
                "Only the authoring clinician may modify this note."
            )

        # Optimistic concurrency
        if record.version != payload.expected_version:
            raise ConflictException(
                f"Version conflict: expected {payload.expected_version}, current is {record.version}. "
                "Refresh and retry."
            )

        now = datetime.now(timezone.utc)
        updated_fields: list[str] = []

        new_title = record.title
        if payload.title is not None and payload.title != record.title:
            new_title = payload.title
            updated_fields.append("title")

        new_content = record.content
        if payload.content is not None and payload.content != record.content:
            new_content = payload.content
            updated_fields.append("content")

        updated = record.model_copy(
            update={
                "title": new_title,
                "content": new_content,
                "version": record.version + 1,
                "updated_at": now,
            }
        )
        await self.note_repo.update(note_id, updated)

        if updated_fields:
            await self.audit_service.record_clinical_note_updated(
                actor_id=clinician_id,
                patient_id=patient_id,
                note_id=note_id,
                updated_fields=updated_fields,
            )

        return self._to_response(updated)

    # -----------------------------------------------------------------------
    # Sign
    # -----------------------------------------------------------------------

    async def sign_note(
        self,
        patient_id: str,
        note_id: str,
        payload: ClinicalNoteSign,
        clinician_id: str,
    ) -> ClinicalNoteResponse:
        """Sign/lock a clinical note. Only the authoring clinician may sign."""
        record = await self._get_and_validate(patient_id, note_id)

        if record.is_signed:
            raise AppException(
                code=ErrorCode.CONFLICT,
                message="Clinical note is already signed.",
                status_code=409,
            )

        if record.clinician_id != clinician_id:
            raise ForbiddenException("Only the authoring clinician may sign this note.")

        if record.version != payload.expected_version:
            raise ConflictException(
                f"Version conflict: expected {payload.expected_version}, current is {record.version}."
            )

        now = datetime.now(timezone.utc)
        signed = record.model_copy(
            update={
                "is_signed": True,
                "signed_at": now,
                "version": record.version + 1,
                "updated_at": now,
            }
        )
        await self.note_repo.update(note_id, signed)

        await self.audit_service.record_clinical_note_signed(
            actor_id=clinician_id,
            patient_id=patient_id,
            note_id=note_id,
        )
        return self._to_response(signed)

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    async def _get_and_validate(
        self,
        patient_id: str,
        note_id: str,
    ) -> ClinicalNoteRecord:
        record = await self.note_repo.get_by_id(note_id)
        if not record or record.patient_id != patient_id:
            raise AppException(
                code=ErrorCode.NOT_FOUND,
                message=f"Clinical note '{note_id}' not found for patient.",
                status_code=404,
            )
        return record

    def _to_response(self, record: ClinicalNoteRecord) -> ClinicalNoteResponse:
        return ClinicalNoteResponse(
            note_id=record.id,
            patient_id=record.patient_id,
            encounter_id=record.encounter_id,
            clinician_id=record.clinician_id,
            note_type=record.note_type,
            title=record.title,
            content=record.content,
            is_signed=record.is_signed,
            signed_at=record.signed_at,
            is_addendum=record.is_addendum,
            parent_note_id=record.parent_note_id,
            version=record.version,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
