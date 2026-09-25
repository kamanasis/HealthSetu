"""Phase 5 tests: Document processing, OCR extraction, idempotency, and clinical boundary."""

import pytest
from httpx import AsyncClient

from app.api.deps import (
    _global_allergy_repo,
    _global_document_repo,
    _global_document_storage,
    _global_history_repo,
    _global_vitals_repo,
)
from app.repositories.patient_repository import PatientRecord
from app.schemas.document import ProcessingStatus

SYNTHETIC_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Length 60 >>\nstream\nBT\n/F1 12 Tf\n(Diagnosis: Type 2 Diabetes)\n(Rx: Metformin 500mg)\nET\nendstream\nendobj\n%%EOF"


async def test_processing_creates_extraction_and_structured_fields(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Uploaded document is processed and structured extraction is generated."""
    token = make_token("usr-patient-001", "PATIENT")
    files = {"file": ("report.pdf", SYNTHETIC_PDF_BYTES, "application/pdf")}
    res = await async_client.post(
        "/api/v1/patients/pat-001/documents",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    doc_id = res.json()["data"]["id"]

    # Directly retrieve extraction result
    ext_res = await async_client.get(
        f"/api/v1/patients/pat-001/documents/{doc_id}/extraction",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ext_res.status_code == 200
    ext = ext_res.json()["data"]
    assert ext["document_id"] == doc_id
    assert "processor" in ext
    assert "processor_version" in ext
    assert ext["page_count"] >= 1
    assert "disclaimer" in ext
    assert "not clinically verified" in ext["disclaimer"].lower() or "not constitute verified" in ext["disclaimer"].lower()


async def test_processing_is_idempotent(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Re-processing an already extracted document is idempotent."""
    token = make_token("usr-patient-001", "PATIENT")
    files = {"file": ("report.pdf", SYNTHETIC_PDF_BYTES, "application/pdf")}
    res = await async_client.post(
        "/api/v1/patients/pat-001/documents",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    doc_id = res.json()["data"]["id"]

    # First extraction count
    initial_extractions = len(_global_document_repo._extractions.get(doc_id, []))
    assert initial_extractions >= 1

    # Call processing service again directly
    from app.api.deps import _global_ocr_provider
    from app.services.document_processing_service import DocumentProcessingService
    from app.services.audit_service import AuditService
    from app.services.processors.generic_processor import GenericDocumentProcessor
    from app.services.processors.registry import DocumentProcessorRegistry

    proc_service = DocumentProcessingService(
        repository=_global_document_repo,
        storage=_global_document_storage,
        registry=DocumentProcessorRegistry(GenericDocumentProcessor(_global_ocr_provider)),
        audit_service=AuditService(_global_document_repo),
    )
    result = await proc_service.process_document_job(doc_id, "usr-patient-001")
    assert result is not None
    # No duplicate extractions created
    assert len(_global_document_repo._extractions.get(doc_id, [])) == initial_extractions


async def test_processing_failure_preserves_source_document(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Document binary is preserved in storage even if processing fails."""
    token = make_token("usr-patient-001", "PATIENT")
    files = {"file": ("report.pdf", SYNTHETIC_PDF_BYTES, "application/pdf")}
    res = await async_client.post(
        "/api/v1/patients/pat-001/documents",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    doc_id = res.json()["data"]["id"]
    doc = await _global_document_repo.get_document_by_id(doc_id)

    # Verify binary exists in storage
    data = await _global_document_storage.get(doc.storage_key)
    assert data is not None

    # Simulate processing failure
    job = await _global_document_repo.get_job_by_document_id(doc_id)
    job.status = ProcessingStatus.FAILED
    await _global_document_repo.create_or_update_job(job)

    # Verify binary STILL exists in storage
    data_after = await _global_document_storage.get(doc.storage_key)
    assert data_after == data


async def test_retry_processing_failed_document(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Failed document can be retried by authorized user."""
    token = make_token("usr-patient-001", "PATIENT")
    files = {"file": ("report.pdf", SYNTHETIC_PDF_BYTES, "application/pdf")}
    res = await async_client.post(
        "/api/v1/patients/pat-001/documents",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    doc_id = res.json()["data"]["id"]

    # Mark document as failed
    job = await _global_document_repo.get_job_by_document_id(doc_id)
    job.status = ProcessingStatus.FAILED
    job.attempts = 1
    await _global_document_repo.create_or_update_job(job)

    # Retry endpoint
    retry_res = await async_client.post(
        f"/api/v1/patients/pat-001/documents/{doc_id}/retry",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert retry_res.status_code == 200
    assert retry_res.json()["data"]["document_id"] == doc_id


async def test_retry_rejected_when_max_attempts_exceeded(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Retry is rejected if attempts exceed MAX_PROCESSING_RETRIES."""
    token = make_token("usr-patient-001", "PATIENT")
    files = {"file": ("report.pdf", SYNTHETIC_PDF_BYTES, "application/pdf")}
    res = await async_client.post(
        "/api/v1/patients/pat-001/documents",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    doc_id = res.json()["data"]["id"]

    # Set attempts to 3 (max)
    job = await _global_document_repo.get_job_by_document_id(doc_id)
    job.status = ProcessingStatus.FAILED
    job.attempts = 3
    await _global_document_repo.create_or_update_job(job)

    retry_res = await async_client.post(
        f"/api/v1/patients/pat-001/documents/{doc_id}/retry",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert retry_res.status_code == 422
    assert "exceeded" in retry_res.json()["error"]["message"].lower()


# ---------------------------------------------------------------------------
# Critical Clinical Boundary Test
# ---------------------------------------------------------------------------

async def test_extraction_does_not_automatically_update_clinical_records(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """CRITICAL DOMAIN TEST: Document extraction does NOT automatically update clinical records.

    Extracted "Diagnosis: Type 2 Diabetes" must NOT create a condition.
    Extracted "Rx: Metformin" must NOT update patient allergies or vitals.
    """
    token = make_token("usr-patient-001", "PATIENT")
    # Record starting counts of clinical entities
    initial_history = len(await _global_history_repo.list_by_patient("pat-001"))
    initial_allergies = len(await _global_allergy_repo.list_by_patient("pat-001"))
    initial_vitals = len(await _global_vitals_repo.list_by_patient("pat-001"))

    # Upload and extract document containing medical conditions
    files = {"file": ("prescription.pdf", SYNTHETIC_PDF_BYTES, "application/pdf")}
    res = await async_client.post(
        "/api/v1/patients/pat-001/documents",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201

    # Verify NO automatic changes were made to clinical tables
    after_history = len(await _global_history_repo.list_by_patient("pat-001"))
    after_allergies = len(await _global_allergy_repo.list_by_patient("pat-001"))
    after_vitals = len(await _global_vitals_repo.list_by_patient("pat-001"))

    assert after_history == initial_history
    assert after_allergies == initial_allergies
    assert after_vitals == initial_vitals
