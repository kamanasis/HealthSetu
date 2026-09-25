"""Medication Safety Service.

CRITICAL CLINICAL BOUNDARIES:
- Consumes normalized medication data (Phase 6) and patient clinical records (Phase 4).
- Uses abstract MedicationSafetyProvider interface to query authoritative clinical evidence.
- Zero autonomous clinical mutations: NO automatic prescription cancellations, dose adjustments, or allergy creation.
- Provider failures MUST NEVER be converted to false CLEAR results.
- Sensitive patient PHI is minimized before calling external safety providers.
- Strict audit logging without PHI in logs or audit metadata.
"""

import asyncio
from datetime import date, datetime, timezone
import time
import uuid

from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundException, ValidationException
from app.core.logging import get_logger
from app.integrations.medication_safety.base import (
    MedicationSafetyAuthError,
    MedicationSafetyProvider,
    MedicationSafetyProviderError,
    MedicationSafetyTimeoutError,
    MedicationSafetyUnsupportedError,
    ProviderSafetyCheckResult,
)
from app.integrations.medication_safety.registry import get_medication_safety_provider
from app.repositories.allergy_repository import AllergyRepository
from app.repositories.clinical_history_repository import ClinicalHistoryRepository
from app.repositories.medication_repository import MedicationRepository
from app.repositories.medication_safety_repository import (
    CheckSummaryRecord,
    MedicationSafetyRepository,
    SafetyAlertRecord,
    SafetyEvaluationRecord,
)
from app.repositories.patient_medication_repository import PatientMedicationRepository
from app.repositories.patient_repository import PatientRepository
from app.schemas.allergy import AllergyStatus
from app.schemas.clinical_history import ConditionStatus
from app.schemas.medication import PatientMedicationStatus
from app.schemas.medication_safety import (
    CLINICAL_SAFETY_DISCLAIMER,
    CheckTypeSummary,
    MedicationContextSource,
    PatientSafetyCheckRequest,
    ProspectiveMedicationsCheckRequest,
    SafetyAlert,
    SafetyAlertSeverity,
    SafetyCheckType,
    SafetyEvaluationListResponse,
    SafetyEvaluationResponse,
    SafetyEvaluationStatus,
    SafetyEvaluationSummaryItem,
    SafetyMedicationInput,
    SafetyPatientContext,
)
from app.services.audit_service import AuditService

logger = get_logger("medication_safety_service")


class MedicationSafetyService:
    """Service orchestrating medication safety evaluations, context collection, and persistence."""

    def __init__(
        self,
        safety_repo: MedicationSafetyRepository,
        patient_medication_repo: PatientMedicationRepository,
        medication_repo: MedicationRepository,
        allergy_repo: AllergyRepository,
        clinical_history_repo: ClinicalHistoryRepository,
        patient_repo: PatientRepository,
        audit_service: AuditService,
        provider: MedicationSafetyProvider | None = None,
        settings: Settings | None = None,
    ):
        self.safety_repo = safety_repo
        self.patient_medication_repo = patient_medication_repo
        self.medication_repo = medication_repo
        self.allergy_repo = allergy_repo
        self.clinical_history_repo = clinical_history_repo
        self.patient_repo = patient_repo
        self.audit_service = audit_service
        self.settings = settings or get_settings()
        self.provider = provider or get_medication_safety_provider(settings=self.settings)

    async def evaluate_patient_safety(
        self,
        patient_id: str,
        request: PatientSafetyCheckRequest,
        actor_id: str,
    ) -> SafetyEvaluationResponse:
        """Evaluate safety for a patient's active or selected medications."""
        evaluation_id = f"eval-{uuid.uuid4().hex[:12]}"
        start_time = time.perf_counter()

        # 1. Collect medications
        medications = await self._collect_patient_medications(
            patient_id=patient_id,
            medication_ids=request.medication_ids,
            context_source=request.medication_context,
        )

        # 2. Collect minimized patient clinical context
        patient_context, context_counts = await self._collect_patient_context(patient_id)

        # 3. Audit check started (Counts & IDs only — NO PHI)
        check_types_str = [ct.value for ct in (request.requested_check_types or list(SafetyCheckType))]
        await self.audit_service.record_medication_safety_check_started(
            actor_id=actor_id,
            patient_id=patient_id,
            evaluation_id=evaluation_id,
            provider=self.provider.provider_name,
            check_types=check_types_str,
            medication_count=len(medications),
        )

        # If no medications are present, return a clean CLEAR evaluation immediately
        if not medications:
            now = datetime.now(timezone.utc)
            record = SafetyEvaluationRecord(
                id=evaluation_id,
                patient_id=patient_id,
                medication_context=request.medication_context,
                status=SafetyEvaluationStatus.CLEAR,
                provider=self.provider.provider_name,
                provider_version=self.provider.provider_version,
                ruleset_version=self.provider.ruleset_version,
                medications_evaluated_count=0,
                patient_context_used=context_counts,
                disclaimer=CLINICAL_SAFETY_DISCLAIMER,
                checked_at=now,
                created_at=now,
            )
            await self.safety_repo.save_evaluation(record, [], [])
            duration_ms = (time.perf_counter() - start_time) * 1000
            await self.audit_service.record_medication_safety_check_completed(
                actor_id=actor_id,
                patient_id=patient_id,
                evaluation_id=evaluation_id,
                provider=self.provider.provider_name,
                status=SafetyEvaluationStatus.CLEAR.value,
                alerts_count=0,
                duration_ms=duration_ms,
            )
            return self._build_response(record, [], [])

        # 4. Invoke provider with retry
        return await self._execute_and_persist_evaluation(
            evaluation_id=evaluation_id,
            patient_id=patient_id,
            medications=medications,
            patient_context=patient_context,
            context_counts=context_counts,
            medication_context=request.medication_context,
            requested_checks=request.requested_check_types,
            actor_id=actor_id,
            start_time=start_time,
        )

    async def evaluate_prospective_medications(
        self,
        patient_id: str,
        request: ProspectiveMedicationsCheckRequest,
        actor_id: str,
    ) -> SafetyEvaluationResponse:
        """Evaluate prospective/new medications, optionally against existing active medications."""
        evaluation_id = f"eval-{uuid.uuid4().hex[:12]}"
        start_time = time.perf_counter()

        medications_to_check: list[SafetyMedicationInput] = list(request.medications)

        if request.include_current_medications:
            current_meds = await self._collect_patient_medications(
                patient_id=patient_id,
                medication_ids=None,
                context_source=MedicationContextSource.CURRENT_MEDICATIONS,
            )
            medications_to_check.extend(current_meds)

        # Collect clinical context
        patient_context, context_counts = await self._collect_patient_context(patient_id)

        # Audit check started
        check_types_str = [ct.value for ct in (request.requested_check_types or list(SafetyCheckType))]
        await self.audit_service.record_medication_safety_check_started(
            actor_id=actor_id,
            patient_id=patient_id,
            evaluation_id=evaluation_id,
            provider=self.provider.provider_name,
            check_types=check_types_str,
            medication_count=len(medications_to_check),
        )

        return await self._execute_and_persist_evaluation(
            evaluation_id=evaluation_id,
            patient_id=patient_id,
            medications=medications_to_check,
            patient_context=patient_context,
            context_counts=context_counts,
            medication_context=MedicationContextSource.NEW_PRESCRIPTION,
            requested_checks=request.requested_check_types,
            actor_id=actor_id,
            start_time=start_time,
        )

    async def get_evaluation(
        self,
        patient_id: str,
        evaluation_id: str,
        actor_id: str,
    ) -> SafetyEvaluationResponse:
        """Retrieve historical safety evaluation by ID."""
        record = await self.safety_repo.get_evaluation(evaluation_id)
        if not record or record.patient_id != patient_id:
            raise NotFoundException(f"Safety evaluation '{evaluation_id}' not found.")

        alerts = await self.safety_repo.get_alerts_for_evaluation(evaluation_id)
        summaries = await self.safety_repo.get_summaries_for_evaluation(evaluation_id)

        await self.audit_service.record_medication_safety_result_viewed(
            actor_id=actor_id,
            patient_id=patient_id,
            evaluation_id=evaluation_id,
        )

        return self._build_response(record, alerts, summaries)

    async def list_evaluations(
        self,
        patient_id: str,
        status: SafetyEvaluationStatus | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> SafetyEvaluationListResponse:
        """List historical evaluations for patient with pagination and filtering."""
        records, total = await self.safety_repo.list_evaluations_for_patient(
            patient_id=patient_id,
            status=status,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
        )

        items: list[SafetyEvaluationSummaryItem] = []
        for r in records:
            alerts = await self.safety_repo.get_alerts_for_evaluation(r.id)
            highest_sev = None
            if alerts:
                severity_order = [
                    SafetyAlertSeverity.CRITICAL,
                    SafetyAlertSeverity.MAJOR,
                    SafetyAlertSeverity.MODERATE,
                    SafetyAlertSeverity.MINOR,
                    SafetyAlertSeverity.INFO,
                ]
                for s in severity_order:
                    if any(a.severity == s for a in alerts):
                        highest_sev = s
                        break

            items.append(
                SafetyEvaluationSummaryItem(
                    evaluation_id=r.id,
                    patient_id=r.patient_id,
                    status=r.status,
                    medication_context=r.medication_context,
                    checked_at=r.checked_at,
                    provider=r.provider,
                    alert_count=len(alerts),
                    highest_severity=highest_sev,
                )
            )

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return SafetyEvaluationListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    # -----------------------------------------------------------------------
    # Provider Execution & Persistence
    # -----------------------------------------------------------------------

    async def _execute_and_persist_evaluation(
        self,
        evaluation_id: str,
        patient_id: str,
        medications: list[SafetyMedicationInput],
        patient_context: SafetyPatientContext,
        context_counts: dict[str, int],
        medication_context: MedicationContextSource,
        requested_checks: list[SafetyCheckType] | None,
        actor_id: str,
        start_time: float,
    ) -> SafetyEvaluationResponse:
        """Execute checks with retry policy and ensure provider failure NEVER yields false CLEAR."""
        now = datetime.now(timezone.utc)
        retries = self.settings.MEDICATION_SAFETY_MAX_RETRIES

        result: ProviderSafetyCheckResult | None = None
        last_error: Exception | None = None

        for attempt in range(retries + 1):
            try:
                result = await self.provider.evaluate_safety(
                    medications=medications,
                    patient_context=patient_context,
                    requested_checks=requested_checks,
                )
                break
            except (MedicationSafetyTimeoutError, MedicationSafetyProviderError) as exc:
                last_error = exc
                if getattr(exc, "is_transient", False) and attempt < retries:
                    await asyncio.sleep(0.05 * (2**attempt))
                    continue
                break
            except MedicationSafetyAuthError as exc:
                last_error = exc
                break
            except Exception as exc:
                last_error = exc
                break

        # Handle Provider Failures: CRITICAL CLINICAL SAFETY RULE
        # Never convert provider failure to false CLEAR
        if result is None:
            duration_ms = (time.perf_counter() - start_time) * 1000
            error_cat = (
                "TIMEOUT"
                if isinstance(last_error, MedicationSafetyTimeoutError)
                else "AUTH_ERROR"
                if isinstance(last_error, MedicationSafetyAuthError)
                else "PROVIDER_ERROR"
            )

            logger.error(
                "Medication safety check failed",
                extra={
                    "evaluation_id": evaluation_id,
                    "provider": self.provider.provider_name,
                    "error_category": error_cat,
                },
            )

            await self.audit_service.record_medication_safety_check_failed(
                actor_id=actor_id,
                patient_id=patient_id,
                evaluation_id=evaluation_id,
                provider=self.provider.provider_name,
                error_category=error_cat,
            )

            error_summary = CheckSummaryRecord(
                id=f"sum-{uuid.uuid4().hex[:8]}",
                evaluation_id=evaluation_id,
                check_type=SafetyCheckType.OTHER,
                supported=False,
                status=SafetyEvaluationStatus.UNKNOWN,
                alert_count=0,
                note=f"Safety evaluation failed: {error_cat}. Clinical safety status is UNKNOWN.",
                created_at=now,
            )

            eval_record = SafetyEvaluationRecord(
                id=evaluation_id,
                patient_id=patient_id,
                medication_context=medication_context,
                status=SafetyEvaluationStatus.UNKNOWN,
                provider=self.provider.provider_name,
                provider_version=self.provider.provider_version,
                ruleset_version=self.provider.ruleset_version,
                medications_evaluated_count=len(medications),
                patient_context_used=context_counts,
                disclaimer=CLINICAL_SAFETY_DISCLAIMER,
                checked_at=now,
                created_at=now,
            )
            await self.safety_repo.save_evaluation(eval_record, [], [error_summary])
            return self._build_response(eval_record, [], [error_summary])

        # Success path
        duration_ms = (time.perf_counter() - start_time) * 1000
        await self.audit_service.record_medication_safety_check_completed(
            actor_id=actor_id,
            patient_id=patient_id,
            evaluation_id=evaluation_id,
            provider=result.provider_name,
            status=result.status.value,
            alerts_count=len(result.alerts),
            duration_ms=duration_ms,
        )

        alert_records = [
            SafetyAlertRecord(
                id=a.alert_id,
                evaluation_id=evaluation_id,
                check_type=a.check_type,
                severity=a.severity,
                title=a.title,
                description=a.description,
                medications_involved=a.medications_involved,
                clinical_context_involved=a.clinical_context_involved,
                evidence=a.evidence,
                source=a.source,
                provider_rule_id=a.provider_rule_id,
                created_at=now,
            )
            for a in result.alerts
        ]

        summary_records = [
            CheckSummaryRecord(
                id=f"sum-{uuid.uuid4().hex[:8]}",
                evaluation_id=evaluation_id,
                check_type=s.check_type,
                supported=s.supported,
                status=s.status,
                alert_count=s.alert_count,
                note=s.note,
                created_at=now,
            )
            for s in result.check_summaries
        ]

        eval_record = SafetyEvaluationRecord(
            id=evaluation_id,
            patient_id=patient_id,
            medication_context=medication_context,
            status=result.status,
            provider=result.provider_name,
            provider_version=result.provider_version,
            ruleset_version=result.ruleset_version,
            medications_evaluated_count=len(medications),
            patient_context_used=context_counts,
            disclaimer=CLINICAL_SAFETY_DISCLAIMER,
            checked_at=now,
            created_at=now,
        )

        await self.safety_repo.save_evaluation(eval_record, alert_records, summary_records)
        return self._build_response(eval_record, alert_records, summary_records)

    # -----------------------------------------------------------------------
    # Context Assembly & Data Minimization
    # -----------------------------------------------------------------------

    async def _collect_patient_medications(
        self,
        patient_id: str,
        medication_ids: list[str] | None,
        context_source: MedicationContextSource,
    ) -> list[SafetyMedicationInput]:
        """Collect and normalize patient medications for safety analysis."""
        status_filter = (
            None
            if context_source == MedicationContextSource.FULL_MEDICATION_REVIEW
            else PatientMedicationStatus.ACTIVE
        )

        records = await self.patient_medication_repo.list_by_patient(
            patient_id=patient_id,
            status_filter=status_filter,
            limit=100,
        )

        if medication_ids is not None:
            id_set = set(medication_ids)
            records = [r for r in records if r.id in id_set]

        inputs: list[SafetyMedicationInput] = []
        for r in records:
            name = r.drug_name_raw
            system = None
            code = None
            strength = r.strength_raw
            dosage_form = r.dosage_form_raw
            route = r.route_raw

            if r.normalized_medication_id:
                canonical = await self.medication_repo.get_by_id(r.normalized_medication_id)
                if canonical:
                    name = canonical.canonical_name
                    system = canonical.terminology_system
                    code = canonical.terminology_code
                    strength = canonical.strength or strength
                    dosage_form = canonical.dosage_form or dosage_form
                    route = canonical.route or route

            inputs.append(
                SafetyMedicationInput(
                    medication_id=r.id,
                    name=name,
                    terminology_system=system,
                    terminology_code=code,
                    strength=strength,
                    dosage_form=dosage_form,
                    route=route,
                    frequency=r.frequency_raw,
                    duration=r.duration_raw,
                    status=r.status.value,
                )
            )

        return inputs

    async def _collect_patient_context(
        self, patient_id: str
    ) -> tuple[SafetyPatientContext, dict[str, int]]:
        """Collect minimized clinical context without sending unnecessary PHI."""
        # 1. Active Allergies
        allergy_records = await self.allergy_repo.list_by_patient(patient_id, include_archived=False)
        active_allergies = [
            {"id": a.id, "allergen": a.allergen, "severity": a.severity.value if hasattr(a.severity, "value") else str(a.severity)}
            for a in allergy_records
            if a.status == AllergyStatus.ACTIVE
        ]

        # 2. Active Conditions
        condition_records = await self.clinical_history_repo.list_by_patient(patient_id, include_archived=False)
        active_conditions = [
            {"id": c.id, "diagnosis": c.description, "status": c.condition_status.value}
            for c in condition_records
            if c.condition_status == ConditionStatus.ACTIVE
        ]

        # 3. Patient age and sex (NO name, NO phone, NO email)
        patient_rec = await self.patient_repo.get_by_id(patient_id)
        age_years = None
        sex_str = None
        if patient_rec:
            sex_str = patient_rec.sex.value if hasattr(patient_rec.sex, "value") else str(patient_rec.sex)
            if patient_rec.date_of_birth:
                today = date.today()
                dob = patient_rec.date_of_birth
                age_years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        patient_context = SafetyPatientContext(
            allergies=active_allergies,
            conditions=active_conditions,
            vitals=[],
            age_years=age_years,
            sex=sex_str,
        )

        counts = {
            "allergies_evaluated": len(active_allergies),
            "conditions_evaluated": len(active_conditions),
            "age_included": 1 if age_years is not None else 0,
        }

        return patient_context, counts

    def _build_response(
        self,
        record: SafetyEvaluationRecord,
        alerts: list[SafetyAlertRecord],
        summaries: list[CheckSummaryRecord],
    ) -> SafetyEvaluationResponse:
        """Assemble API response model."""
        return SafetyEvaluationResponse(
            evaluation_id=record.id,
            patient_id=record.patient_id,
            status=record.status,
            medication_context=record.medication_context,
            checked_at=record.checked_at,
            provider=record.provider,
            provider_version=record.provider_version,
            ruleset_version=record.ruleset_version,
            alerts=[
                SafetyAlert(
                    alert_id=a.id,
                    check_type=a.check_type,
                    severity=a.severity,
                    title=a.title,
                    description=a.description,
                    medications_involved=a.medications_involved,
                    clinical_context_involved=a.clinical_context_involved,
                    evidence=a.evidence,
                    source=a.source,
                    provider_rule_id=a.provider_rule_id,
                )
                for a in alerts
            ],
            check_summaries=[
                CheckTypeSummary(
                    check_type=s.check_type,
                    supported=s.supported,
                    status=s.status,
                    alert_count=s.alert_count,
                    note=s.note,
                )
                for s in summaries
            ],
            medications_evaluated_count=record.medications_evaluated_count,
            patient_context_used=record.patient_context_used,
            disclaimer=record.disclaimer,
        )
