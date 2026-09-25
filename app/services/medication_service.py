"""Medication service managing longitudinal patient medication records, corrections, and history."""

import uuid
from datetime import datetime, timezone

from app.core.exceptions import NotFoundException, ValidationException
from app.core.logging import get_logger
from app.integrations.medication.base import (
    MedicationTerminologyProvider,
    RawMedicationInput,
    TerminologyLookupResult,
)
from app.repositories.medication_repository import (
    MedicationRecord,
    MedicationRepository,
)
from app.repositories.patient_medication_repository import (
    PatientMedicationRecord,
    PatientMedicationRepository,
)
from app.schemas.medication import (
    MedicationCorrectionRequest,
    MedicationSource,
    MedicationStatusUpdateRequest,
    NormalizedMedicationInfo,
    PatientMedicationListResponse,
    PatientMedicationResponse,
    PatientMedicationStatus,
    VerificationStatus,
)
from app.schemas.prescription import NormalizationStatus
from app.services.audit_service import AuditService

logger = get_logger("medication_service")


class MedicationService:
    """Service managing patient medication records, lifecycle transitions, and corrections.

    CRITICAL BOUNDARIES:
    - Prescription ≠ Active medication (PRESCRIBED does not imply patient is actively taking it).
    - Data-level duplicate detection does NOT constitute clinical duplicate-therapy evaluation.
    - Historical records and original extraction artifacts are preserved across corrections.
    """

    def __init__(
        self,
        patient_medication_repo: PatientMedicationRepository,
        medication_repo: MedicationRepository,
        provider: MedicationTerminologyProvider,
        audit_service: AuditService,
    ) -> None:
        self.patient_medication_repo = patient_medication_repo
        self.medication_repo = medication_repo
        self.provider = provider
        self.audit_service = audit_service

    async def list_patient_medications(
        self,
        patient_id: str,
        status_filter: PatientMedicationStatus | None = None,
        source_filter: MedicationSource | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> PatientMedicationListResponse:
        """List patient medications with pagination, status, and source filters."""
        records = await self.patient_medication_repo.list_by_patient(
            patient_id=patient_id,
            status_filter=status_filter,
            source_filter=source_filter,
            skip=skip,
            limit=limit,
        )
        total = await self.patient_medication_repo.count_by_patient(
            patient_id=patient_id,
            status_filter=status_filter,
            source_filter=source_filter,
        )

        responses: list[PatientMedicationResponse] = []
        for rec in records:
            info = None
            if rec.normalized_medication_id:
                med = await self.medication_repo.get_by_id(rec.normalized_medication_id)
                if med:
                    info = self._map_medication_to_info(med)

            responses.append(self._map_record_to_response(rec, info))

        return PatientMedicationListResponse(
            items=responses,
            total=total,
            skip=skip,
            limit=limit,
        )

    async def get_patient_medication(
        self, patient_id: str, medication_id: str
    ) -> PatientMedicationResponse:
        """Retrieve single patient medication record with provenance and normalized details."""
        rec = await self.patient_medication_repo.get_record(medication_id)
        if not rec or rec.patient_id != patient_id:
            raise NotFoundException("Patient medication record not found.")

        info = None
        if rec.normalized_medication_id:
            med = await self.medication_repo.get_by_id(rec.normalized_medication_id)
            if med:
                info = self._map_medication_to_info(med)

        return self._map_record_to_response(rec, info)

    async def update_medication_status(
        self,
        patient_id: str,
        medication_id: str,
        request: MedicationStatusUpdateRequest,
        actor_id: str,
    ) -> PatientMedicationResponse:
        """Update patient medication status (e.g. PRESCRIBED -> ACTIVE / INACTIVE / HISTORICAL)."""
        rec = await self.patient_medication_repo.get_record(medication_id)
        if not rec or rec.patient_id != patient_id:
            raise NotFoundException("Patient medication record not found.")

        old_status = rec.status
        now = datetime.now(timezone.utc)
        updated_rec = rec.model_copy(
            update={
                "status": request.status,
                "updated_at": now,
            }
        )
        await self.patient_medication_repo.update_record(updated_rec)

        await self.audit_service.record_medication_status_changed(
            actor_id=actor_id,
            patient_id=patient_id,
            medication_id=medication_id,
            old_status=old_status.value,
            new_status=request.status.value,
        )

        return await self.get_patient_medication(patient_id=patient_id, medication_id=medication_id)

    async def correct_medication(
        self,
        patient_id: str,
        medication_id: str,
        request: MedicationCorrectionRequest,
        actor_id: str,
    ) -> PatientMedicationResponse:
        """Correct raw medication extraction, preserving original values and re-normalizing."""
        rec = await self.patient_medication_repo.get_record(medication_id)
        if not rec or rec.patient_id != patient_id:
            raise NotFoundException("Patient medication record not found.")

        now = datetime.now(timezone.utc)
        original_raw = rec.original_raw_value or rec.drug_name_raw

        # Re-evaluate normalization with corrected drug name and fields
        norm_input = RawMedicationInput(
            drug_name_raw=request.drug_name,
            strength_raw=request.strength or rec.strength_raw,
            dosage_form_raw=request.dosage_form or rec.dosage_form_raw,
            route_raw=request.route or rec.route_raw,
            frequency_raw=request.frequency or rec.frequency_raw,
            duration_raw=request.duration or rec.duration_raw,
            instructions_raw=request.instructions or rec.instructions_raw,
        )

        lookup: TerminologyLookupResult = await self.provider.normalize(norm_input)
        new_med_id = rec.normalized_medication_id

        if lookup.status == NormalizationStatus.MATCHED and lookup.concept:
            concept = lookup.concept
            existing_med = await self.medication_repo.find_by_terminology(
                terminology_system=concept.terminology_system,
                terminology_code=concept.terminology_code,
                strength=concept.normalized_strength,
                dosage_form=concept.normalized_dosage_form,
            )
            if existing_med:
                new_med_id = existing_med.id
            else:
                new_id = str(uuid.uuid4())
                created_med = MedicationRecord(
                    id=new_id,
                    canonical_name=concept.canonical_name,
                    generic_name=concept.generic_name,
                    brand_name=concept.brand_name,
                    terminology_system=concept.terminology_system,
                    terminology_code=concept.terminology_code,
                    strength=concept.normalized_strength,
                    dosage_form=concept.normalized_dosage_form,
                    route=concept.normalized_route,
                    provider=concept.provider,
                    provider_version=concept.provider_version,
                    confidence_score=concept.confidence_score,
                    created_at=now,
                )
                saved = await self.medication_repo.save_medication(created_med)
                new_med_id = saved.id

        updated_rec = rec.model_copy(
            update={
                "drug_name_raw": request.drug_name,
                "strength_raw": request.strength or rec.strength_raw,
                "dosage_form_raw": request.dosage_form or rec.dosage_form_raw,
                "route_raw": request.route or rec.route_raw,
                "frequency_raw": request.frequency or rec.frequency_raw,
                "duration_raw": request.duration or rec.duration_raw,
                "instructions_raw": request.instructions or rec.instructions_raw,
                "normalized_medication_id": new_med_id,
                "verification_status": VerificationStatus.CORRECTED,
                "is_corrected": True,
                "original_raw_value": original_raw,
                "corrected_raw_value": request.drug_name,
                "corrected_by": actor_id,
                "corrected_at": now,
                "updated_at": now,
            }
        )

        await self.patient_medication_repo.update_record(updated_rec)

        await self.audit_service.record_medication_corrected(
            actor_id=actor_id,
            patient_id=patient_id,
            medication_id=medication_id,
        )

        return await self.get_patient_medication(patient_id=patient_id, medication_id=medication_id)

    def _map_medication_to_info(self, med: MedicationRecord) -> NormalizedMedicationInfo:
        return NormalizedMedicationInfo(
            medication_id=med.id,
            canonical_name=med.canonical_name,
            generic_name=med.generic_name,
            brand_name=med.brand_name,
            terminology_system=med.terminology_system,
            terminology_code=med.terminology_code,
            normalized_strength=med.strength,
            normalized_dosage_form=med.dosage_form,
            normalized_route=med.route,
            provider=med.provider,
            provider_version=med.provider_version,
            confidence_score=med.confidence_score,
        )

    def _map_record_to_response(
        self, rec: PatientMedicationRecord, info: NormalizedMedicationInfo | None
    ) -> PatientMedicationResponse:
        return PatientMedicationResponse(
            id=rec.id,
            patient_id=rec.patient_id,
            status=rec.status,
            verification_status=rec.verification_status,
            drug_name_raw=rec.drug_name_raw,
            strength_raw=rec.strength_raw,
            dosage_form_raw=rec.dosage_form_raw,
            route_raw=rec.route_raw,
            frequency_raw=rec.frequency_raw,
            duration_raw=rec.duration_raw,
            instructions_raw=rec.instructions_raw,
            normalized_medication_id=rec.normalized_medication_id,
            normalized_info=info,
            source=rec.source,
            document_id=rec.document_id,
            extraction_id=rec.extraction_id,
            prescription_id=rec.prescription_id,
            prescription_item_id=rec.prescription_item_id,
            potential_duplicate=rec.potential_duplicate,
            is_corrected=rec.is_corrected,
            original_raw_value=rec.original_raw_value,
            corrected_raw_value=rec.corrected_raw_value,
            corrected_by=rec.corrected_by,
            corrected_at=rec.corrected_at,
            start_date=rec.start_date,
            end_date=rec.end_date,
            created_at=rec.created_at,
            updated_at=rec.updated_at,
        )
