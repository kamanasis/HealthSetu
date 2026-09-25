"""Tests for Discharge Information Extraction and Clinical Verification Boundary (Phase 9).

Validates:
- Extraction of structured discharge instructions from Phase 5 documents:
  - Discharge diagnoses
  - Discharge medications
  - Activity instructions
  - Dietary orders
  - Wound care instructions
  - Red flag warning signs and emergency actions
  - Follow-up timeline and appointments
- Initial status is UNVERIFIED
- Clinical verification boundary: Clinician verification and correction
- Provenance and audit logging
- API endpoint integration
"""

from datetime import date, datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import (
    _global_audit_repo,
    _global_authz_service,
    _global_consent_repo,
    _global_discharge_extractor,
    _global_discharge_repo,
    _global_document_repo,
    _global_patient_repo,
    _global_user_repo,
)
from app.core.security import create_access_token, hash_password
from app.integrations.discharge.extractor import LocalDischargeExtractor
from app.main import create_app
from app.repositories.consent_repository import ConsentRecord, ConsentStatus
from app.repositories.document_repository import DocumentRecord, ExtractionRecord
from app.repositories.patient_repository import PatientRecord
from app.repositories.user_repository import UserRecord
from app.schemas.audit import AuditEventType
from app.schemas.auth import AccountStatus, UserRole
from app.schemas.discharge import (
    DISCHARGE_CLINICAL_DISCLAIMER,
    DischargeVerificationStatus,
    DischargeVerificationUpdate,
)
from app.schemas.document import (
    DocumentLifecycleState,
    DocumentSource,
    DocumentType,
    ProcessingStatus,
)
from app.schemas.patient import BiologicalSex, PatientStatus
from app.services.audit_service import AuditService
from app.services.discharge_service import DischargeService

SAMPLE_DISCHARGE_SUMMARY_TEXT = """
HOSPITAL DISCHARGE SUMMARY
PATIENT: Sayan Mukherjee | MRN: 987654 | ADMITTED: 2026-09-10 | DISCHARGED: 2026-09-20
ATTENDING PHYSICIAN: Dr. Robert Vance, MD

DISCHARGE DIAGNOSES:
1. Acute ST-elevation Myocardial Infarction (STEMI), status post primary PCI to LAD with drug-eluting stent.
2. Essential Hypertension.
3. Type 2 Diabetes Mellitus without acute complications.

HOSPITAL COURSE:
Patient presented with acute substernal chest pressure. Coronary angiography confirmed 95% occlusion of the proximal LAD. Successful PCI with 3.0x18mm DES deployed with TIMI 3 flow restored. Post-procedure recovery uneventful.

DISCHARGE MEDICATIONS:
- Aspirin 81 mg oral tablet daily in the morning indefinitely.
- Ticagrelor 90 mg oral tablet twice daily for 12 months.
- Atorvastatin 80 mg oral tablet once daily at bedtime.
- Metoprolol Succinate 25 mg oral tablet once daily in the morning.
- Metformin 500 mg oral tablet twice daily with meals.

ACTIVITY RESTRICTIONS:
- No heavy lifting greater than 10 lbs for 2 weeks.
- Light walking encouraged for 15-20 minutes twice daily on flat surfaces.
- No driving for 1 week post-procedure.

DIETARY ORDERS:
- Low sodium (<2,000 mg/day) cardiac diet.
- Diabetic carbohydrate-consistent diet. Fluid intake not restricted.

WOUND CARE:
- Right femoral access site: Keep clean and dry for 48 hours.
- Inspect puncture site daily for hematoma, warmth, or active bleeding. Do not submerge in bathtub.

RED FLAGS & WARNING SIGNS:
- Recurrent chest pain or pressure -> Call 911 immediately or go to nearest emergency department.
- Shortness of breath at rest, fever over 101F, or sudden dizziness -> Contact cardiology clinic urgently.
- Active bleeding from puncture site -> Apply firm continuous pressure and call 911.

FOLLOW-UP APPOINTMENTS:
- Cardiology clinic follow-up in 14 days for post-PCI evaluation and ECG.
- Primary Care Physician follow-up in 30 days for routine diabetes and lipid panel check.
"""


@pytest.fixture
def test_app():
    return create_app()


@pytest.fixture
async def discharge_test_context():
    """Seed patient, doctor, document, and relationships for discharge testing."""
    hashed_pwd = hash_password("DischargeSecurePass123!")
    now = datetime.now(timezone.utc)

    # 1. Patient User & Patient Record
    pat_user = UserRecord(
        id="usr-pat-disc-001",
        identifier="disc_patient@example.com",
        password_hash=hashed_pwd,
        role=UserRole.PATIENT,
        status=AccountStatus.ACTIVE,
        created_at=now,
    )
    pat_record = PatientRecord(
        id="pat-disc-001",
        user_id="usr-pat-disc-001",
        first_name="Sayan",
        last_name="Mukherjee",
        date_of_birth=date(1985, 4, 12),
        sex=BiologicalSex.MALE,
        status=PatientStatus.ACTIVE,
        phone="+919876543201",
        email="disc_patient@example.com",
        created_at=now,
        updated_at=now,
    )

    # 2. Doctor User
    doc_user = UserRecord(
        id="usr-doc-disc-001",
        identifier="disc_doctor@example.com",
        password_hash=hashed_pwd,
        role=UserRole.DOCTOR,
        status=AccountStatus.ACTIVE,
        created_at=now,
    )

    _global_user_repo.register_in_memory_user(pat_user)
    _global_user_repo.register_in_memory_user(doc_user)
    await _global_patient_repo.create(pat_record)

    # 3. Doctor-Patient Relationship & Consent
    _global_authz_service.add_relationship(doc_user.id, pat_user.id)
    _global_authz_service.add_relationship(doc_user.id, pat_record.id)

    consent = ConsentRecord(
        id="cns-disc-001",
        patient_id=pat_user.id,
        grantee_id=doc_user.id,
        purpose="care_delivery",
        scope="discharge_summary",
        status=ConsentStatus.ACTIVE,
        granted_at=now,
        effective_from=now,
        revoked_at=None,
    )
    await _global_consent_repo.create(consent)
    # Also add for pat_record.id
    c_rec = ConsentRecord(
        id="cns-disc-002",
        patient_id=pat_record.id,
        grantee_id=doc_user.id,
        purpose="care_delivery",
        scope="discharge_summary",
        status=ConsentStatus.ACTIVE,
        granted_at=now,
        effective_from=now,
        revoked_at=None,
    )
    await _global_consent_repo.create(c_rec)

    # 4. Phase 5 Document Record & Extraction
    doc_record = DocumentRecord(
        id="doc-disc-summary-001",
        patient_id=pat_record.id,
        uploader_id=doc_user.id,
        document_type=DocumentType.DISCHARGE_SUMMARY,
        source=DocumentSource.DOCTOR_UPLOAD,
        filename="discharge_summary_cardiac.txt",
        mime_type="text/plain",
        size_bytes=len(SAMPLE_DISCHARGE_SUMMARY_TEXT.encode("utf-8")),
        checksum_sha256="c" * 64,
        storage_key=f"{pat_record.id}/doc-disc-summary-001.txt",
        lifecycle_state=DocumentLifecycleState.EXTRACTED,
        processing_status=ProcessingStatus.COMPLETED,
        created_at=now,
        updated_at=now,
    )
    await _global_document_repo.create_document(doc_record)

    ext_record = ExtractionRecord(
        id="ext-disc-001",
        document_id=doc_record.id,
        processor="generic_ocr",
        processor_version="1.0",
        extracted_text=SAMPLE_DISCHARGE_SUMMARY_TEXT,
        language="en",
        page_count=1,
        created_at=now,
    )
    await _global_document_repo.save_extraction(ext_record)

    pat_token, _ = create_access_token(pat_user.id, pat_user.role)
    doc_token, _ = create_access_token(doc_user.id, doc_user.role)

    return {
        "pat_user": pat_user,
        "pat_record": pat_record,
        "doc_user": doc_user,
        "doc_record": doc_record,
        "pat_token": pat_token,
        "doc_token": doc_token,
    }


@pytest.mark.asyncio
async def test_local_discharge_extractor_parsing():
    """Verify LocalDischargeExtractor parses clinical domains correctly."""
    extractor = LocalDischargeExtractor()
    extracted = await extractor.extract(SAMPLE_DISCHARGE_SUMMARY_TEXT)

    assert len(extracted.discharge_diagnoses) >= 2
    assert any("myocardial infarction" in d.lower() or "stemi" in d.lower() for d in extracted.discharge_diagnoses)

    # Medications
    assert len(extracted.medications) >= 3
    drug_names = [m.drug_name.lower() for m in extracted.medications]
    assert any("aspirin" in d for d in drug_names)
    assert any("atorvastatin" in d for d in drug_names)

    # Activity & Diet
    assert len(extracted.activity_instructions) >= 1
    assert any("lifting" in a.description.lower() or "walking" in a.description.lower() for a in extracted.activity_instructions)
    assert len(extracted.diet_instructions) >= 1

    # Red flags / Warning signs
    assert len(extracted.warning_signs) >= 1
    assert any("chest pain" in ws.symptom.lower() for ws in extracted.warning_signs)

    # Follow-up
    assert len(extracted.follow_up_instructions) >= 1
    assert any("cardiology" in fu.provider_or_specialty.lower() or "cardiology" in fu.recommended_timeframe.lower() for fu in extracted.follow_up_instructions)


@pytest.mark.asyncio
async def test_discharge_service_lifecycle_and_verification(discharge_test_context):
    """Verify discharge extraction lifecycle, unverified initial status, and clinician verification."""
    ctx = discharge_test_context
    pat_record = ctx["pat_record"]
    doc_record = ctx["doc_record"]
    doc_user = ctx["doc_user"]

    audit_svc = AuditService(audit_repository=_global_audit_repo)
    svc = DischargeService(
        discharge_repo=_global_discharge_repo,
        document_repo=_global_document_repo,
        audit_service=audit_svc,
        extractor=_global_discharge_extractor,
    )

    # 1. Extract from document
    res = await svc.extract_from_document(
        patient_id=pat_record.id,
        document_id=doc_record.id,
        encounter_id="enc-001",
        actor_id=doc_user.id,
    )

    assert res.discharge_id is not None
    assert res.patient_id == pat_record.id
    assert res.document_id == doc_record.id
    # CRITICAL: Extracted discharge instructions must be UNVERIFIED until clinician signs off
    assert res.verification_status == DischargeVerificationStatus.UNVERIFIED
    assert res.verified_by is None
    assert res.disclaimer == DISCHARGE_CLINICAL_DISCLAIMER
    assert len(res.discharge_diagnoses) >= 2
    assert len(res.medications) >= 3

    # 2. Clinician reviews and verifies
    update_payload = DischargeVerificationUpdate(
        status=DischargeVerificationStatus.VERIFIED,
        clinician_notes="Reviewed post-PCI LAD stenting discharge instructions. Patient instructed on DAPT adherence.",
    )
    verified = await svc.verify_discharge_instructions(
        patient_id=pat_record.id,
        discharge_id=res.discharge_id,
        payload=update_payload,
        clinician_id=doc_user.id,
    )

    assert verified.verification_status == DischargeVerificationStatus.VERIFIED
    assert verified.verified_by == doc_user.id
    assert verified.verified_at is not None
    assert "Reviewed post-PCI" in verified.clinician_notes

    # 3. Retrieve
    retrieved = await svc.get_discharge_instructions(
        patient_id=pat_record.id,
        discharge_id=res.discharge_id,
        actor_id=doc_user.id,
    )
    assert retrieved.discharge_id == res.discharge_id
    assert retrieved.verification_status == DischargeVerificationStatus.VERIFIED

    # 4. Check audit log
    events = [e for e in _global_audit_repo._events if (e.metadata or {}).get("patient_id") == pat_record.id]
    types = [e.event_type for e in events]
    assert AuditEventType.DISCHARGE_EXTRACTION_STARTED in types
    assert AuditEventType.DISCHARGE_EXTRACTION_COMPLETED in types
    assert AuditEventType.DISCHARGE_VERIFIED in types


@pytest.mark.asyncio
async def test_discharge_api_endpoints(test_app, discharge_test_context):
    """Test FastAPI discharge endpoints: extract, get, verify."""
    ctx = discharge_test_context
    pat_record = ctx["pat_record"]
    doc_record = ctx["doc_record"]
    doc_token = ctx["doc_token"]
    pat_token = ctx["pat_token"]

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Extract endpoint (Doctor with consent)
        extract_resp = await client.post(
            f"/api/v1/patients/{pat_record.id}/discharge/extract",
            headers={"Authorization": f"Bearer {doc_token}"},
            json={"document_id": doc_record.id, "encounter_id": "enc-101"},
        )
        assert extract_resp.status_code == 201
        extract_data = extract_resp.json()["data"]
        discharge_id = extract_data["discharge_id"]
        assert extract_data["verification_status"] == "UNVERIFIED"

        # 2. Get endpoint (Patient reading their own instructions)
        get_resp = await client.get(
            f"/api/v1/patients/{pat_record.id}/discharge/{discharge_id}",
            headers={"Authorization": f"Bearer {pat_token}"},
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["data"]["discharge_id"] == discharge_id

        # 3. Verify endpoint (Doctor verifies)
        verify_resp = await client.post(
            f"/api/v1/patients/{pat_record.id}/discharge/{discharge_id}/verify",
            headers={"Authorization": f"Bearer {doc_token}"},
            json={
                "status": "VERIFIED",
                "clinician_notes": "Instructions verified with patient before discharge.",
            },
        )
        assert verify_resp.status_code == 200
        verify_data = verify_resp.json()["data"]
        assert verify_data["verification_status"] == "VERIFIED"
        assert verify_data["clinician_notes"] == "Instructions verified with patient before discharge."
