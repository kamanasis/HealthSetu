"""Audit event service — structured security/access event recording.

This service is the single entry point for recording audit events.
It enforces the PHI-exclusion policy before handing off to the repository.

SEPARATION OF CONCERNS
=======================
Application logging   → operational, debugging (app/core/logging.py)
Audit events          → accountability, access decisions, consent lifecycle (here)

These MUST remain separate. Application log rotation or level changes
must NOT affect the audit trail.
"""

from app.core.logging import get_logger, request_id_ctx_var
from app.repositories.audit_repository import AuditRepository
from app.schemas.audit import AuditEventRecord, AuditEventType
from app.services.base import BaseService

logger = get_logger("app.audit_service")

# Fields that must NEVER appear in audit event metadata
_FORBIDDEN_METADATA_KEYS: frozenset[str] = frozenset({
    "password", "token", "access_token", "refresh_token", "secret",
    "api_key", "authorization", "cookie",
    # Clinical PHI safeguards
    "diagnosis", "diagnoses", "prescription", "prescriptions",
    "medication", "medications", "history", "medical_history",
    "clinical_notes", "document_content", "patient_data", "symptoms",
})


def _sanitize_metadata(metadata: dict | None) -> dict | None:
    """Remove forbidden keys from audit event metadata before persisting."""
    if not metadata:
        return metadata
    return {k: v for k, v in metadata.items() if k.lower() not in _FORBIDDEN_METADATA_KEYS}


class AuditService(BaseService[AuditRepository]):
    """Service for recording immutable security and access audit events."""

    def __init__(self, audit_repository: AuditRepository) -> None:
        super().__init__(repository=audit_repository)
        self.audit_repo = audit_repository

    async def record(
        self,
        event_type: AuditEventType,
        outcome: str,
        actor_id: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        reason_code: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Record an audit event.

        PHI exclusion is enforced on metadata before persistence.
        Tokens and secrets are NEVER valid metadata fields.
        """
        clean_metadata = _sanitize_metadata(metadata)
        event = AuditEventRecord(
            event_type=event_type,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            reason_code=reason_code,
            request_id=request_id_ctx_var.get(),
            metadata=clean_metadata,
        )
        await self.audit_repo.append(event)

    async def record_access_granted(
        self,
        actor_id: str,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Record a successful authorization grant."""
        await self.record(
            event_type=AuditEventType.AUTHZ_ACCESS_GRANTED,
            outcome="ALLOW",
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata,
        )

    async def record_access_denied(
        self,
        actor_id: str | None,
        action: str,
        reason_code: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Record an authorization denial."""
        await self.record(
            event_type=AuditEventType.AUTHZ_ACCESS_DENIED,
            outcome="DENY",
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            reason_code=reason_code,
            metadata=metadata,
        )

    async def record_consent_created(
        self,
        actor_id: str,
        consent_id: str,
        patient_id: str,
        grantee_id: str,
        purpose: str,
        scope: str,
    ) -> None:
        """Record a consent creation event."""
        await self.record(
            event_type=AuditEventType.CONSENT_CREATED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="consent:create",
            resource_type="consent",
            resource_id=consent_id,
            metadata={
                "patient_id": patient_id,
                "grantee_id": grantee_id,
                "purpose": purpose,
                "scope": scope,
            },
        )

    async def record_consent_revoked(
        self,
        actor_id: str,
        consent_id: str,
        reason: str | None = None,
    ) -> None:
        """Record a consent revocation event."""
        await self.record(
            event_type=AuditEventType.CONSENT_REVOKED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="consent:revoke",
            resource_type="consent",
            resource_id=consent_id,
            metadata={"reason": reason} if reason else None,
        )

    async def record_consent_check(
        self,
        actor_id: str,
        allowed: bool,
        purpose: str,
        scope: str,
        consent_id: str | None = None,
        reason_code: str | None = None,
    ) -> None:
        """Record the result of a consent check."""
        await self.record(
            event_type=(
                AuditEventType.CONSENT_CHECK_PASSED
                if allowed
                else AuditEventType.CONSENT_CHECK_FAILED
            ),
            outcome="ALLOW" if allowed else "DENY",
            actor_id=actor_id,
            action="consent:check",
            resource_type="consent",
            resource_id=consent_id,
            reason_code=reason_code,
            metadata={"purpose": purpose, "scope": scope},
        )

    # -----------------------------------------------------------------------
    # Phase 4: Clinical record audit helpers
    # -----------------------------------------------------------------------

    async def record_clinical_record_viewed(
        self,
        actor_id: str,
        patient_id: str,
        resource_type: str = "patient",
    ) -> None:
        """Audit: clinical record accessed."""
        await self.record(
            event_type=AuditEventType.CLINICAL_RECORD_VIEWED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="clinical_record:read",
            resource_type=resource_type,
            resource_id=patient_id,
        )

    async def record_patient_profile_updated(
        self,
        actor_id: str,
        patient_id: str,
        updated_fields: list[str],
    ) -> None:
        """Audit: patient profile updated (field names only, no values)."""
        await self.record(
            event_type=AuditEventType.PATIENT_PROFILE_UPDATED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="patient:update",
            resource_type="patient",
            resource_id=patient_id,
            metadata={"updated_fields": updated_fields},
        )

    async def record_clinical_history_created(
        self, actor_id: str, patient_id: str, entry_id: str
    ) -> None:
        """Audit: clinical history entry created."""
        await self.record(
            event_type=AuditEventType.CLINICAL_HISTORY_CREATED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="clinical_history:create",
            resource_type="clinical_history",
            resource_id=entry_id,
            metadata={"patient_id": patient_id},
        )

    async def record_clinical_history_updated(
        self, actor_id: str, patient_id: str, entry_id: str
    ) -> None:
        """Audit: clinical history entry updated."""
        await self.record(
            event_type=AuditEventType.CLINICAL_HISTORY_UPDATED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="clinical_history:update",
            resource_type="clinical_history",
            resource_id=entry_id,
            metadata={"patient_id": patient_id},
        )

    async def record_allergy_created(
        self, actor_id: str, patient_id: str, allergy_id: str
    ) -> None:
        """Audit: allergy record created."""
        await self.record(
            event_type=AuditEventType.ALLERGY_CREATED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="allergy:create",
            resource_type="allergy",
            resource_id=allergy_id,
            metadata={"patient_id": patient_id},
        )

    async def record_allergy_updated(
        self, actor_id: str, patient_id: str, allergy_id: str
    ) -> None:
        """Audit: allergy record updated."""
        await self.record(
            event_type=AuditEventType.ALLERGY_UPDATED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="allergy:update",
            resource_type="allergy",
            resource_id=allergy_id,
            metadata={"patient_id": patient_id},
        )

    async def record_vital_recorded(
        self, actor_id: str, patient_id: str, vital_id: str, vital_type: str
    ) -> None:
        """Audit: vital measurement recorded."""
        await self.record(
            event_type=AuditEventType.VITAL_RECORDED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="vital:create",
            resource_type="vital",
            resource_id=vital_id,
            metadata={"patient_id": patient_id, "vital_type": vital_type},
        )

    async def record_encounter_viewed(
        self, actor_id: str, patient_id: str, encounter_id: str
    ) -> None:
        """Audit: encounter record viewed."""
        await self.record(
            event_type=AuditEventType.ENCOUNTER_VIEWED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="encounter:read",
            resource_type="encounter",
            resource_id=encounter_id,
            metadata={"patient_id": patient_id},
        )

    async def record_encounter_created(
        self, actor_id: str, patient_id: str, encounter_id: str
    ) -> None:
        """Audit: encounter record created."""
        await self.record(
            event_type=AuditEventType.ENCOUNTER_CREATED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="encounter:create",
            resource_type="encounter",
            resource_id=encounter_id,
            metadata={"patient_id": patient_id},
        )

    async def record_clinical_summary_viewed(
        self, actor_id: str, patient_id: str
    ) -> None:
        """Audit: clinical summary viewed."""
        await self.record(
            event_type=AuditEventType.CLINICAL_SUMMARY_VIEWED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="clinical_summary:read",
            resource_type="clinical_summary",
            resource_id=patient_id,
        )

    # -----------------------------------------------------------------------
    # Phase 5: Medical document audit helpers
    # -----------------------------------------------------------------------

    async def record_document_uploaded(
        self,
        actor_id: str,
        patient_id: str,
        document_id: str,
        document_type: str,
        filename: str,
        size_bytes: int,
    ) -> None:
        """Audit: medical document uploaded."""
        await self.record(
            event_type=AuditEventType.DOCUMENT_UPLOADED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="document:upload",
            resource_type="document",
            resource_id=document_id,
            metadata={
                "patient_id": patient_id,
                "document_type": document_type,
                "filename": filename,
                "size_bytes": size_bytes,
            },
        )

    async def record_document_viewed(
        self, actor_id: str, patient_id: str, document_id: str
    ) -> None:
        """Audit: document metadata viewed."""
        await self.record(
            event_type=AuditEventType.DOCUMENT_VIEWED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="document:read",
            resource_type="document",
            resource_id=document_id,
            metadata={"patient_id": patient_id},
        )

    async def record_document_download_requested(
        self, actor_id: str, patient_id: str, document_id: str
    ) -> None:
        """Audit: document download requested."""
        await self.record(
            event_type=AuditEventType.DOCUMENT_DOWNLOAD_REQUESTED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="document:download",
            resource_type="document",
            resource_id=document_id,
            metadata={"patient_id": patient_id},
        )

    async def record_document_archived(
        self, actor_id: str, patient_id: str, document_id: str
    ) -> None:
        """Audit: document archived."""
        await self.record(
            event_type=AuditEventType.DOCUMENT_ARCHIVED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="document:archive",
            resource_type="document",
            resource_id=document_id,
            metadata={"patient_id": patient_id},
        )

    async def record_document_processing_started(
        self, actor_id: str, document_id: str, job_id: str, processor: str
    ) -> None:
        """Audit: document processing started."""
        await self.record(
            event_type=AuditEventType.DOCUMENT_PROCESSING_STARTED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="document:process",
            resource_type="document",
            resource_id=document_id,
            metadata={"job_id": job_id, "processor": processor},
        )

    async def record_document_processing_completed(
        self,
        actor_id: str,
        document_id: str,
        job_id: str,
        processor: str,
        extraction_id: str,
    ) -> None:
        """Audit: document processing successfully completed."""
        await self.record(
            event_type=AuditEventType.DOCUMENT_PROCESSING_COMPLETED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="document:process",
            resource_type="document",
            resource_id=document_id,
            metadata={
                "job_id": job_id,
                "processor": processor,
                "extraction_id": extraction_id,
            },
        )

    async def record_document_processing_failed(
        self,
        actor_id: str,
        document_id: str,
        job_id: str,
        error_code: str,
        retry_count: int,
    ) -> None:
        """Audit: document processing failed."""
        await self.record(
            event_type=AuditEventType.DOCUMENT_PROCESSING_FAILED,
            outcome="DENY",
            actor_id=actor_id,
            action="document:process",
            resource_type="document",
            resource_id=document_id,
            reason_code=error_code,
            metadata={"job_id": job_id, "retry_count": retry_count},
        )

    async def record_document_processing_retried(
        self, actor_id: str, document_id: str, job_id: str, attempt: int
    ) -> None:
        """Audit: document processing retry initiated."""
        await self.record(
            event_type=AuditEventType.DOCUMENT_PROCESSING_RETRIED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="document:retry",
            resource_type="document",
            resource_id=document_id,
            metadata={"job_id": job_id, "attempt": attempt},
        )

    async def record_document_extraction_created(
        self, actor_id: str, document_id: str, extraction_id: str, processor: str
    ) -> None:
        """Audit: document extraction result recorded."""
        await self.record(
            event_type=AuditEventType.DOCUMENT_EXTRACTION_CREATED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="document:extraction_create",
            resource_type="document_extraction",
            resource_id=extraction_id,
            metadata={"document_id": document_id, "processor": processor},
        )

    async def record_document_extraction_viewed(
        self, actor_id: str, patient_id: str, document_id: str, extraction_id: str
    ) -> None:
        """Audit: extraction result viewed."""
        await self.record(
            event_type=AuditEventType.DOCUMENT_EXTRACTION_VIEWED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="document_extraction:read",
            resource_type="document_extraction",
            resource_id=extraction_id,
            metadata={"patient_id": patient_id, "document_id": document_id},
        )

    # -----------------------------------------------------------------------
    # Phase 6: Prescription & Medication Audit Helpers
    # -----------------------------------------------------------------------

    async def record_prescription_created(
        self, actor_id: str, patient_id: str, prescription_id: str, source: str
    ) -> None:
        """Audit: prescription record created."""
        await self.record(
            event_type=AuditEventType.PRESCRIPTION_CREATED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="prescription:create",
            resource_type="prescription",
            resource_id=prescription_id,
            metadata={"patient_id": patient_id, "source": source},
        )

    async def record_prescription_viewed(
        self, actor_id: str, patient_id: str, prescription_id: str
    ) -> None:
        """Audit: prescription viewed."""
        await self.record(
            event_type=AuditEventType.PRESCRIPTION_VIEWED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="prescription:read",
            resource_type="prescription",
            resource_id=prescription_id,
            metadata={"patient_id": patient_id},
        )

    async def record_prescription_updated(
        self, actor_id: str, patient_id: str, prescription_id: str
    ) -> None:
        """Audit: prescription updated."""
        await self.record(
            event_type=AuditEventType.PRESCRIPTION_UPDATED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="prescription:update",
            resource_type="prescription",
            resource_id=prescription_id,
            metadata={"patient_id": patient_id},
        )

    async def record_prescription_normalization_started(
        self, actor_id: str, patient_id: str, prescription_id: str
    ) -> None:
        """Audit: prescription normalization started."""
        await self.record(
            event_type=AuditEventType.PRESCRIPTION_NORMALIZATION_STARTED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="prescription:normalize",
            resource_type="prescription",
            resource_id=prescription_id,
            metadata={"patient_id": patient_id},
        )

    async def record_prescription_normalization_completed(
        self, actor_id: str, patient_id: str, prescription_id: str, items_count: int
    ) -> None:
        """Audit: prescription normalization completed."""
        await self.record(
            event_type=AuditEventType.PRESCRIPTION_NORMALIZATION_COMPLETED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="prescription:normalize",
            resource_type="prescription",
            resource_id=prescription_id,
            metadata={"patient_id": patient_id, "items_count": items_count},
        )

    async def record_prescription_normalization_failed(
        self, actor_id: str, patient_id: str, prescription_id: str, reason_code: str
    ) -> None:
        """Audit: prescription normalization failed."""
        await self.record(
            event_type=AuditEventType.PRESCRIPTION_NORMALIZATION_FAILED,
            outcome="DENY",
            actor_id=actor_id,
            action="prescription:normalize",
            resource_type="prescription",
            resource_id=prescription_id,
            reason_code=reason_code,
            metadata={"patient_id": patient_id},
        )

    async def record_medication_created(
        self, actor_id: str, patient_id: str, medication_id: str, source: str
    ) -> None:
        """Audit: patient medication record created."""
        await self.record(
            event_type=AuditEventType.MEDICATION_CREATED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="medication:create",
            resource_type="medication",
            resource_id=medication_id,
            metadata={"patient_id": patient_id, "source": source},
        )

    async def record_medication_viewed(
        self, actor_id: str, patient_id: str, medication_id: str
    ) -> None:
        """Audit: patient medication viewed."""
        await self.record(
            event_type=AuditEventType.MEDICATION_VIEWED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="medication:read",
            resource_type="medication",
            resource_id=medication_id,
            metadata={"patient_id": patient_id},
        )

    async def record_medication_updated(
        self, actor_id: str, patient_id: str, medication_id: str
    ) -> None:
        """Audit: patient medication updated."""
        await self.record(
            event_type=AuditEventType.MEDICATION_UPDATED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="medication:update",
            resource_type="medication",
            resource_id=medication_id,
            metadata={"patient_id": patient_id},
        )

    async def record_medication_status_changed(
        self, actor_id: str, patient_id: str, medication_id: str, old_status: str, new_status: str
    ) -> None:
        """Audit: patient medication status changed."""
        await self.record(
            event_type=AuditEventType.MEDICATION_STATUS_CHANGED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="medication:status",
            resource_type="medication",
            resource_id=medication_id,
            metadata={"patient_id": patient_id, "old_status": old_status, "new_status": new_status},
        )

    async def record_medication_corrected(
        self, actor_id: str, patient_id: str, medication_id: str
    ) -> None:
        """Audit: patient medication corrected."""
        await self.record(
            event_type=AuditEventType.MEDICATION_CORRECTED,
            outcome="ALLOW",
            actor_id=actor_id,
            action="medication:correct",
            resource_type="medication",
            resource_id=medication_id,
            metadata={"patient_id": patient_id},
        )

