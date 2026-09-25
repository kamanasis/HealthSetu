"""Medication normalization service coordinating terminology lookups and record creation."""

import uuid
from datetime import datetime, timezone

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
from app.repositories.prescription_repository import (
    PrescriptionItemRecord,
    PrescriptionRecord,
    PrescriptionRepository,
)
from app.schemas.medication import (
    MedicationSource,
    NormalizedMedicationInfo,
    PatientMedicationStatus,
    VerificationStatus,
)
from app.schemas.prescription import NormalizationStatus

logger = get_logger("medication_normalization_service")


class MedicationNormalizationService:
    """Orchestrates terminology normalization for prescription items and patient medications.

    CRITICAL BOUNDARIES:
    - Raw extraction values are NEVER overwritten.
    - Normalization is terminology data standardization, NOT clinical verification or safety checking.
    - Multiple matches return AMBIGUOUS; no guessing.
    """

    def __init__(
        self,
        provider: MedicationTerminologyProvider,
        medication_repo: MedicationRepository,
        patient_medication_repo: PatientMedicationRepository,
        prescription_repo: PrescriptionRepository,
    ) -> None:
        self.provider = provider
        self.medication_repo = medication_repo
        self.patient_medication_repo = patient_medication_repo
        self.prescription_repo = prescription_repo

    async def normalize_prescription_item(
        self,
        prescription: PrescriptionRecord,
        item: PrescriptionItemRecord,
        force_reprocess: bool = False,
    ) -> tuple[PrescriptionItemRecord, NormalizedMedicationInfo | None]:
        """Normalize a single prescription item against the terminology provider.

        Guarantees:
        - Idempotent: returns existing normalized concept if already MATCHED unless force_reprocess is True.
        - Preserves raw input values.
        - Links or creates a canonical MedicationRecord on MATCHED.
        - Synchronizes/creates a patient medication record with full provenance.
        """
        # Idempotency check
        if not force_reprocess and item.normalization_status == NormalizationStatus.MATCHED and item.normalized_medication_id:
            existing_med = await self.medication_repo.get_by_id(item.normalized_medication_id)
            if existing_med:
                info = self._map_medication_to_info(existing_med)
                return item, info

        med_input = RawMedicationInput(
            drug_name_raw=item.drug_name_raw,
            strength_raw=item.strength_raw,
            dosage_form_raw=item.dosage_form_raw,
            route_raw=item.route_raw,
            frequency_raw=item.frequency_raw,
            duration_raw=item.duration_raw,
            instructions_raw=item.instructions_raw,
        )

        lookup_result: TerminologyLookupResult = await self.provider.normalize(med_input)

        normalized_info: NormalizedMedicationInfo | None = None
        med_id: str | None = None

        if lookup_result.status == NormalizationStatus.MATCHED and lookup_result.concept:
            concept = lookup_result.concept
            # Check or create canonical MedicationRecord
            now = datetime.now(timezone.utc)
            existing_med = await self.medication_repo.find_by_terminology(
                terminology_system=concept.terminology_system,
                terminology_code=concept.terminology_code,
                strength=concept.normalized_strength,
                dosage_form=concept.normalized_dosage_form,
            )

            if existing_med:
                med_id = existing_med.id
                normalized_info = self._map_medication_to_info(existing_med)
            else:
                med_id = str(uuid.uuid4())
                new_med = MedicationRecord(
                    id=med_id,
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
                saved_med = await self.medication_repo.save_medication(new_med)
                med_id = saved_med.id
                normalized_info = self._map_medication_to_info(saved_med)

        # Update prescription item record
        updated_item = await self.prescription_repo.update_item_normalization(
            item_id=item.id,
            status=lookup_result.status,
            normalized_medication_id=med_id,
        ) or item

        # Create or update PatientMedicationRecord for longitudinal tracking
        await self._sync_patient_medication(prescription, updated_item, med_id)

        return updated_item, normalized_info

    async def _sync_patient_medication(
        self,
        prescription: PrescriptionRecord,
        item: PrescriptionItemRecord,
        normalized_med_id: str | None,
    ) -> None:
        """Create or update corresponding PatientMedicationRecord ensuring complete provenance."""
        now = datetime.now(timezone.utc)
        # Check potential duplicate at data level
        is_dup = await self.patient_medication_repo.check_potential_duplicate(
            patient_id=prescription.patient_id,
            drug_name_raw=item.drug_name_raw,
            normalized_medication_id=normalized_med_id,
        )

        patient_med = PatientMedicationRecord(
            id=str(uuid.uuid4()),
            patient_id=prescription.patient_id,
            status=PatientMedicationStatus.PRESCRIBED,
            verification_status=VerificationStatus.EXTRACTED,
            drug_name_raw=item.drug_name_raw,
            strength_raw=item.strength_raw,
            dosage_form_raw=item.dosage_form_raw,
            route_raw=item.route_raw,
            frequency_raw=item.frequency_raw,
            duration_raw=item.duration_raw,
            instructions_raw=item.instructions_raw,
            normalized_medication_id=normalized_med_id,
            source=MedicationSource.PRESCRIPTION,
            document_id=prescription.document_id,
            extraction_id=prescription.extraction_id,
            prescription_id=prescription.id,
            prescription_item_id=item.id,
            potential_duplicate=is_dup,
            is_corrected=False,
            created_at=now,
            updated_at=now,
        )
        await self.patient_medication_repo.create_record(patient_med)

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
