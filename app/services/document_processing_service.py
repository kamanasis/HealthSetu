"""Document processing and OCR orchestration service."""

import uuid
from datetime import datetime, timezone

from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.logging import get_logger
from app.integrations.storage.base import DocumentStorage
from app.repositories.document_repository import (
    DocumentProcessingRecord,
    DocumentRecord,
    DocumentRepository,
    ExtractionRecord,
)
from app.schemas.document import (
    DocumentLifecycleState,
    DocumentRetryResponse,
    ExtractionResultResponse,
    ProcessingStatus,
    StructuredExtractionField,
)
from app.services.audit_service import AuditService
from app.services.base import BaseService
from app.services.processors.registry import DocumentProcessorRegistry

logger = get_logger("app.document_processor")


class DocumentProcessingService(BaseService[DocumentRepository]):
    """Service orchestrating background document extraction and state transitions."""

    def __init__(
        self,
        repository: DocumentRepository,
        storage: DocumentStorage,
        registry: DocumentProcessorRegistry,
        audit_service: AuditService,
        max_retries: int = 3,
    ) -> None:
        super().__init__(repository=repository)
        self.doc_repo = repository
        self.storage = storage
        self.registry = registry
        self.audit_service = audit_service
        self.max_retries = max_retries

    async def enqueue_document(
        self, document: DocumentRecord, actor_id: str
    ) -> DocumentProcessingRecord:
        """Enqueue document for processing."""
        job_id = str(uuid.uuid4())
        processor = self.registry.get_processor(document.document_type)
        now = datetime.now(timezone.utc)

        job = DocumentProcessingRecord(
            id=job_id,
            document_id=document.id,
            status=ProcessingStatus.QUEUED,
            attempts=0,
            processor=processor.processor_name,
            processor_version=processor.processor_version,
            started_at=now,
            created_at=now,
        )
        await self.doc_repo.create_or_update_job(job)
        await self.doc_repo.update_document_status(
            document_id=document.id,
            lifecycle_state=DocumentLifecycleState.QUEUED,
            processing_status=ProcessingStatus.QUEUED,
        )
        return job

    async def process_document_job(
        self, document_id: str, actor_id: str
    ) -> ExtractionResultResponse | None:
        """Process document job idempotently.

        Safe against duplicate execution: if already COMPLETED, returns existing extraction.
        """
        doc = await self.doc_repo.get_document_by_id(document_id)
        if not doc or doc.is_archived:
            logger.warning("Attempted to process non-existent or archived document", extra={"document_id": document_id})
            return None

        job = await self.doc_repo.get_job_by_document_id(document_id)
        if not job:
            job = await self.enqueue_document(doc, actor_id)

        # Idempotency check: if already completed, do not duplicate extraction
        if job.status == ProcessingStatus.COMPLETED and doc.lifecycle_state == DocumentLifecycleState.EXTRACTED:
            logger.info("Document already extracted. Idempotent skip.", extra={"document_id": document_id})
            latest = await self.doc_repo.get_latest_extraction(document_id)
            if latest:
                return self._map_extraction_record(latest)

        # Update state to PROCESSING
        job.attempts += 1
        job.status = ProcessingStatus.PROCESSING
        await self.doc_repo.create_or_update_job(job)
        await self.doc_repo.update_document_status(
            document_id=document_id,
            lifecycle_state=DocumentLifecycleState.PROCESSING,
            processing_status=ProcessingStatus.PROCESSING,
        )

        processor = self.registry.get_processor(doc.document_type)
        await self.audit_service.record_document_processing_started(
            actor_id=actor_id,
            document_id=document_id,
            job_id=job.id,
            processor=processor.processor_name,
        )

        try:
            # Fetch bytes from storage
            data = await self.storage.get(doc.storage_key)
            if data is None:
                raise ValueError(f"Document binary content missing from storage key '{doc.storage_key}'")

            # Execute processor
            result = await processor.process(
                document_id=doc.id,
                document_bytes=data,
                mime_type=doc.mime_type,
                filename=doc.filename,
            )

            # Persist extraction result version
            ext_record = ExtractionRecord(
                id=result.extraction_id,
                document_id=doc.id,
                processor=result.processor,
                processor_version=result.processor_version,
                extracted_text=result.extracted_text,
                language=result.language,
                page_count=result.page_count,
                structured_fields=[f.model_dump() for f in result.structured_fields],
                created_at=result.created_at,
            )
            await self.doc_repo.save_extraction(ext_record)

            # Update job and document states
            job.status = ProcessingStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            await self.doc_repo.create_or_update_job(job)

            await self.doc_repo.update_document_status(
                document_id=doc.id,
                lifecycle_state=DocumentLifecycleState.EXTRACTED,
                processing_status=ProcessingStatus.COMPLETED,
            )

            # Auditing
            await self.audit_service.record_document_processing_completed(
                actor_id=actor_id,
                document_id=doc.id,
                job_id=job.id,
                processor=processor.processor_name,
                extraction_id=result.extraction_id,
            )
            await self.audit_service.record_document_extraction_created(
                actor_id=actor_id,
                document_id=doc.id,
                extraction_id=result.extraction_id,
                processor=processor.processor_name,
            )
            return result

        except Exception as exc:
            logger.error(
                "Document processing failure",
                extra={
                    "event_type": "DOCUMENT_PROCESSING_FAILED",
                    "document_id": document_id,
                    "job_id": job.id,
                    "attempt": job.attempts,
                    "error": str(exc),
                },
            )
            job.status = ProcessingStatus.FAILED
            job.error_message = "Internal extraction error"
            await self.doc_repo.create_or_update_job(job)

            await self.doc_repo.update_document_status(
                document_id=doc.id,
                lifecycle_state=DocumentLifecycleState.FAILED,
                processing_status=ProcessingStatus.FAILED,
            )

            await self.audit_service.record_document_processing_failed(
                actor_id=actor_id,
                document_id=doc.id,
                job_id=job.id,
                error_code="PROCESSING_ERROR",
                retry_count=job.attempts,
            )
            return None

    async def retry_document_processing(
        self, patient_id: str, document_id: str, actor_id: str
    ) -> DocumentRetryResponse:
        """Retry a previously failed document processing job."""
        doc = await self.doc_repo.get_document_by_id(document_id)
        if not doc or doc.patient_id != patient_id or doc.is_archived:
            raise NotFoundException("Document not found.")

        job = await self.doc_repo.get_job_by_document_id(document_id)
        if not job or job.status != ProcessingStatus.FAILED:
            raise ValidationException("Document is not in a failed state eligible for retry.")

        if job.attempts >= self.max_retries:
            raise ValidationException(
                f"Maximum retry attempts ({self.max_retries}) exceeded for this document."
            )

        job.status = ProcessingStatus.QUEUED
        await self.doc_repo.create_or_update_job(job)
        await self.doc_repo.update_document_status(
            document_id=doc.id,
            lifecycle_state=DocumentLifecycleState.QUEUED,
            processing_status=ProcessingStatus.QUEUED,
        )

        await self.audit_service.record_document_processing_retried(
            actor_id=actor_id,
            document_id=doc.id,
            job_id=job.id,
            attempt=job.attempts + 1,
        )

        # Trigger processing job execution
        await self.process_document_job(document_id=doc.id, actor_id=actor_id)

        return DocumentRetryResponse(
            document_id=doc.id,
            job_id=job.id,
            processing_status=ProcessingStatus.QUEUED,
            retry_count=job.attempts,
            message="Document processing re-queued successfully",
        )

    async def get_extraction_result(
        self, patient_id: str, document_id: str
    ) -> ExtractionResultResponse:
        """Retrieve extraction result for document."""
        doc = await self.doc_repo.get_document_by_id(document_id)
        if not doc or doc.patient_id != patient_id or doc.is_archived:
            raise NotFoundException("Document not found.")

        extraction = await self.doc_repo.get_latest_extraction(document_id)
        if not extraction:
            raise NotFoundException("No extraction result available for this document.")

        return self._map_extraction_record(extraction)

    def _map_extraction_record(self, record: ExtractionRecord) -> ExtractionResultResponse:
        fields = [StructuredExtractionField(**f) for f in record.structured_fields]
        return ExtractionResultResponse(
            extraction_id=record.id,
            document_id=record.document_id,
            processor=record.processor,
            processor_version=record.processor_version,
            extracted_text=record.extracted_text,
            language=record.language,
            page_count=record.page_count,
            structured_fields=fields,
            created_at=record.created_at,
        )
