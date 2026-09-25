"""Phase 5 tests: Document upload, validation, and storage security."""

import pytest
from httpx import AsyncClient

from app.api.deps import _global_document_repo
from app.repositories.patient_repository import PatientRecord

# Synthetic test PDF bytes with selectable text stream
SYNTHETIC_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Length 50 >>\nstream\nBT\n/F1 12 Tf\n(Rx: Amoxicillin 500mg capsules)\nET\nendstream\nendobj\n%%EOF"

# Synthetic PNG bytes with valid PNG magic bytes
SYNTHETIC_PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4Diagnosis: Hypertension"

# EICAR standard test signature for malware scanning hook
EICAR_BYTES = b"%PDF-1.4\nX5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


async def test_authorized_patient_upload_pdf_success(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Patient can upload a valid medical PDF document."""
    token = make_token("usr-patient-001", "PATIENT")
    files = {
        "file": ("prescription.pdf", SYNTHETIC_PDF_BYTES, "application/pdf"),
    }
    data = {
        "document_type": "PRESCRIPTION",
    }
    response = await async_client.post(
        "/api/v1/patients/pat-001/documents",
        files=files,
        data=data,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    doc = body["data"]
    assert doc["patient_id"] == "pat-001"
    assert doc["document_type"] == "PRESCRIPTION"
    assert doc["filename"] == "prescription.pdf"
    assert doc["mime_type"] == "application/pdf"
    assert doc["source"] == "PATIENT_UPLOAD"
    assert doc["size_bytes"] == len(SYNTHETIC_PDF_BYTES)
    assert doc["lifecycle_state"] in ("UPLOADED", "QUEUED", "PROCESSING", "EXTRACTED")


async def test_authorized_patient_upload_image_png_success(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Patient can upload a medical image (PNG)."""
    token = make_token("usr-patient-001", "PATIENT")
    files = {
        "file": ("lab_report.png", SYNTHETIC_PNG_BYTES, "image/png"),
    }
    data = {
        "document_type": "LAB_REPORT",
    }
    response = await async_client.post(
        "/api/v1/patients/pat-001/documents",
        files=files,
        data=data,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    assert response.json()["data"]["mime_type"] == "image/png"


async def test_upload_unauthenticated_returns_401(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
):
    """Unauthenticated upload request is rejected with 401."""
    files = {
        "file": ("report.pdf", SYNTHETIC_PDF_BYTES, "application/pdf"),
    }
    response = await async_client.post(
        "/api/v1/patients/pat-001/documents",
        files=files,
    )
    assert response.status_code == 401


async def test_patient_upload_to_other_patient_returns_404(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Patient attempting to upload to another patient ID gets 404 (preventing enumeration)."""
    token = make_token("usr-patient-001", "PATIENT")
    files = {
        "file": ("report.pdf", SYNTHETIC_PDF_BYTES, "application/pdf"),
    }
    response = await async_client.post(
        "/api/v1/patients/pat-002/documents",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


async def test_upload_empty_file_rejected(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Uploading a zero-byte file is rejected with 422."""
    token = make_token("usr-patient-001", "PATIENT")
    files = {
        "file": ("empty.pdf", b"", "application/pdf"),
    }
    response = await async_client.post(
        "/api/v1/patients/pat-001/documents",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
    assert "empty" in response.json()["error"]["message"].lower()


async def test_upload_unsupported_mime_type_rejected(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Unsupported file types (e.g. executables or scripts) are rejected."""
    token = make_token("usr-patient-001", "PATIENT")
    files = {
        "file": ("script.sh", b"#!/bin/bash\necho hello", "application/x-sh"),
    }
    response = await async_client.post(
        "/api/v1/patients/pat-001/documents",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
    assert "unsupported" in response.json()["error"]["message"].lower()


async def test_upload_mime_spoofing_signature_mismatch_rejected(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """File claiming to be PDF but having plain text/executable signature is rejected."""
    token = make_token("usr-patient-001", "PATIENT")
    files = {
        "file": ("fake.pdf", b"MZ\x90\x00This is an executable binary", "application/pdf"),
    }
    response = await async_client.post(
        "/api/v1/patients/pat-001/documents",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
    assert "signature" in response.json()["error"]["message"].lower()


async def test_upload_malicious_file_rejected_by_scanner(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """File containing malware test signature is rejected by security scanning hook."""
    token = make_token("usr-patient-001", "PATIENT")
    files = {
        "file": ("infected.pdf", EICAR_BYTES, "application/pdf"),
    }
    response = await async_client.post(
        "/api/v1/patients/pat-001/documents",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
    assert "security" in response.json()["error"]["message"].lower()


async def test_unsafe_filename_sanitized(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Path traversal filename (../../passwd) is sanitized cleanly."""
    token = make_token("usr-patient-001", "PATIENT")
    files = {
        "file": ("../../../../etc/passwd.pdf", SYNTHETIC_PDF_BYTES, "application/pdf"),
    }
    response = await async_client.post(
        "/api/v1/patients/pat-001/documents",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    saved_filename = response.json()["data"]["filename"]
    assert ".." not in saved_filename
    assert "/" not in saved_filename
    assert "\\" not in saved_filename
