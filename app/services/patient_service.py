"""Patient service — patient record lifecycle and access management.

PATIENT vs USER distinction
============================
  USER   = authentication identity (Phase 2 AuthService)
  PATIENT = clinical subject (this service)

A patient has a stable patient ID that serves as the canonical
clinical identifier. The optional user_id link connects the clinical
patient record to an authentication account.

This service is NOT responsible for:
- Authentication (Phase 2)
- Authorization evaluation (Phase 3 AuthorizationService)
- Clinical history, allergies, vitals, encounters (ClinicalRecordService)

AUTHORIZATION PATTERN
======================
All routes calling this service must have already passed through:
  1. get_current_user  (authentication)
  2. authz_service.authorize_or_raise()  (authorization)

This service assumes authorization is pre-verified.
It does NOT re-check permissions internally.

PHI PROTECTION
==============
Never log patient names, DOB, phone, email, or other PHI fields.
Audit events contain patient_id only — not demographic content.

DATABASE TEAM DEPENDENCIES
===========================
- patients table (see patient_repository.py for full contract)
- user_id → patient_id linkage
"""

from datetime import datetime, timezone

from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.logging import get_logger
from app.repositories.patient_repository import PatientRecord, PatientRepository
from app.schemas.patient import BiologicalSex, PatientResponse, PatientStatus, PatientUpdateRequest
from app.services.base import BaseService

logger = get_logger("app.patient")


def _map_to_response(record: PatientRecord) -> PatientResponse:
    """Map internal record to public API response schema."""
    return PatientResponse(
        id=record.id,
        user_id=record.user_id,
        first_name=record.first_name,
        last_name=record.last_name,
        date_of_birth=record.date_of_birth,
        sex=record.sex,
        preferred_language=record.preferred_language,
        phone=record.phone,
        email=record.email,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class PatientService(BaseService[PatientRepository]):
    """Service orchestrating patient record lifecycle."""

    def __init__(self, patient_repository: PatientRepository) -> None:
        super().__init__(repository=patient_repository)
        self.patient_repo = patient_repository

    # -----------------------------------------------------------------------
    # Retrieval
    # -----------------------------------------------------------------------

    async def get_patient(self, patient_id: str) -> PatientResponse:
        """Retrieve a patient record by ID.

        Authorization: caller must hold PATIENT_READ_SELF or CLINICAL_RECORD_READ.
        This is enforced at the route layer — not re-checked here.

        Raises NotFoundException for non-existent or INACTIVE patients to
        avoid confirming patient existence to unauthorized callers.
        """
        record = await self.patient_repo.get_by_id(patient_id)
        if record is None or record.status == PatientStatus.INACTIVE:
            raise NotFoundException("Patient not found.")
        return _map_to_response(record)

    async def get_patient_by_user_id(self, user_id: str) -> PatientResponse:
        """Retrieve the patient record linked to an authentication user.

        Used when a patient authenticates and requests their own record.
        Returns NotFoundException if no patient record is linked.

        Note: Not every authentication user has a patient record.
        """
        record = await self.patient_repo.get_by_user_id(user_id)
        if record is None:
            raise NotFoundException(
                "No patient record is linked to your account. "
                "Please contact your care provider."
            )
        if record.status == PatientStatus.INACTIVE:
            raise NotFoundException("Patient record is inactive.")
        return _map_to_response(record)

    async def get_patient_record_for_user(
        self,
        user_id: str,
        patient_id: str,
    ) -> PatientResponse:
        """Retrieve patient by ID, verifying that user is the linked account owner.

        Used for patient self-access to enforce:
          authenticated user_id == patient.user_id

        Raises NotFoundException (not 403) to prevent enumeration.
        """
        record = await self.patient_repo.get_by_id(patient_id)
        if record is None or record.status == PatientStatus.INACTIVE:
            raise NotFoundException("Patient not found.")
        if record.user_id != user_id:
            # Generic 404 to avoid confirming the patient exists
            raise NotFoundException("Patient not found.")
        return _map_to_response(record)

    # -----------------------------------------------------------------------
    # Update
    # -----------------------------------------------------------------------

    async def update_patient(
        self,
        patient_id: str,
        request: PatientUpdateRequest,
    ) -> PatientResponse:
        """Apply a partial update to permitted patient profile fields.

        Only fields explicitly provided in the request are modified.
        Omitted fields remain unchanged.
        PHI fields cannot be set to empty strings (min_length=1 enforced by schema).

        Raises NotFoundException if patient does not exist.
        """
        record = await self.patient_repo.get_by_id(patient_id)
        if record is None:
            raise NotFoundException("Patient not found.")

        # Build update dict from only the explicitly supplied fields
        updates = {
            k: v for k, v in request.model_dump(exclude_unset=True).items()
            if v is not None
        }

        if not updates:
            # No fields were supplied — return current record unchanged
            return _map_to_response(record)

        updated = await self.patient_repo.update(patient_id, updates)
        if updated is None:
            raise NotFoundException("Patient not found after update.")

        logger.info(
            "Patient profile updated",
            extra={
                "event_type": "PATIENT_PROFILE_UPDATED",
                "patient_id": patient_id,
                "updated_fields": list(updates.keys()),
                # NOTE: updated_fields lists field NAMES only — not values
            },
        )
        return _map_to_response(updated)

    # -----------------------------------------------------------------------
    # Internal: authorization context helpers
    # -----------------------------------------------------------------------

    async def resolve_patient_id(self, patient_id: str) -> str:
        """Resolve and validate that a patient_id exists.

        Used by clinical record service and routes to confirm the patient
        before performing sub-resource operations.

        Raises NotFoundException if patient does not exist.
        """
        record = await self.patient_repo.get_by_id(patient_id)
        if record is None or record.status == PatientStatus.INACTIVE:
            raise NotFoundException("Patient not found.")
        return record.id
