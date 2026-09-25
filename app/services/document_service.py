"""Medical document lifecycle service."""

import hashlib
import os
import re
import uuid
from datetime import datetime, timezone

from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.logging import get_logger
from app.integrations.scanning.base import DocumentSecurityScanner
from app.integrations.storage.base import DocumentStorage
from app.repositories.document_repository import DocumentRecord, DocumentRepository
from app.schemas.document import (
    DocumentDownloadResponse,
    DocumentLifecycleState,
    DocumentResponse,
    DocumentSource,
    DocumentType,
    ProcessingStatus,
)
from app.services.base import BaseService

logger = get_logger("app.document")

SUPPORTED_MIME_TYPES: dict[str, list[str]] = {
    "application/pdf": [".pdf"],
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/webp": [".webp"],
}

# File magic byte signatures
FILE_SIGNATURES: list[tuple[bytes, str]] = [
    (b"%PDF", "application/pdf"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"RIFF", "image/webp"),  # WEBP has RIFF header
]


def _map_doc_to_response(rec: DocumentRecord) -> DocumentResponse:
    return DocumentResponse(
        id=rec.id,
        patient_id=rec.patient_id,
        uploader_id=rec.uploader_id,
        document_type=rec.document_type,
        source=rec.source,
        filename=rec.filename,
        mime_type=rec.mime_type,
        size_bytes=rec.size_bytes,
        checksum_sha256=rec.checksum_sha256,
        lifecycle_state=rec.lifecycle_state,
        processing_status=rec.processing_status,
        created_at=rec.created_at,
        updated_at=rec.updated_at,
        is_archived=rec.is_archived,
    )


class DocumentService(BaseService[DocumentRepository]):
    """Service managing medical document upload, validation, storage, and retrieval."""

    def __init__(
        self,
        repository: DocumentRepository,
        storage: DocumentStorage,
        scanner: DocumentSecurityScanner,
        max_size_bytes: int = 20 * 1024 * 1024,
    ) -> None:
        super().__init__(repository=repository)
        self.doc_repo = repository
        self.storage = storage
        self.scanner = scanner
        self.max_size_bytes = max_size_bytes

    def validate_upload(
        self, file_bytes: bytes, filename: str, content_type: str
    ) -> tuple[str, str]:
        """Validate uploaded file for safety, size, content-type, and magic bytes."""
        if not file_bytes:
            raise ValidationException("Uploaded file is empty.")

        if len(file_bytes) > self.max_size_bytes:
            raise ValidationException(
                f"File size ({len(file_bytes)} bytes) exceeds the maximum allowed limit of {self.max_size_bytes} bytes."
            )

        # Sanitize filename (strip directory traversal characters)
        safe_name = os.path.basename(filename)
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", safe_name)
        if not safe_name or safe_name.startswith("."):
            safe_name = f"document_{uuid.uuid4().hex[:8]}"

        # Check content type and extension
        normalized_mime = content_type.lower()
        if normalized_mime not in SUPPORTED_MIME_TYPES:
            raise ValidationException(
                f"Unsupported document MIME type '{content_type}'. Allowed types: {list(SUPPORTED_MIME_TYPES.keys())}"
            )

        # Inspect magic bytes / file signatures to prevent MIME spoofing
        matched = False
        for sig, expected_mime in FILE_SIGNATURES:
            if file_bytes.startswith(sig):
                matched = True
                break
        if not matched and not normalized_mime.startswith("text/"):
            raise ValidationException("File content signature does not match supported medical document formats.")

        return safe_name, normalized_mime

    async def upload_document(
        self,
        patient_id: str,
        uploader_id: str,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        document_type: DocumentType,
        source: DocumentSource,
    ) -> DocumentRecord:
        """Validate, virus scan, persist binary to object storage, and save metadata."""
        safe_filename, validated_mime = self.validate_upload(file_bytes, filename, content_type)

        # Security scan hook
        scan_result = await self.scanner.scan(file_bytes, safe_filename)
        if not scan_result.is_safe:
            logger.warning(
                "Uploaded document failed security scan",
                extra={
                    "event_type": "SECURITY_SCAN_FAILED",
                    "threat": scan_result.threat_name,
                    "patient_id": patient_id,
                },
            )
            raise ValidationException(f"Document security verification failed: {scan_result.message}")

        # Compute SHA-256 checksum
        checksum = hashlib.sha256(file_bytes).hexdigest()

        # Generate unique storage key: documents/{patient_id}/{doc_id}/{safe_filename}
        doc_id = str(uuid.uuid4())
        ext = os.path.splitext(safe_filename)[1] or ".bin"
        storage_key = f"documents/{patient_id}/{doc_id}/{uuid.uuid4().hex[:12]}{ext}"

        # Persist to object storage
        await self.storage.put(key=storage_key, data=file_bytes, content_type=validated_mime)

        now = datetime.now(timezone.utc)
        record = DocumentRecord(
            id=doc_id,
            patient_id=patient_id,
            uploader_id=uploader_id,
            document_type=document_type,
            source=source,
            filename=safe_filename,
            mime_type=validated_mime,
            size_bytes=len(file_bytes),
            checksum_sha256=checksum,
            storage_key=storage_key,
            lifecycle_state=DocumentLifecycleState.UPLOADED,
            processing_status=ProcessingStatus.PENDING,
            created_at=now,
            updated_at=now,
            is_archived=False,
        )
        return await self.doc_repo.create_document(record)

    async def get_document(self, patient_id: str, document_id: str) -> DocumentResponse:
        """Retrieve document metadata."""
        doc = await self.doc_repo.get_document_by_id(document_id)
        if not doc or doc.patient_id != patient_id:
            raise NotFoundException("Document not found.")
        return _map_doc_to_response(doc)

    async def list_documents(
        self, patient_id: str, include_archived: bool = False
    ) -> list[DocumentResponse]:
        """List patient documents."""
        records = await self.doc_repo.list_documents_by_patient(
            patient_id, include_archived=include_archived
        )
        return [_map_doc_to_response(r) for r in records]

    async def generate_download(
        self, patient_id: str, document_id: str, expires_in_seconds: int = 300
    ) -> DocumentDownloadResponse:
        """Generate short-lived controlled access download link for an authorized requester."""
        doc = await self.doc_repo.get_document_by_id(document_id)
        if not doc or doc.patient_id != patient_id or doc.is_archived:
            raise NotFoundException("Document not found.")

        url = await self.storage.generate_download_url(
            key=doc.storage_key,
            filename=doc.filename,
            expires_in_seconds=expires_in_seconds,
        )
        return DocumentDownloadResponse(
            document_id=doc.id,
            download_url=url,
            expires_in_seconds=expires_in_seconds,
            filename=doc.filename,
            mime_type=doc.mime_type,
        )

    async def archive_document(self, patient_id: str, document_id: str) -> DocumentResponse:
        """Archive / soft-delete a document."""
        doc = await self.doc_repo.get_document_by_id(document_id)
        if not doc or doc.patient_id != patient_id:
            raise NotFoundException("Document not found.")

        archived = await self.doc_repo.archive_document(document_id)
        if not archived:
            raise NotFoundException("Document not found.")
        return _map_doc_to_response(archived)
