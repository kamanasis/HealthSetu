"""Patient Transfer and Referral Service (Phase 12).

Manages transfer requests, receiving-facility validation, explicit selection,
clinical context minimization, consent verification, and status state machine.
"""

from datetime import datetime, timezone
import uuid
from typing import Any

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    EncounterAccessDeniedException,
    FacilityNotFoundException,
    ReceivingFacilityInvalidException,
    SBARAccessDeniedException,
    SendingFacilityInvalidException,
    TransferAccessDeniedException,
    TransferConsentRequiredException,
    TransferInvalidStateException,
    TransferNotFoundException,
)
from app.core.logging import get_logger
from app.repositories.allergy_repository import AllergyRepository
from app.repositories.consent_repository import ConsentRepository, ConsentStatus
from app.repositories.encounter_repository import EncounterRepository
from app.repositories.facility_repository import FacilityRepository
from app.repositories.patient_medication_repository import PatientMedicationRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.sbar_repository import SBARRepository
from app.repositories.symptom_repository import SymptomRepository
from app.repositories.transfer_repository import TransferRepository
from app.repositories.triage_repository import TriageRepository
from app.repositories.vitals_repository import VitalsRepository
from app.schemas.audit import AuditEventType
from app.schemas.facility import FacilityStatus
from app.schemas.transfer import (
    VALID_TRANSFER_TRANSITIONS,
    TransferCreateRequest,
    TransferRecord,
    TransferResponse,
    TransferStatus,
    TransferStatusUpdateRequest,
)
from app.schemas.transfer_context import TransferClinicalContext
from app.schemas.user import AuthenticatedUserContext
from app.services.audit_service import AuditService

logger = get_logger("app.services.transfer")


class TransferService:
    """Service managing patient transfers, referrals, and clinical context handoff."""

    def __init__(
        self,
        transfer_repo: TransferRepository,
        facility_repo: FacilityRepository,
        patient_repo: PatientRepository,
        encounter_repo: EncounterRepository,
        consent_repo: ConsentRepository,
        sbar_repo: SBARRepository,
        triage_repo: TriageRepository,
        symptom_repo: SymptomRepository,
        allergy_repo: AllergyRepository,
        medication_repo: PatientMedicationRepository,
        vitals_repo: VitalsRepository,
        audit_service: AuditService,
        settings: Settings | None = None,
    ) -> None:
        self.transfer_repo = transfer_repo
        self.facility_repo = facility_repo
        self.patient_repo = patient_repo
        self.encounter_repo = encounter_repo
        self.consent_repo = consent_repo
        self.sbar_repo = sbar_repo
        self.triage_repo = triage_repo
        self.symptom_repo = symptom_repo
        self.allergy_repo = allergy_repo
        self.medication_repo = medication_repo
        self.vitals_repo = vitals_repo
        self.audit_service = audit_service
        self.settings = settings or get_settings()

    async def create_transfer(
        self,
        patient_id: str,
        request_data: TransferCreateRequest,
        user_context: AuthenticatedUserContext,
    ) -> TransferResponse:
        """Create an explicit patient transfer or referral request."""
        # 1. Validate sending facility
        sending_fac = await self.facility_repo.get_by_id(request_data.sending_facility_id)
        if not sending_fac or sending_fac.status != FacilityStatus.ACTIVE:
            raise SendingFacilityInvalidException(
                f"Sending facility '{request_data.sending_facility_id}' not found or inactive."
            )

        # 2. Validate receiving facility
        receiving_fac = await self.facility_repo.get_by_id(request_data.receiving_facility_id)
        if not receiving_fac or receiving_fac.status != FacilityStatus.ACTIVE:
            raise ReceivingFacilityInvalidException(
                f"Receiving facility '{request_data.receiving_facility_id}' not found or inactive."
            )

        # 3. Sending facility cannot equal receiving facility
        if sending_fac.id == receiving_fac.id:
            raise ReceivingFacilityInvalidException(
                "Sending and receiving facilities cannot be identical."
            )

        # 4. Validate patient exists
        patient = await self.patient_repo.get_by_id(patient_id)
        if not patient:
            raise TransferAccessDeniedException(f"Patient '{patient_id}' not found.")

        # 5. Validate encounter if specified
        if request_data.encounter_id:
            encounter = await self.encounter_repo.get_by_id(request_data.encounter_id)
            if not encounter or encounter.patient_id != patient_id:
                raise EncounterAccessDeniedException(
                    f"Encounter '{request_data.encounter_id}' does not belong to patient '{patient_id}'."
                )

        # 6. Validate SBAR report if specified
        sbar_record = None
        if request_data.sbar_id:
            sbar_record = await self.sbar_repo.get_by_id(request_data.sbar_id)
            if not sbar_record or sbar_record.patient_id != patient_id:
                raise SBARAccessDeniedException(
                    f"SBAR report '{request_data.sbar_id}' does not belong to patient '{patient_id}'."
                )

        # 7. Validate Consent if required by configuration
        if self.settings.TRANSFER_REQUIRE_CONSENT:
            active_consents = await self.consent_repo.list_by_patient(patient_id, status_filter=ConsentStatus.ACTIVE)
            if not active_consents and patient.user_id:
                active_consents = await self.consent_repo.list_by_patient(patient.user_id, status_filter=ConsentStatus.ACTIVE)

            # Find a consent covering transfer or clinical records
            has_valid_consent = False
            for c in active_consents:
                c_scopes = getattr(c, "scopes", None) or [getattr(c, "scope", "")]
                if isinstance(c_scopes, str):
                    c_scopes = [c_scopes]
                scopes = [s.lower() for s in c_scopes if s]
                if any(scope in scopes for scope in ("transfer", "clinical_records", "all_records")):
                    has_valid_consent = True
                    break

            if not has_valid_consent and not request_data.consent_id:
                logger.warning(f"Transfer creation failed: missing consent for patient '{patient_id}'")
                raise TransferConsentRequiredException(
                    "Explicit patient consent is required to share clinical context for this transfer."
                )

        transfer_id = f"trf-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        # 8. Snapshot minimal clinical context if enabled
        if self.settings.TRANSFER_CLINICAL_CONTEXT_ENABLED:
            await self._attach_minimal_clinical_context(
                transfer_id=transfer_id,
                patient_id=patient_id,
                encounter_id=request_data.encounter_id,
                sbar_record=sbar_record,
                consent_id=request_data.consent_id,
                authorized_by=user_context.user_id,
            )

        # 9. Create Transfer record
        transfer = TransferRecord(
            id=transfer_id,
            patient_id=patient_id,
            encounter_id=request_data.encounter_id,
            sending_organization_id=sending_fac.organization_id,
            sending_facility_id=sending_fac.id,
            receiving_organization_id=receiving_fac.organization_id,
            receiving_facility_id=receiving_fac.id,
            status=TransferStatus.REQUESTED,
            priority=request_data.priority,
            reason=request_data.reason,
            sbar_id=request_data.sbar_id,
            consent_id=request_data.consent_id,
            clinical_context_reference=f"ctx-{transfer_id}",
            notes=request_data.notes,
            status_history=[
                {
                    "from_status": None,
                    "to_status": TransferStatus.REQUESTED.value,
                    "transitioned_by": user_context.user_id,
                    "timestamp": now.isoformat(),
                    "reason": "Initial transfer request created",
                }
            ],
            created_by=user_context.user_id,
            created_at=now,
            updated_at=now,
        )

        persisted = await self.transfer_repo.create(transfer)

        # Audit events
        await self.audit_service.record(
            event_type=AuditEventType.TRANSFER_CREATED,
            outcome="ALLOW",
            actor_id=user_context.user_id,
            action="transfer:create",
            resource_type="transfer",
            resource_id=transfer_id,
            metadata={
                "patient_id": patient_id,
                "sending_facility": sending_fac.id,
                "receiving_facility": receiving_fac.id,
                "priority": request_data.priority.value,
            },
        )

        if request_data.sbar_id:
            await self.audit_service.record(
                event_type=AuditEventType.TRANSFER_SBAR_ATTACHED,
                outcome="ALLOW",
                actor_id=user_context.user_id,
                action="transfer:attach_sbar",
                resource_type="transfer",
                resource_id=transfer_id,
                metadata={"sbar_id": request_data.sbar_id},
            )

        return TransferResponse.model_validate(persisted)

    async def _attach_minimal_clinical_context(
        self,
        transfer_id: str,
        patient_id: str,
        encounter_id: str | None,
        sbar_record: Any | None,
        consent_id: str | None,
        authorized_by: str,
    ) -> None:
        """Capture a strictly minimal clinical snapshot for transfer handoff."""
        # 1. Triage urgency
        urgency_level = None
        triage_notes = None
        triage_list, _ = await self.triage_repo.list_by_patient(patient_id=patient_id, limit=1)
        if triage_list:
            latest_t = triage_list[0]
            urgency_val = getattr(latest_t, "urgency", None) or getattr(latest_t, "urgency_level", None)
            urgency_level = (
                urgency_val.value
                if hasattr(urgency_val, "value")
                else str(urgency_val or "")
            )
            triage_notes = getattr(latest_t, "clinical_summary", None) or getattr(latest_t, "recommendation", None)
            if not triage_notes and getattr(latest_t, "explanation", None):
                triage_notes = getattr(latest_t.explanation, "summary", None)

        # 2. Symptoms
        symptoms_res = await self.symptom_repo.list_by_patient(patient_id=patient_id, limit=5)
        symptoms_list = symptoms_res[0] if isinstance(symptoms_res, tuple) else symptoms_res
        primary_symptoms = [getattr(s, "description", None) or getattr(s, "symptom_name", str(s)) for s in symptoms_list]

        # 3. Allergies
        allergies_res = await self.allergy_repo.list_by_patient(patient_id=patient_id)
        allergies_list = allergies_res[0] if isinstance(allergies_res, tuple) else allergies_res
        known_allergies = [getattr(a, "substance", str(a)) for a in allergies_list if getattr(a, "is_active", True)]

        # 4. Active medications
        meds_res = await self.medication_repo.list_by_patient(patient_id=patient_id, limit=5)
        meds_list = meds_res[0] if isinstance(meds_res, tuple) else meds_res
        active_medications = [
            getattr(m, "drug_name_raw", None) or getattr(m, "medication_name", str(m))
            for m in meds_list
        ]

        # 5. Latest vitals
        vitals_res = await self.vitals_repo.list_by_patient(patient_id=patient_id, limit=1)
        vitals_list = vitals_res[0] if isinstance(vitals_res, tuple) else vitals_res
        latest_vitals = None
        if vitals_list:
            v = vitals_list[0]
            latest_vitals = {
                "type": getattr(v, "vital_type", None).value if hasattr(getattr(v, "vital_type", None), "value") else str(getattr(v, "vital_type", "")),
                "value": getattr(v, "value", None),
                "unit": getattr(v, "unit", None),
                "measured_at": v.measured_at.isoformat() if hasattr(v, "measured_at") and v.measured_at else None,
            }

        # 6. SBAR summary
        sbar_id = None
        sbar_situation = None
        sbar_background = None
        sbar_assessment = None
        sbar_recommendation = None

        if sbar_record:
            sbar_id = sbar_record.id
            sbar_situation = (
                sbar_record.situation.summary_text
                if hasattr(sbar_record.situation, "summary_text")
                else str(sbar_record.situation)
            )
            sbar_background = (
                sbar_record.background.summary_text
                if hasattr(sbar_record.background, "summary_text")
                else str(sbar_record.background)
            )
            sbar_assessment = (
                sbar_record.assessment.summary_text
                if hasattr(sbar_record.assessment, "summary_text")
                else str(sbar_record.assessment)
            )
            sbar_recommendation = (
                sbar_record.recommendation.summary_text
                if hasattr(sbar_record.recommendation, "summary_text")
                else str(sbar_record.recommendation)
            )

        context = TransferClinicalContext(
            transfer_id=transfer_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
            urgency_level=urgency_level,
            triage_notes=triage_notes,
            primary_symptoms=primary_symptoms,
            known_allergies=known_allergies,
            active_medications=active_medications,
            latest_vitals=latest_vitals,
            sbar_id=sbar_id,
            sbar_situation=sbar_situation,
            sbar_background=sbar_background,
            sbar_assessment=sbar_assessment,
            sbar_recommendation=sbar_recommendation,
            consent_id=consent_id,
            authorized_by=authorized_by,
        )

        await self.transfer_repo.save_clinical_context(context)

        await self.audit_service.record(
            event_type=AuditEventType.TRANSFER_CLINICAL_CONTEXT_SHARED,
            outcome="ALLOW",
            actor_id=authorized_by,
            action="transfer:share_context",
            resource_type="transfer",
            resource_id=transfer_id,
            metadata={
                "has_sbar": sbar_id is not None,
                "symptoms_count": len(primary_symptoms),
                "meds_count": len(active_medications),
            },
        )

    async def get_transfer(
        self,
        transfer_id: str,
        user_context: AuthenticatedUserContext,
    ) -> TransferResponse:
        """Retrieve single transfer details."""
        transfer = await self.transfer_repo.get_by_id(transfer_id)
        if not transfer:
            raise TransferNotFoundException(f"Transfer '{transfer_id}' not found.")

        await self.audit_service.record(
            event_type=AuditEventType.TRANSFER_VIEWED,
            outcome="ALLOW",
            actor_id=user_context.user_id,
            action="transfer:read",
            resource_type="transfer",
            resource_id=transfer_id,
        )

        return TransferResponse.model_validate(transfer)

    async def list_patient_transfers(
        self,
        patient_id: str,
        user_context: AuthenticatedUserContext,
        limit: int = 50,
        offset: int = 0,
        status: TransferStatus | None = None,
    ) -> tuple[list[TransferResponse], int]:
        """List all transfers involving a patient."""
        records, total = await self.transfer_repo.list_by_patient(
            patient_id=patient_id,
            limit=limit,
            offset=offset,
            status=status,
        )

        await self.audit_service.record(
            event_type=AuditEventType.TRANSFER_VIEWED,
            outcome="ALLOW",
            actor_id=user_context.user_id,
            action="transfer:list",
            resource_type="patient",
            resource_id=patient_id,
            metadata={"total": total, "returned": len(records)},
        )

        return [TransferResponse.model_validate(r) for r in records], total

    async def update_transfer_status(
        self,
        transfer_id: str,
        update_data: TransferStatusUpdateRequest,
        user_context: AuthenticatedUserContext,
    ) -> TransferResponse:
        """Advance transfer through its state machine with strict transition validation."""
        transfer = await self.transfer_repo.get_by_id(transfer_id)
        if not transfer:
            raise TransferNotFoundException(f"Transfer '{transfer_id}' not found.")

        current_status = transfer.status
        target_status = update_data.status

        # Validate state transition
        allowed_transitions = VALID_TRANSFER_TRANSITIONS.get(current_status, set())
        if target_status not in allowed_transitions:
            logger.warning(
                f"Invalid transfer status transition attempted: {current_status.value} -> {target_status.value}"
            )
            raise TransferInvalidStateException(
                f"Transition from '{current_status.value}' to '{target_status.value}' is not permitted."
            )

        now = datetime.now(timezone.utc)
        transfer.status = target_status
        transfer.updated_at = now
        transfer.status_history.append(
            {
                "from_status": current_status.value,
                "to_status": target_status.value,
                "transitioned_by": user_context.user_id,
                "timestamp": now.isoformat(),
                "reason": update_data.reason,
                "notes": update_data.notes,
            }
        )

        updated = await self.transfer_repo.update(transfer_id, transfer)

        # Audit appropriate status event
        status_audit_map = {
            TransferStatus.ACCEPTED: AuditEventType.TRANSFER_ACCEPTED,
            TransferStatus.DECLINED: AuditEventType.TRANSFER_DECLINED,
            TransferStatus.CANCELLED: AuditEventType.TRANSFER_CANCELLED,
            TransferStatus.COMPLETED: AuditEventType.TRANSFER_COMPLETED,
            TransferStatus.FAILED: AuditEventType.TRANSFER_FAILED,
        }
        event_type = status_audit_map.get(target_status, AuditEventType.TRANSFER_STATUS_UPDATED)

        await self.audit_service.record(
            event_type=event_type,
            outcome="ALLOW",
            actor_id=user_context.user_id,
            action="transfer:update_status",
            resource_type="transfer",
            resource_id=transfer_id,
            metadata={
                "from_status": current_status.value,
                "to_status": target_status.value,
                "reason": update_data.reason,
            },
        )

        return TransferResponse.model_validate(updated)
