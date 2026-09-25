"""Prescription service managing lifecycle, extraction linkage, and normalization."""

import uuid
from datetime import datetime, timezone

from app.core.exceptions import NotFoundException, ValidationException
from app.core.logging import get_logger
from app.repositories.document_repository import DocumentRepository
from app.repositories.medication_repository import MedicationRepository
from app.repositories.prescription_repository import (
    PrescriptionItemRecord,
    PrescriptionRecord,
    PrescriptionRepository,
)
from app.schemas.medication import NormalizedMedicationInfo
from app.schemas.prescription import (
    NormalizationStatus,
    PrescriptionCreate,
    PrescriptionItemResponse,
    PrescriptionListResponse,
    PrescriptionNormalizeResponse,
    PrescriptionResponse,
    PrescriptionStatus,
)
from app.services.audit_service import AuditService
from app.services.medication_normalization_service import MedicationNormalizationService
from app.services.prescription_extraction_mapper import PrescriptionExtractionMapper

logger = get_logger("prescription_service")


class PrescriptionService:
    """Service managing prescription entities, extraction integration, and items."""

    def __init__(
        self,
        prescription_repo: PrescriptionRepository,
        medication_repo: MedicationRepository,
        document_repo: DocumentRepository,
        normalization_service: MedicationNormalizationService,
        audit_service: AuditService,
    ) -> None:
        self.prescription_repo = prescription_repo
        self.medication_repo = medication_repo
        self.document_repo = document_repo
        self.normalization_service = normalization_service
        self.audit_service = audit_service

    async def create_prescription(
        self,
        patient_id: str,
        request: PrescriptionCreate,
        actor_id: str,
        auto_normalize: bool = True,
    ) -> PrescriptionResponse:
        """Create a new prescription record, optionally sourcing items from Phase 5 extraction."""
        # Validate document link if provided
        extraction_id = request.extraction_id
        if request.document_id:
            doc = await self.document_repo.get_document_by_id(request.document_id)
            if not doc or doc.patient_id != patient_id:
                raise NotFoundException(f"Referenced document '{request.document_id}' not found.")
            
            # If no items provided directly, attempt to map from document extraction
            if not request.items:
                ext = await self.document_repo.get_latest_extraction(request.document_id)
                if ext:
                    extraction_id = ext.id
                    mapped_items = PrescriptionExtractionMapper.map_extraction_fields(
                        fields=ext.structured_fields, extraction_id=ext.id
                    )
                    request.items.extend(mapped_items)

        prescription_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        prescription_date = (
            request.prescription_date
            if isinstance(request.prescription_date, datetime)
            else now
        )

        prescription_record = PrescriptionRecord(
            id=prescription_id,
            patient_id=patient_id,
            document_id=request.document_id,
            extraction_id=extraction_id,
            prescriber_reference=request.prescriber_reference,
            prescription_date=prescription_date,
            source=request.source,
            status=PrescriptionStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        item_records: list[PrescriptionItemRecord] = []
        for it in request.items:
            item_records.append(
                PrescriptionItemRecord(
                    id=str(uuid.uuid4()),
                    prescription_id=prescription_id,
                    drug_name_raw=it.drug_name_raw,
                    strength_raw=it.strength_raw,
                    dosage_form_raw=it.dosage_form_raw,
                    dose_raw=it.dose_raw,
                    route_raw=it.route_raw,
                    frequency_raw=it.frequency_raw,
                    duration_raw=it.duration_raw,
                    quantity_raw=it.quantity_raw,
                    instructions_raw=it.instructions_raw,
                    normalized_medication_id=None,
                    normalization_status=NormalizationStatus.PENDING,
                    extraction_reference=it.extraction_reference,
                    created_at=now,
                    updated_at=now,
                )
            )

        await self.prescription_repo.create_prescription(prescription_record, item_records)

        # Audit event
        await self.audit_service.record_prescription_created(
            actor_id=actor_id,
            patient_id=patient_id,
            prescription_id=prescription_id,
            source=request.source.value,
        )

        # Auto-normalize items if enabled
        if auto_normalize and item_records:
            await self.normalize_prescription(
                patient_id=patient_id,
                prescription_id=prescription_id,
                actor_id=actor_id,
            )

        return await self.get_prescription(patient_id=patient_id, prescription_id=prescription_id)

    async def get_prescription(self, patient_id: str, prescription_id: str) -> PrescriptionResponse:
        """Retrieve prescription by ID with child items and normalized info."""
        rec = await self.prescription_repo.get_prescription(prescription_id)
        if not rec or rec.patient_id != patient_id:
            raise NotFoundException("Prescription not found.")

        items = await self.prescription_repo.list_items(prescription_id)
        item_responses: list[PrescriptionItemResponse] = []
        for item in items:
            concept_info = None
            if item.normalized_medication_id:
                med = await self.medication_repo.get_by_id(item.normalized_medication_id)
                if med:
                    concept_info = self.normalization_service._map_medication_to_info(med)

            item_responses.append(
                PrescriptionItemResponse(
                    id=item.id,
                    prescription_id=item.prescription_id,
                    drug_name_raw=item.drug_name_raw,
                    strength_raw=item.strength_raw,
                    dosage_form_raw=item.dosage_form_raw,
                    dose_raw=item.dose_raw,
                    route_raw=item.route_raw,
                    frequency_raw=item.frequency_raw,
                    duration_raw=item.duration_raw,
                    quantity_raw=item.quantity_raw,
                    instructions_raw=item.instructions_raw,
                    normalized_medication_id=item.normalized_medication_id,
                    normalization_status=item.normalization_status,
                    normalized_concept=concept_info,
                    extraction_reference=item.extraction_reference,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                )
            )

        return PrescriptionResponse(
            id=rec.id,
            patient_id=rec.patient_id,
            document_id=rec.document_id,
            extraction_id=rec.extraction_id,
            prescriber_reference=rec.prescriber_reference,
            prescription_date=rec.prescription_date,
            source=rec.source,
            status=rec.status,
            items=item_responses,
            created_at=rec.created_at,
            updated_at=rec.updated_at,
        )

    async def list_prescriptions(
        self, patient_id: str, skip: int = 0, limit: int = 20
    ) -> PrescriptionListResponse:
        """List patient prescriptions with pagination."""
        prescriptions = await self.prescription_repo.list_prescriptions(
            patient_id=patient_id, skip=skip, limit=limit
        )
        total = await self.prescription_repo.count_prescriptions(patient_id=patient_id)

        responses: list[PrescriptionResponse] = []
        for p in prescriptions:
            detail = await self.get_prescription(patient_id=patient_id, prescription_id=p.id)
            responses.append(detail)

        return PrescriptionListResponse(
            items=responses,
            total=total,
            skip=skip,
            limit=limit,
        )

    async def normalize_prescription(
        self, patient_id: str, prescription_id: str, actor_id: str
    ) -> PrescriptionNormalizeResponse:
        """Trigger terminology normalization across all items in a prescription."""
        rec = await self.prescription_repo.get_prescription(prescription_id)
        if not rec or rec.patient_id != patient_id:
            raise NotFoundException("Prescription not found.")

        await self.audit_service.record_prescription_normalization_started(
            actor_id=actor_id, patient_id=patient_id, prescription_id=prescription_id
        )

        items = await self.prescription_repo.list_items(prescription_id)
        matched = 0
        ambiguous = 0
        unmatched = 0
        failed = 0

        normalized_items: list[PrescriptionItemResponse] = []
        for item in items:
            updated_item, concept_info = await self.normalization_service.normalize_prescription_item(
                prescription=rec, item=item
            )
            if updated_item.normalization_status == NormalizationStatus.MATCHED:
                matched += 1
            elif updated_item.normalization_status == NormalizationStatus.AMBIGUOUS:
                ambiguous += 1
            elif updated_item.normalization_status == NormalizationStatus.UNMATCHED:
                unmatched += 1
            elif updated_item.normalization_status == NormalizationStatus.FAILED:
                failed += 1

            normalized_items.append(
                PrescriptionItemResponse(
                    id=updated_item.id,
                    prescription_id=updated_item.prescription_id,
                    drug_name_raw=updated_item.drug_name_raw,
                    strength_raw=updated_item.strength_raw,
                    dosage_form_raw=updated_item.dosage_form_raw,
                    dose_raw=updated_item.dose_raw,
                    route_raw=updated_item.route_raw,
                    frequency_raw=updated_item.frequency_raw,
                    duration_raw=updated_item.duration_raw,
                    quantity_raw=updated_item.quantity_raw,
                    instructions_raw=updated_item.instructions_raw,
                    normalized_medication_id=updated_item.normalized_medication_id,
                    normalization_status=updated_item.normalization_status,
                    normalized_concept=concept_info,
                    extraction_reference=updated_item.extraction_reference,
                    created_at=updated_item.created_at,
                    updated_at=updated_item.updated_at,
                )
            )

        await self.audit_service.record_prescription_normalization_completed(
            actor_id=actor_id,
            patient_id=patient_id,
            prescription_id=prescription_id,
            items_count=len(normalized_items),
        )

        return PrescriptionNormalizeResponse(
            prescription_id=prescription_id,
            normalized_items_count=len(normalized_items),
            matched_count=matched,
            ambiguous_count=ambiguous,
            unmatched_count=unmatched,
            failed_count=failed,
            items=normalized_items,
        )

    async def get_prescription_item(
        self, patient_id: str, prescription_id: str, item_id: str
    ) -> PrescriptionItemResponse:
        """Retrieve single prescription item details."""
        rec = await self.prescription_repo.get_prescription(prescription_id)
        if not rec or rec.patient_id != patient_id:
            raise NotFoundException("Prescription not found.")

        item = await self.prescription_repo.get_item(prescription_id=prescription_id, item_id=item_id)
        if not item:
            raise NotFoundException("Prescription item not found.")

        concept_info = None
        if item.normalized_medication_id:
            med = await self.medication_repo.get_by_id(item.normalized_medication_id)
            if med:
                concept_info = self.normalization_service._map_medication_to_info(med)

        return PrescriptionItemResponse(
            id=item.id,
            prescription_id=item.prescription_id,
            drug_name_raw=item.drug_name_raw,
            strength_raw=item.strength_raw,
            dosage_form_raw=item.dosage_form_raw,
            dose_raw=item.dose_raw,
            route_raw=item.route_raw,
            frequency_raw=item.frequency_raw,
            duration_raw=item.duration_raw,
            quantity_raw=item.quantity_raw,
            instructions_raw=item.instructions_raw,
            normalized_medication_id=item.normalized_medication_id,
            normalization_status=item.normalization_status,
            normalized_concept=concept_info,
            extraction_reference=item.extraction_reference,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
