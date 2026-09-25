"""Phase 6 tests: Prescription domain service, document integration, and item lifecycle."""

from datetime import datetime, timezone
import pytest
from httpx import AsyncClient

from app.api.deps import _global_authz_service, _global_consent_repo, _global_document_repo
from app.repositories.consent_repository import ConsentRecord, ConsentStatus
from app.repositories.document_repository import DocumentRecord, ExtractionRecord
from app.repositories.patient_repository import PatientRecord
from app.schemas.prescription import PrescriptionSource, PrescriptionStatus


@pytest.fixture
def doctor_consent(seeded_patients):
    """Seed active consent and relationship for doctor on patient pat-001 covering prescriptions."""
    now = datetime.now(timezone.utc)
    consent = ConsentRecord(
        id="cst-presc-001",
        patient_id="usr-patient-001",
        grantee_id="usr-doctor-001",
        purpose="care_delivery",
        scope="prescriptions",
        status=ConsentStatus.ACTIVE,
        granted_at=now,
        effective_from=now,
        expires_at=None,
        version=1,
    )
    _global_consent_repo._consents[consent.id] = consent
    _global_authz_service.add_relationship("usr-doctor-001", "usr-patient-001")
    return consent


from app.schemas.document import (
    DocumentLifecycleState,
    DocumentSource,
    DocumentType,
    ProcessingStatus,
)


@pytest.fixture
def seeded_document_with_extraction():
    """Seed a Phase 5 medical document and extraction record."""
    now = datetime.now(timezone.utc)
    doc = DocumentRecord(
        id="doc-presc-001",
        patient_id="pat-001",
        uploader_id="usr-patient-001",
        document_type=DocumentType.PRESCRIPTION,
        source=DocumentSource.PATIENT_UPLOAD,
        filename="rx_clinic.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        checksum_sha256="a" * 64,
        storage_key="pat-001/doc-presc-001.bin",
        lifecycle_state=DocumentLifecycleState.EXTRACTED,
        processing_status=ProcessingStatus.COMPLETED,
        created_at=now,
        updated_at=now,
    )
    _global_document_repo._documents[doc.id] = doc

    ext = ExtractionRecord(
        id="ext-presc-001",
        document_id="doc-presc-001",
        processor="generic",
        processor_version="generic-1.0",
        extracted_text="Amoxicillin 500 mg 1 tab po twice daily for 5 days after food",
        language="en",
        page_count=1,
        structured_fields=[
            {"field_name": "drug_name", "value": "Amoxicillin"},
            {"field_name": "strength", "value": "500 mg"},
            {"field_name": "dosage_form", "value": "tablet"},
            {"field_name": "route", "value": "oral"},
            {"field_name": "frequency", "value": "twice daily"},
            {"field_name": "duration", "value": "5 days"},
            {"field_name": "instructions", "value": "after food"},
        ],
        created_at=now,
    )
    _global_document_repo._extractions[ext.document_id] = [ext]
    return doc, ext


async def test_doctor_can_create_prescription(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    doctor_consent,
    make_token,
):
    """Doctor with active consent creates a prescription with medication items."""
    token = make_token("usr-doctor-001", "DOCTOR")
    payload = {
        "prescriber_reference": "Dr. Ramesh Gupta, MD",
        "source": "DOCTOR_UPLOAD",
        "items": [
            {
                "drug_name_raw": "Amoxicillin",
                "strength_raw": "500 mg",
                "dosage_form_raw": "capsule",
                "route_raw": "oral",
                "frequency_raw": "twice daily",
                "duration_raw": "5 days",
                "instructions_raw": "after food",
            }
        ],
    }
    response = await async_client.post(
        "/api/v1/patients/pat-001/prescriptions",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["patient_id"] == "pat-001"
    assert data["prescriber_reference"] == "Dr. Ramesh Gupta, MD"
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["drug_name_raw"] == "Amoxicillin"
    assert item["strength_raw"] == "500 mg"
    assert item["normalization_status"] == "MATCHED"
    assert item["normalized_concept"]["canonical_name"] == "Amoxicillin"
    assert item["normalized_concept"]["terminology_code"] == "8640"


async def test_create_prescription_sourcing_from_phase5_extraction(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    doctor_consent,
    seeded_document_with_extraction,
    make_token,
):
    """Doctor references Phase 5 document ID and items are automatically extracted and mapped."""
    token = make_token("usr-doctor-001", "DOCTOR")
    payload = {
        "document_id": "doc-presc-001",
        "prescriber_reference": "City Clinic",
        "source": "PATIENT_UPLOAD",
        "items": [],  # empty: should auto-populate from document extraction
    }
    response = await async_client.post(
        "/api/v1/patients/pat-001/prescriptions",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    data = body["data"]
    assert data["document_id"] == "doc-presc-001"
    assert data["extraction_id"] == "ext-presc-001"
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["drug_name_raw"] == "Amoxicillin"
    assert item["strength_raw"] == "500 mg"
    assert item["frequency_raw"] == "twice daily"
    assert item["duration_raw"] == "5 days"


async def test_patient_can_view_own_prescriptions(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    doctor_consent,
    make_token,
):
    """Patient can view their own prescription list and prescription details."""
    doc_token = make_token("usr-doctor-001", "DOCTOR")
    payload = {
        "prescriber_reference": "Dr. Gupta",
        "items": [{"drug_name_raw": "Metformin", "strength_raw": "500 mg"}],
    }
    create_res = await async_client.post(
        "/api/v1/patients/pat-001/prescriptions",
        json=payload,
        headers={"Authorization": f"Bearer {doc_token}"},
    )
    presc_id = create_res.json()["data"]["id"]

    # Patient view list
    pat_token = make_token("usr-patient-001", "PATIENT")
    list_res = await async_client.get(
        "/api/v1/patients/pat-001/prescriptions",
        headers={"Authorization": f"Bearer {pat_token}"},
    )
    assert list_res.status_code == 200
    assert list_res.json()["data"]["total"] == 1

    # Patient view detail
    detail_res = await async_client.get(
        f"/api/v1/patients/pat-001/prescriptions/{presc_id}",
        headers={"Authorization": f"Bearer {pat_token}"},
    )
    assert detail_res.status_code == 200
    assert detail_res.json()["data"]["id"] == presc_id


async def test_get_single_prescription_item(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    doctor_consent,
    make_token,
):
    """Retrieve details for a single prescription item."""
    doc_token = make_token("usr-doctor-001", "DOCTOR")
    payload = {
        "items": [
            {"drug_name_raw": "Atorvastatin", "strength_raw": "20 mg"},
            {"drug_name_raw": "Ibuprofen", "strength_raw": "400 mg"},
        ]
    }
    create_res = await async_client.post(
        "/api/v1/patients/pat-001/prescriptions",
        json=payload,
        headers={"Authorization": f"Bearer {doc_token}"},
    )
    presc = create_res.json()["data"]
    item_id = presc["items"][0]["id"]

    pat_token = make_token("usr-patient-001", "PATIENT")
    item_res = await async_client.get(
        f"/api/v1/patients/pat-001/prescriptions/{presc['id']}/items/{item_id}",
        headers={"Authorization": f"Bearer {pat_token}"},
    )
    assert item_res.status_code == 200
    item_data = item_res.json()["data"]
    assert item_data["id"] == item_id
    assert item_data["drug_name_raw"] == "Atorvastatin"
