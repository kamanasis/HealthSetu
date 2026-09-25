"""Clinical Workspace Service (Phase 10).

Provides a consolidated, read-only clinical workspace view for authorized
clinicians. Aggregates data from all prior-phase domains:
  - Phase 4: Patient demographics, clinical history, allergies, vitals, encounters
  - Phase 5: Documents
  - Phase 6: Prescriptions, medications
  - Phase 7: Medication safety results
  - Phase 8: Symptoms, triage, SBAR
  - Phase 9: Discharge summaries, care plans
  - Phase 10: Clinical notes, assessments, plans

SECURITY:
  - The workspace is only available to DOCTOR role with an authorized patient relationship.
  - clinician_id is sourced exclusively from the server-side JWT.
  - The workspace contains structural counts only at the summary level.
    Individual domain reads require their own endpoints with their own auth.
"""

from datetime import datetime, timezone

from app.repositories.allergy_repository import AllergyRepository
from app.repositories.care_plan_repository import CarePlanRepository
from app.repositories.clinical_assessment_repository import ClinicalAssessmentRepository
from app.repositories.clinical_history_repository import ClinicalHistoryRepository
from app.repositories.clinical_note_repository import ClinicalNoteRepository
from app.repositories.clinical_plan_repository import ClinicalPlanRepository
from app.repositories.discharge_repository import DischargeRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.encounter_repository import EncounterRepository
from app.repositories.medication_safety_repository import MedicationSafetyRepository
from app.repositories.patient_medication_repository import PatientMedicationRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.prescription_repository import PrescriptionRepository
from app.repositories.sbar_repository import SBARRepository
from app.repositories.symptom_repository import SymptomRepository
from app.repositories.triage_repository import TriageRepository
from app.repositories.vitals_repository import VitalsRepository
from app.schemas.clinical_workflow import (
    ClinicalNoteResponse,
    ClinicalAssessmentResponse,
    ClinicalPlanResponse,
    ClinicalPlanStatus,
    ClinicalWorkspaceResponse,
    WorkspacePatientSummary,
    WorkspaceSummary,
)
from app.services.audit_service import AuditService
from app.services.clinical_note_service import ClinicalNoteService
from app.services.clinical_assessment_service import ClinicalAssessmentService
from app.services.clinical_plan_service import ClinicalPlanService
from app.core.exceptions import AppException, ErrorCode


class ClinicalWorkspaceService:
    """Consolidates all clinical domain data into a single workspace view.

    This service is read-only — it aggregates but never mutates clinical data.
    Each domain's write operations are delegated to their respective services.
    """

    def __init__(
        self,
        patient_repo: PatientRepository,
        history_repo: ClinicalHistoryRepository,
        allergy_repo: AllergyRepository,
        vitals_repo: VitalsRepository,
        encounter_repo: EncounterRepository,
        document_repo: DocumentRepository,
        prescription_repo: PrescriptionRepository,
        patient_medication_repo: PatientMedicationRepository,
        safety_repo: MedicationSafetyRepository,
        symptom_repo: SymptomRepository,
        triage_repo: TriageRepository,
        sbar_repo: SBARRepository,
        discharge_repo: DischargeRepository,
        care_plan_repo: CarePlanRepository,
        note_repo: ClinicalNoteRepository,
        assessment_repo: ClinicalAssessmentRepository,
        plan_repo: ClinicalPlanRepository,
        note_service: ClinicalNoteService,
        assessment_service: ClinicalAssessmentService,
        plan_service: ClinicalPlanService,
        audit_service: AuditService,
    ) -> None:
        self.patient_repo = patient_repo
        self.history_repo = history_repo
        self.allergy_repo = allergy_repo
        self.vitals_repo = vitals_repo
        self.encounter_repo = encounter_repo
        self.document_repo = document_repo
        self.prescription_repo = prescription_repo
        self.patient_medication_repo = patient_medication_repo
        self.safety_repo = safety_repo
        self.symptom_repo = symptom_repo
        self.triage_repo = triage_repo
        self.sbar_repo = sbar_repo
        self.discharge_repo = discharge_repo
        self.care_plan_repo = care_plan_repo
        self.note_repo = note_repo
        self.assessment_repo = assessment_repo
        self.plan_repo = plan_repo
        self.note_service = note_service
        self.assessment_service = assessment_service
        self.plan_service = plan_service
        self.audit_service = audit_service

    async def get_workspace(
        self,
        patient_id: str,
        clinician_id: str,
        encounter_id: str | None = None,
    ) -> ClinicalWorkspaceResponse:
        """Assemble the consolidated clinical workspace for a clinician.

        Aggregates summary counts from all clinical domains and fetches
        the most recent clinical notes/assessments/plans for quick review.
        """
        # --- Patient demographics ---
        patient = await self.patient_repo.get_by_id(patient_id)
        if not patient:
            raise AppException(
                code=ErrorCode.NOT_FOUND,
                message=f"Patient '{patient_id}' not found.",
                status_code=404,
            )

        patient_summary = WorkspacePatientSummary(
            patient_id=patient.id,
            first_name=patient.first_name,
            last_name=patient.last_name,
            date_of_birth=patient.date_of_birth,
            sex=patient.sex.value if patient.sex else None,
            preferred_language=patient.preferred_language,
        )

        # --- Domain counts ---
        # Phase 4 — history/allergy return plain lists (no pagination)
        history_records = await self.history_repo.list_by_patient(patient_id)
        history_total = len(history_records)

        allergy_records = await self.allergy_repo.list_by_patient(patient_id)
        allergy_total = len(allergy_records)

        # vitals/encounter: limit-only param
        vitals_records = await self.vitals_repo.list_by_patient(patient_id, limit=1000)
        vitals_total = len(vitals_records)

        encounter_records = await self.encounter_repo.list_by_patient(patient_id, limit=1000)
        encounter_total = len(encounter_records)

        # Phase 5 — document repo returns a plain list
        doc_records = await self.document_repo.list_documents_by_patient(patient_id)
        doc_total = len(doc_records)

        # Phase 6 — prescriptions use skip/limit
        rx_records = await self.prescription_repo.list_prescriptions(
            patient_id=patient_id, skip=0, limit=1000
        )
        rx_total = len(rx_records)

        all_meds = await self.patient_medication_repo.list_by_patient(
            patient_id, skip=0, limit=1000
        )
        active_med_count = sum(
            1 for m in all_meds
            if hasattr(m, "status") and str(m.status).upper() in ("ACTIVE",)
        )

        # Phase 7 — safety uses page/page_size
        all_safety, _total_safety = await self.safety_repo.list_evaluations_for_patient(
            patient_id=patient_id, page=1, page_size=1000
        )
        safety_total = len(all_safety)

        # Phase 8
        sym_records, sym_total = await self.symptom_repo.list_by_patient(
            patient_id, limit=1, offset=0
        )
        triage_records, triage_total = await self.triage_repo.list_by_patient(
            patient_id, limit=1, offset=0
        )
        sbar_records, sbar_total = await self.sbar_repo.list_by_patient(
            patient_id, limit=1, offset=0
        )

        # Phase 9
        discharge_records, discharge_total = await self.discharge_repo.list_by_patient(
            patient_id, limit=1, offset=0
        )
        care_plan_records, care_plan_total = await self.care_plan_repo.list_by_patient(
            patient_id, limit=1, offset=0
        )

        # Phase 10
        note_records, note_total = await self.note_repo.list_by_patient(
            patient_id, limit=5, offset=0
        )
        assess_records, assess_total = await self.assessment_repo.list_by_patient(
            patient_id, limit=5, offset=0
        )
        plan_records, plan_total = await self.plan_repo.list_by_patient(
            patient_id, limit=10, offset=0, status=ClinicalPlanStatus.ACTIVE
        )
        _, all_plan_total = await self.plan_repo.list_by_patient(patient_id, limit=1, offset=0)

        summary = WorkspaceSummary(
            total_history_entries=history_total,
            total_allergies=allergy_total,
            total_vitals_entries=vitals_total,
            total_encounters=encounter_total,
            total_documents=doc_total,
            total_prescriptions=rx_total,
            total_active_medications=active_med_count,
            total_safety_results=safety_total,
            total_symptom_intakes=sym_total,
            total_triage_assessments=triage_total,
            total_sbar_records=sbar_total,
            total_discharge_summaries=discharge_total,
            total_care_plans=care_plan_total,
            total_clinical_notes=note_total,
            total_clinical_assessments=assess_total,
            total_clinical_plans=all_plan_total,
        )

        # Recent items for quick-review panel
        recent_notes: list[ClinicalNoteResponse] = [
            self.note_service._to_response(n) for n in note_records
        ]
        recent_assessments: list[ClinicalAssessmentResponse] = [
            self.assessment_service._to_response(a) for a in assess_records
        ]
        active_plans: list[ClinicalPlanResponse] = [
            self.plan_service._to_response(p) for p in plan_records
        ]

        await self.audit_service.record_clinical_workspace_accessed(
            actor_id=clinician_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
        )

        return ClinicalWorkspaceResponse(
            patient=patient_summary,
            encounter_id=encounter_id,
            summary=summary,
            recent_notes=recent_notes,
            recent_assessments=recent_assessments,
            active_plans=active_plans,
            workspace_generated_at=datetime.now(timezone.utc),
            clinician_id=clinician_id,
        )
