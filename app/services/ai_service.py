"""AI Orchestration Service (Phase 14).

Coordinates task execution, input sanitization, provider delegation,
structured output validation, factual grounding, and clinical review workflows.

Architectural boundaries:
- AI is an orchestration layer, NOT a clinical decision engine.
- AI output is NOT clinical truth.
- AI confidence is NOT clinical certainty.
- AI must NOT independently diagnose, prescribe, triage, or select transfer facilities.
- AI output must enter REVIEW_REQUIRED status and be clinician-verified before clinical acceptance.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional, Type
from uuid import uuid4
from pydantic import BaseModel

from app.core.config import settings
from app.core.exceptions import (
    AIDisabledException,
    AIGroundingFailedException,
    AIOutputInvalidException,
    AIProviderTimeoutException,
    AIProviderUnavailableException,
    AITaskFailedException,
    AITaskNotSupportedException,
    AIVerificationRequiredException,
    ForbiddenException,
    PromptInjectionDetectedException,
)
from app.integrations.ai.base import AIProvider
from app.integrations.ai.client import get_ai_provider
from app.integrations.ai.models import AIProviderRequest, AIProviderResponse
from app.integrations.ai.security import AISecurityValidator
from app.prompts.care_plan import build_care_plan_prompt
from app.prompts.clinical_documentation import build_clinical_documentation_prompt
from app.prompts.discharge import build_discharge_prompt
from app.prompts.document_extraction import build_document_extraction_prompt
from app.prompts.explanation import build_explanation_prompt
from app.prompts.sbar import build_sbar_prompt
from app.prompts.summarization import build_summarization_prompt
from app.repositories.ai_repository import AIRepository
from app.schemas.ai import (
    AIConfidenceLevel,
    AIGroundingStatus,
    AISourceReference,
    AITaskStatus,
    AITaskType,
    AIUsageMetadata,
    AIVerificationStatus,
)
from app.schemas.ai_results import (
    AIResultRecord,
    AIVerificationRequest,
    CarePlanOrganizationResult,
    ClinicalNoteDraftResult,
    ClinicalSummaryResult,
    DischargeOrganizationResult,
    DocumentExtractionResult,
    PatientExplanationResult,
    SBARAssistanceResult,
    StructuredClassificationResult,
)
from app.schemas.ai_tasks import AITaskCreateRequest, AITaskRecord
from app.schemas.audit import AuditEventType
from app.schemas.auth import UserRole
from app.schemas.user import AuthenticatedUserContext
from app.services.ai_provenance_service import AIProvenanceService
from app.services.ai_task_service import AITaskService
from app.services.ai_usage_service import AIUsageService
from app.services.ai_validation_service import AIValidationService
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)


# Schema mapping for approved tasks
TASK_SCHEMA_MAP: Dict[AITaskType, Type[BaseModel]] = {
    AITaskType.DOCUMENT_EXTRACTION: DocumentExtractionResult,
    AITaskType.DOCUMENT_SUMMARIZATION: ClinicalSummaryResult,
    AITaskType.CLINICAL_SUMMARY: ClinicalSummaryResult,
    AITaskType.PATIENT_EXPLANATION: PatientExplanationResult,
    AITaskType.SBAR_ASSISTANCE: SBARAssistanceResult,
    AITaskType.DISCHARGE_EXTRACTION: DischargeOrganizationResult,
    AITaskType.CARE_PLAN_ORGANIZATION: CarePlanOrganizationResult,
    AITaskType.CLINICAL_NOTE_DRAFT: ClinicalNoteDraftResult,
    AITaskType.STRUCTURED_CLASSIFICATION: StructuredClassificationResult,
}


class AIService:
    """Core AI Orchestrator implementing HealthSetu Phase 14 specifications."""

    def __init__(
        self,
        repository: AIRepository,
        audit_service: AuditService,
        task_service: Optional[AITaskService] = None,
        validation_service: Optional[AIValidationService] = None,
        provenance_service: Optional[AIProvenanceService] = None,
        usage_service: Optional[AIUsageService] = None,
        provider: Optional[AIProvider] = None,
    ) -> None:
        self.repository = repository
        self.audit_service = audit_service
        self.task_service = task_service or AITaskService(repository)
        self.validation_service = validation_service or AIValidationService()
        self.provenance_service = provenance_service or AIProvenanceService()
        self.usage_service = usage_service or AIUsageService(repository)
        self._provider = provider

    def _get_provider(self) -> AIProvider:
        if self._provider is not None:
            return self._provider
        return get_ai_provider()

    def _ensure_ai_enabled(self) -> None:
        if not settings.AI_ENABLED:
            raise AIDisabledException("AI intelligence layer is disabled by system configuration.")

    def _get_prompt(self, task_type: AITaskType, source_text: str, context: Optional[Dict[str, Any]] = None) -> tuple[str, str, str]:
        """Return (system_prompt, user_prompt, prompt_version)."""
        ctx = context or {}
        if task_type == AITaskType.DOCUMENT_EXTRACTION:
            return build_document_extraction_prompt(source_text, ctx.get("document_type"))
        elif task_type in (AITaskType.DOCUMENT_SUMMARIZATION, AITaskType.CLINICAL_SUMMARY):
            return build_summarization_prompt(source_text, ctx.get("focus_area"))
        elif task_type == AITaskType.PATIENT_EXPLANATION:
            return build_explanation_prompt(source_text, ctx.get("reading_level", "Grade 6"))
        elif task_type == AITaskType.SBAR_ASSISTANCE:
            return build_sbar_prompt(
                situation_facts=ctx.get("situation", ""),
                background_facts=ctx.get("background", ""),
                assessment_facts=ctx.get("assessment", ""),
                recommendation_facts=ctx.get("recommendation", ""),
            )
        elif task_type == AITaskType.DISCHARGE_EXTRACTION:
            return build_discharge_prompt(source_text)
        elif task_type == AITaskType.CARE_PLAN_ORGANIZATION:
            return build_care_plan_prompt(source_text)
        elif task_type == AITaskType.CLINICAL_NOTE_DRAFT:
            return build_clinical_documentation_prompt(source_text, ctx.get("encounter_type", "outpatient"))
        elif task_type == AITaskType.STRUCTURED_CLASSIFICATION:
            # Classification prompt
            sys_p = "You are a healthcare classification assistant. Provide non-authoritative categorization based strictly on source facts."
            user_p = f"Source text to classify:\n<<<SOURCE_START>>>\n{source_text}\n<<<SOURCE_END>>>"
            return sys_p, user_p, "1.0.0"
        else:
            raise AITaskNotSupportedException(f"Task type '{task_type}' is not supported.")

    async def submit_task(
        self,
        request: AITaskCreateRequest,
        user_context: AuthenticatedUserContext,
        source_content: Optional[str] = None,
    ) -> AITaskRecord:
        """Create and queue an AI task, verifying authorization and sanitizing input."""
        self._ensure_ai_enabled()

        if request.task_type not in TASK_SCHEMA_MAP:
            raise AITaskNotSupportedException(f"Task type '{request.task_type}' is not allowed or supported.")

        # PHI Minimization & Prompt Injection check
        content_to_check = (source_content or "") + " " + json.dumps(request.input_context or {})
        AISecurityValidator.detect_prompt_injection(content_to_check)

        # Sanitize source content
        sanitized_content = AISecurityValidator.sanitize_untrusted_text(source_content or "")

        # Create task record
        task = await self.task_service.create_task(
            request=request,
            creator_id=user_context.user_id,
            organization_id=getattr(user_context, "organization_id", None),
            source_content=sanitized_content,
        )

        await self.audit_service.record(
            event_type=AuditEventType.AI_TASK_CREATED,
            outcome="ALLOW",
            actor_id=user_context.user_id,
            action=AuditEventType.AI_TASK_CREATED.value,
            resource_type="ai_task",
            resource_id=task.id,
            metadata={"task_type": task.task_type.value},
        )

        return task

    async def execute_task(
        self,
        task_id: str,
        user_context: AuthenticatedUserContext,
    ) -> AIResultRecord:
        """Execute a queued AI task through the complete validation and grounding pipeline."""
        self._ensure_ai_enabled()

        task = await self.task_service.get_task(task_id)
        if task.status not in (AITaskStatus.QUEUED, AITaskStatus.PROCESSING):
            # Already completed or failed
            res = await self.repository.get_result_by_task_id(task.id)
            if res:
                return res

        await self.task_service.mark_processing(task)

        await self.audit_service.record(
            event_type=AuditEventType.AI_TASK_STARTED,
            outcome="ALLOW",
            actor_id=user_context.user_id,
            action=AuditEventType.AI_TASK_STARTED.value,
            resource_type="ai_task",
            resource_id=task.id,
            metadata={"task_type": task.task_type.value},
        )

        target_schema = TASK_SCHEMA_MAP[task.task_type]
        source_text = task.source_content or json.dumps(task.input_context or {})

        sys_prompt, user_prompt, prompt_version = self._get_prompt(
            task_type=task.task_type,
            source_text=source_text,
            context=task.input_context,
        )

        provider = self._get_provider()
        provider_req = AIProviderRequest(
            task_type=task.task_type,
            system_prompt=sys_prompt,
            user_prompt=user_prompt,
            model=settings.AI_MODEL or provider.model_name,
            temperature=settings.AI_TEMPERATURE,
            max_tokens=settings.AI_MAX_OUTPUT_TOKENS,
        )

        try:
            provider_resp = await provider.generate_structured(provider_req, schema=target_schema)
        except (AIProviderTimeoutException, AIProviderUnavailableException) as exc:
            logger.error("AI provider error executing task %s: %s", task.id, exc)
            
            # Check for deterministic fallback
            fallback_res = self._attempt_deterministic_fallback(task, str(exc))
            if fallback_res:
                await self.task_service.mark_completed(task, fallback_res.id)
                return fallback_res

            # Retry handling
            can_retry = await self.task_service.record_retry(task, str(exc))
            if not can_retry:
                await self.audit_service.record(
                    event_type=AuditEventType.AI_PROVIDER_ERROR,
                    outcome="FAILURE",
                    actor_id=user_context.user_id,
                    action=AuditEventType.AI_PROVIDER_ERROR.value,
                    resource_type="ai_task",
                    resource_id=task.id,
                    metadata={"error": str(exc)},
                )
            raise

        # Output Safety Boundaries
        parsed_payload = provider_resp.parsed_json or {}
        self.validation_service.enforce_safety_boundaries(parsed_payload)

        # Grounding Validation
        grounding_status, unsupported_claims = self.validation_service.validate_grounding(
            parsed_output=parsed_payload,
            source_text=source_text,
            task_type=task.task_type,
        )

        if grounding_status == AIGroundingStatus.UNSUPPORTED_CONTENT:
            await self.audit_service.record(
                event_type=AuditEventType.AI_GROUNDING_VALIDATION_FAILED,
                outcome="DENY",
                actor_id=user_context.user_id,
                action=AuditEventType.AI_GROUNDING_VALIDATION_FAILED.value,
                resource_type="ai_task",
                resource_id=task.id,
                metadata={"unsupported_claims_count": len(unsupported_claims)},
            )

        # Extract citations
        raw_citations = parsed_payload.get("source_references", [])
        parsed_citations = [
            AISourceReference(**c) if isinstance(c, dict) else c for c in raw_citations
        ]

        # Record Provenance
        provenance = self.provenance_service.create_provenance_record(
            task_type=task.task_type,
            source_text=source_text,
            output_payload=parsed_payload,
            prompt_version=prompt_version,
            task_version=task.task_version,
            provider=provider_resp.provider,
            model=provider_resp.model,
            model_version=provider_resp.model_version,
            citations=parsed_citations,
        )

        # Record Operational Usage without PHI
        usage_meta = await self.usage_service.record_usage(
            task_id=task.id,
            task_type=task.task_type,
            provider=provider_resp.provider,
            model=provider_resp.model,
            prompt_tokens=provider_resp.prompt_tokens,
            completion_tokens=provider_resp.completion_tokens,
            total_tokens=provider_resp.total_tokens,
            latency_ms=provider_resp.latency_ms,
            success=True,
        )

        # Build Result Record
        # MANDATORY CLINICAL SAFETY: Verification status is REVIEW_REQUIRED
        result_id = f"ai-res-{uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        result_record = AIResultRecord(
            id=result_id,
            task_id=task.id,
            task_type=task.task_type,
            verification_status=AIVerificationStatus.REVIEW_REQUIRED,
            grounding_status=grounding_status,
            confidence=AIConfidenceLevel(parsed_payload.get("confidence", AIConfidenceLevel.HIGH.value)),
            structured_output=parsed_payload,
            provenance=provenance,
            usage=usage_meta,
            unsupported_claims=unsupported_claims,
            created_at=now,
            updated_at=now,
        )

        await self.repository.create_result(result_record)
        await self.task_service.mark_completed(task, result_id)

        await self.audit_service.record(
            event_type=AuditEventType.AI_TASK_COMPLETED,
            outcome="ALLOW",
            actor_id=user_context.user_id,
            action=AuditEventType.AI_TASK_COMPLETED.value,
            resource_type="ai_result",
            resource_id=result_record.id,
            metadata={"grounding_status": grounding_status.value},
        )

        return result_record

    def _attempt_deterministic_fallback(self, task: AITaskRecord, reason: str) -> Optional[AIResultRecord]:
        """Execute deterministic fallback for tasks where fallback is clinically safe."""
        if task.task_type == AITaskType.SBAR_ASSISTANCE:
            # Deterministic SBAR fallback
            ctx = task.input_context or {}
            fallback_payload = {
                "situation": ctx.get("situation", "Patient under observation"),
                "background": ctx.get("background", "See clinical history in EHR"),
                "assessment": ctx.get("assessment", "Clinical assessment pending"),
                "recommendation": ctx.get("recommendation", "Review patient in person"),
                "source_references": [],
                "confidence": AIConfidenceLevel.UNKNOWN.value,
            }
            result_id = f"ai-res-{uuid4().hex[:12]}"
            now = datetime.now(timezone.utc)
            provenance = self.provenance_service.create_provenance_record(
                task_type=task.task_type,
                source_text=task.source_content or "",
                output_payload=fallback_payload,
                prompt_version="fallback-1.0.0",
                task_version="1.0.0",
                provider="deterministic_fallback",
                model="deterministic",
                model_version="1.0",
                citations=[],
            )
            return AIResultRecord(
                id=result_id,
                task_id=task.id,
                task_type=task.task_type,
                verification_status=AIVerificationStatus.REVIEW_REQUIRED,
                grounding_status=AIGroundingStatus.GROUNDED,
                confidence=AIConfidenceLevel.UNKNOWN,
                structured_output=fallback_payload,
                provenance=provenance,
                created_at=now,
                updated_at=now,
            )
        return None

    async def verify_result(
        self,
        result_id: str,
        verification_req: AIVerificationRequest,
        user_context: AuthenticatedUserContext,
    ) -> AIResultRecord:
        """Clinician verification boundary: verify, correct, or reject AI result."""
        # Only authenticated clinicians can verify AI output
        if user_context.role not in (UserRole.DOCTOR, UserRole.ADMIN):
            raise ForbiddenException("Only authorized clinicians can verify or correct AI results.")


        result = await self.repository.get_result(result_id)
        if not result:
            raise AIVerificationRequiredException(f"AI result with ID '{result_id}' was not found.")

        result.verification_status = verification_req.verification_status
        result.verified_by = user_context.user_id
        result.verified_at = datetime.now(timezone.utc)
        result.verification_notes = verification_req.notes

        if verification_req.corrected_output:
            result.corrected_output = verification_req.corrected_output
            result.verification_status = AIVerificationStatus.CORRECTED

        await self.repository.update_result(result)

        audit_event = AuditEventType.AI_RESULT_VERIFIED
        if result.verification_status == AIVerificationStatus.CORRECTED:
            audit_event = AuditEventType.AI_RESULT_CORRECTED
        elif result.verification_status == AIVerificationStatus.REJECTED:
            audit_event = AuditEventType.AI_RESULT_REJECTED

        await self.audit_service.record(
            event_type=audit_event,
            outcome="ALLOW",
            actor_id=user_context.user_id,
            action=audit_event.value,
            resource_type="ai_result",
            resource_id=result.id,
            metadata={"status": result.verification_status.value},
        )

        return result
