"""Phase 5 tests: Document security, PHI confidentiality, and access isolation."""

import pytest
from httpx import AsyncClient

from app.api.deps import _global_audit_repo, _global_document_repo
from app.repositories.patient_repository import PatientRecord

SYNTHETIC_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Length 60 >>\nstream\nBT\n/F1 12 Tf\n(Sensitive Clinical Note)\n(Patient: Aarav Sharma)\nET\nendstream\nendobj\n%%EOF"


async def test_patient_cannot_view_other_patient_documents_returns_404(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Patient 1 requesting Patient 2's document list gets 404 (preventing enumeration)."""
    token = make_token("usr-patient-001", "PATIENT")
    response = await async_client.get(
        "/api/v1/patients/pat-002/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


async def test_patient_cannot_download_other_patient_document_returns_404(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Patient 1 requesting download for Patient 2's document gets 404."""
    # Patient 2 uploads a document
    token2 = make_token("usr-patient-002", "PATIENT")
    files = {"file": ("p2_doc.pdf", SYNTHETIC_PDF_BYTES, "application/pdf")}
    upload_res = await async_client.post(
        "/api/v1/patients/pat-002/documents",
        files=files,
        headers={"Authorization": f"Bearer {token2}"},
    )
    doc_id = upload_res.json()["data"]["id"]

    # Patient 1 attempts to download Patient 2's document
    token1 = make_token("usr-patient-001", "PATIENT")
    download_res = await async_client.get(
        f"/api/v1/patients/pat-002/documents/{doc_id}/download",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert download_res.status_code == 404


async def test_patient_cannot_view_other_patient_extraction_returns_404(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Patient 1 attempting to view Patient 2's extraction result gets 404."""
    token2 = make_token("usr-patient-002", "PATIENT")
    files = {"file": ("p2_doc.pdf", SYNTHETIC_PDF_BYTES, "application/pdf")}
    upload_res = await async_client.post(
        "/api/v1/patients/pat-002/documents",
        files=files,
        headers={"Authorization": f"Bearer {token2}"},
    )
    doc_id = upload_res.json()["data"]["id"]

    token1 = make_token("usr-patient-001", "PATIENT")
    ext_res = await async_client.get(
        f"/api/v1/patients/pat-002/documents/{doc_id}/extraction",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert ext_res.status_code == 404


async def test_admin_cannot_access_documents(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Admin role has zero medical document permissions and receives 403."""
    token = make_token("usr-admin-001", "ADMIN")
    response = await async_client.get(
        "/api/v1/patients/pat-001/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_admin_cannot_access_document_extraction(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Admin role cannot read document extractions and receives 403."""
    token = make_token("usr-admin-001", "ADMIN")
    response = await async_client.get(
        "/api/v1/patients/pat-001/documents/doc-123/extraction",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_doctor_cannot_access_documents_without_relationship(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Doctor without established treating relationship receives 403."""
    token = make_token("usr-doctor-001", "DOCTOR")
    response = await async_client.get(
        "/api/v1/patients/pat-001/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_archive_document_and_download_prevention(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Archived document cannot be downloaded and is marked archived."""
    token = make_token("usr-patient-001", "PATIENT")
    files = {"file": ("report.pdf", SYNTHETIC_PDF_BYTES, "application/pdf")}
    upload_res = await async_client.post(
        "/api/v1/patients/pat-001/documents",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    doc_id = upload_res.json()["data"]["id"]

    # Archive document
    archive_res = await async_client.post(
        f"/api/v1/patients/pat-001/documents/{doc_id}/archive",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert archive_res.status_code == 200
    assert archive_res.json()["data"]["is_archived"] is True

    # Attempt to download archived document
    download_res = await async_client.get(
        f"/api/v1/patients/pat-001/documents/{doc_id}/download",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert download_res.status_code == 404


async def test_download_response_does_not_leak_credentials_or_internal_paths(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Download response contains short-lived controlled URL without exposing storage credentials."""
    token = make_token("usr-patient-001", "PATIENT")
    files = {"file": ("report.pdf", SYNTHETIC_PDF_BYTES, "application/pdf")}
    upload_res = await async_client.post(
        "/api/v1/patients/pat-001/documents",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    doc_id = upload_res.json()["data"]["id"]

    download_res = await async_client.get(
        f"/api/v1/patients/pat-001/documents/{doc_id}/download",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert download_res.status_code == 200
    data = download_res.json()["data"]
    assert "download_url" in data
    assert "s3://" not in data["download_url"]
    assert "access_key" not in data["download_url"]
    assert "secret" not in data["download_url"]


async def test_audit_logs_contain_no_phi_or_ocr_text(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Audit logs for document events record IDs and status only, never document or OCR text."""
    token = make_token("usr-patient-001", "PATIENT")
    files = {"file": ("sensitive_note.pdf", SYNTHETIC_PDF_BYTES, "application/pdf")}
    await async_client.post(
        "/api/v1/patients/pat-001/documents",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )

    for event in _global_audit_repo._events:
        metadata = event.metadata or {}
        # Document text strings must never appear in audit events
        assert "Sensitive Clinical Note" not in str(metadata)
        assert "Aarav Sharma" not in str(metadata)
