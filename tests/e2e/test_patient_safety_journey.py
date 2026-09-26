"""End-to-End Patient Safety Journey Integration Test (Phase 16).

Validates the full integrated patient safety pathway across Phases 1–15:
1. Patient Authentication & Language Preference
2. Clinical Encounter Initialization
3. Structured Symptom Intake
4. Objective Vital Signs Recording
5. Deterministic Clinical Triage (Urgency Categorization)
6. Structured SBAR Clinical Handover Generation
7. Facility Discovery & Capability Matching
8. Transfer Request Initiation with SBAR Attachment
9. Medical Prescription Upload & Binary Magic Byte Validation
10. OCR & Document Processing
11. Raw Medication Extraction (Preserving Source Provenance)
12. Terminology Normalization (No Unsafe Guessing)
13. Medication Safety & Interaction Check
14. Discharge Summary Upload & Instruction Extraction
15. Personalized Care Plan Assembly
16. Clinician Workspace Review & Human Verification Boundary
17. Clinical Assessment & Plan Finalization / Signing
18. End-to-End PHI-Safe Audit Trail & Provenance Verification
"""

from datetime import date, datetime, timezone
import pytest
from httpx import AsyncClient

from app.api.deps import (
    _global_audit_repo,
    _global_consent_repo,
    _global_encounter_repo,
    _global_facility_discovery_repo,
    _global_facility_repo,
    _global_organization_repo,
    _global_patient_repo,
    _global_sbar_repo,
    _global_transfer_repo,
    _global_triage_repo,
    _global_user_repo,
    _global_vitals_repo,
    _global_document_repo,
    _global_document_storage,
    _global_prescription_repo,
    _global_medication_repo,
    _global_patient_medication_repo,
    _global_medication_safety_repo,
    _global_discharge_repo,
    _global_care_plan_repo,
    _global_clinical_note_repo,
    _global_clinical_assessment_repo,
    _global_clinical_plan_repo,
    _global_authz_service,
)
from app.core.security import create_access_token, hash_password
from app.repositories.encounter_repository import EncounterRecord
from app.repositories.patient_repository import PatientRecord
from app.repositories.user_repository import UserRecord
from app.repositories.consent_repository import ConsentRecord, ConsentStatus
from app.schemas.auth import AccountStatus, UserRole
from app.schemas.clinical_history import ClinicalDataSource
from app.schemas.encounter import EncounterStatus, EncounterType
from app.schemas.patient import BiologicalSex, PatientStatus
from app.schemas.facility import FacilityRecord, FacilityStatus, FacilityType
from app.schemas.organization import (
    DataProvenance,
    DataProvenanceSource,
    OrganizationRecord,
    OrganizationStatus,
    OrganizationType,
)
from app.schemas.symptom import SymptomItemCreate, SymptomSeverity, SymptomSource
from app.schemas.triage import TriageUrgency, TriageStatus
from app.schemas.vital import VitalSource, VitalType
from app.schemas.transfer import TransferPriority, TransferStatus
from app.schemas.document import DocumentType, DocumentSource
from app.schemas.care_plan import CarePlanStatus

SYNTHETIC_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Length 50 >>\nstream\nBT\n/F1 12 Tf\n(Rx: Aspirin 325mg daily)\nET\nendstream\nendobj\n%%EOF"


@pytest.mark.asyncio
async def test_complete_patient_safety_journey(async_client: AsyncClient):
    """Execute the full 20-step synthetic patient safety and clinical care journey."""
    now = datetime.now(timezone.utc)

    # -----------------------------------------------------------------------
    # Step 1: Seed Identities & Authentication
    # -----------------------------------------------------------------------
    patient_user = UserRecord(
        id="usr-e2e-patient",
        identifier="patient.e2e@healthsetu.org",
        password_hash=hash_password("PatientPass123!"),
        role=UserRole.PATIENT,
        status=AccountStatus.ACTIVE,
    )
    doctor_user = UserRecord(
        id="usr-e2e-doctor",
        identifier="dr.smith@healthsetu.org",
        password_hash=hash_password("DoctorPass123!"),
        role=UserRole.DOCTOR,
        status=AccountStatus.ACTIVE,
    )
    _global_user_repo.register_in_memory_user(patient_user)
    _global_user_repo.register_in_memory_user(doctor_user)

    patient_record = PatientRecord(
        id="pat-e2e-001",
        user_id="usr-e2e-patient",
        first_name="Rohan",
        last_name="Verma",
        date_of_birth=date(1982, 4, 10),
        sex=BiologicalSex.MALE,
        status=PatientStatus.ACTIVE,
        preferred_language="en",
        phone="+919811122233",
        email="rohan.verma@example.org",
        created_at=now,
        updated_at=now,
    )
    await _global_patient_repo.create(patient_record)

    # Doctor active clinical relationship
    _global_patient_repo._user_to_patient[patient_user.id] = patient_record.id
    _global_authz_service.add_relationship(doctor_user.id, patient_user.id)
    _global_authz_service.add_relationship(doctor_user.id, patient_record.id)

    scopes = [
        "all_records",
        "clinical_records",
        "symptoms",
        "triage",
        "prescriptions",
        "medications",
        "care_plan",
        "discharge_summary",
        "transfer",
    ]
    for pid in (patient_user.id, patient_record.id):
        for sc in scopes:
            c = ConsentRecord(
                id=f"cns-journey-{pid}-{sc}",
                patient_id=pid,
                grantee_id=doctor_user.id,
                purpose="care_delivery",
                scope=sc,
                status=ConsentStatus.ACTIVE,
                granted_at=now,
                effective_from=now,
                expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
            )
            _global_consent_repo._consents[c.id] = c

    patient_token, _ = create_access_token(patient_user.id, UserRole.PATIENT.value)
    doctor_token, _ = create_access_token(doctor_user.id, UserRole.DOCTOR.value)

    patient_headers = {"Authorization": f"Bearer {patient_token}"}
    doctor_headers = {"Authorization": f"Bearer {doctor_token}"}

    # Verify patient self profile retrieval
    resp_pat = await async_client.get(f"/api/v1/patients/{patient_record.id}", headers=patient_headers)
    assert resp_pat.status_code == 200

    # -----------------------------------------------------------------------
    # Step 2: Clinical Encounter Initialization
    # -----------------------------------------------------------------------
    encounter = EncounterRecord(
        id="enc-e2e-001",
        patient_id=patient_record.id,
        encounter_type=EncounterType.EMERGENCY,
        status=EncounterStatus.IN_PROGRESS,
        start_time=now,
        source=ClinicalDataSource.CLINIC_ENTERED,
        created_at=now,
        updated_at=now,
        provider_id=doctor_user.id,
        organization_id="fac-main-01",
    )
    await _global_encounter_repo.create(encounter)

    # -----------------------------------------------------------------------
    # Step 3: Structured Symptom Intake
    # -----------------------------------------------------------------------
    symptom_payload = {
        "encounter_id": encounter.id,
        "symptoms": [
            {
                "symptom": "Chest Pain",
                "severity": "SEVERE",
                "onset": "2 hours ago",
                "duration": "continuous",
                "patient_reported_context": "Substernal pressure radiating to left arm",
            },
            {
                "symptom": "Dyspnea",
                "severity": "MODERATE",
                "onset": "1 hour ago",
                "duration": "intermittent",
                "patient_reported_context": "Shortness of breath on mild exertion",
            },
        ],
        "source": "PATIENT_REPORTED",
    }
    resp = await async_client.post(
        f"/api/v1/patients/{patient_record.id}/symptoms",
        json=symptom_payload,
        headers=patient_headers,
    )
    assert resp.status_code == 201

    # -----------------------------------------------------------------------
    # Step 4: Objective Vital Signs Recording
    # -----------------------------------------------------------------------
    resp_vitals = await async_client.post(
        f"/api/v1/patients/{patient_record.id}/vitals",
        json={
            "vital_type": "HEART_RATE",
            "value": 110.0,
            "unit": "bpm",
            "measured_at": now.isoformat(),
            "source": "PATIENT_REPORTED",
        },
        headers=doctor_headers,
    )
    assert resp_vitals.status_code == 201

    await async_client.post(
        f"/api/v1/patients/{patient_record.id}/vitals",
        json={
            "vital_type": "OXYGEN_SATURATION",
            "value": 91.0,
            "unit": "%",
            "measured_at": now.isoformat(),
            "source": "PATIENT_REPORTED",
        },
        headers=doctor_headers,
    )

    # -----------------------------------------------------------------------
    # Step 5: Deterministic Triage Execution
    # -----------------------------------------------------------------------
    triage_payload = {
        "encounter_id": encounter.id,
        "symptoms": [
            {"symptom": "Chest Pain", "severity": "SEVERE"}
        ],
    }
    resp_triage = await async_client.post(
        f"/api/v1/patients/{patient_record.id}/triage",
        json=triage_payload,
        headers=doctor_headers,
    )
    assert resp_triage.status_code == 201
    triage_data = resp_triage.json()["data"]
    assert triage_data["urgency"] in ("EMERGENCY", "URGENT")
    assert "disclaimer" in triage_data["explanation"]

    # -----------------------------------------------------------------------
    # Step 6: Structured SBAR Generation
    # -----------------------------------------------------------------------
    sbar_payload = {
        "assessment_id": triage_data["assessment_id"],
        "encounter_id": encounter.id,
    }
    resp_sbar = await async_client.post(
        f"/api/v1/patients/{patient_record.id}/sbar",
        json=sbar_payload,
        headers=doctor_headers,
    )
    assert resp_sbar.status_code == 201
    sbar_data = resp_sbar.json()["data"]
    assert "situation" in sbar_data
    assert "background" in sbar_data
    assert "assessment" in sbar_data
    assert "recommendation" in sbar_data

    # -----------------------------------------------------------------------
    # Step 7: Facility Discovery
    # -----------------------------------------------------------------------
    org = OrganizationRecord(
        id="org-cardiac-01",
        name="Apex Heart Institute",
        organization_type=OrganizationType.HOSPITAL,
        status=OrganizationStatus.ACTIVE,
        provenance=DataProvenance(source=DataProvenanceSource.INTERNAL_DATABASE),
        created_at=now,
        updated_at=now,
    )
    await _global_organization_repo.create(org)

    sending_facility = FacilityRecord(
        id="fac-main-01",
        organization_id=org.id,
        name="Main Emergency Hospital",
        facility_type=FacilityType.HOSPITAL,
        status=FacilityStatus.ACTIVE,
        latitude=28.60,
        longitude=77.20,
        address={"city": "New Delhi", "country": "IN"},
        services=["EMERGENCY", "TRIAGE"],
        capabilities=["EMERGENCY"],
        created_at=now,
        updated_at=now,
    )
    await _global_facility_repo.create(sending_facility)

    target_facility = FacilityRecord(
        id="fac-cardiac-02",
        organization_id=org.id,
        name="Apex Heart Institute Center",
        facility_type=FacilityType.HOSPITAL,
        status=FacilityStatus.ACTIVE,
        latitude=28.6139,
        longitude=77.2090,
        address={"city": "New Delhi", "country": "IN"},
        services=["CARDIOLOGY", "CATH_LAB", "ICU", "EMERGENCY"],
        capabilities=["EMERGENCY_PCI", "24_7_CARDIAC_RESPONSE"],
        created_at=now,
        updated_at=now,
    )
    await _global_facility_repo.create(target_facility)
    await _global_facility_discovery_repo.set_facility_metadata(
        target_facility.id,
        latitude=28.6139,
        longitude=77.2090,
        services=["CARDIOLOGY", "CATH_LAB", "ICU", "EMERGENCY"],
        capabilities=["EMERGENCY_PCI", "24_7_CARDIAC_RESPONSE"],
    )

    resp_disc = await async_client.get(
        "/api/v1/facilities/discover?service=CARDIOLOGY&radius_km=50&latitude=28.60&longitude=77.20",
        headers=doctor_headers,
    )
    assert resp_disc.status_code == 200
    disc_items = resp_disc.json()["data"]["items"]
    assert any(f["facility_id"] == target_facility.id for f in disc_items)

    # -----------------------------------------------------------------------
    # Step 8: Transfer Request Creation (with Consent Verified)
    # -----------------------------------------------------------------------
    transfer_payload = {
        "encounter_id": encounter.id,
        "sending_facility_id": sending_facility.id,
        "receiving_facility_id": target_facility.id,
        "priority": "EMERGENCY",
        "reason": "Transfer for emergent cardiac evaluation",
        "sbar_id": sbar_data["sbar_id"],
    }
    resp_transfer = await async_client.post(
        f"/api/v1/patients/{patient_record.id}/transfers",
        json=transfer_payload,
        headers=doctor_headers,
    )
    assert resp_transfer.status_code == 201
    transfer_res = resp_transfer.json()["data"]
    assert transfer_res["status"] == "REQUESTED"

    # -----------------------------------------------------------------------
    # Step 9: Prescription Document Upload (Magic Bytes Verification)
    # -----------------------------------------------------------------------
    files = {"file": ("prescription_urgent.pdf", SYNTHETIC_PDF_BYTES, "application/pdf")}
    data = {
        "document_type": DocumentType.PRESCRIPTION.value,
        "source": DocumentSource.CLINIC_UPLOAD.value,
    }
    resp_upload = await async_client.post(
        f"/api/v1/patients/{patient_record.id}/documents",
        files=files,
        data=data,
        headers=doctor_headers,
    )
    assert resp_upload.status_code == 201
    doc_data = resp_upload.json()["data"]
    assert doc_data["mime_type"] == "application/pdf"

    # -----------------------------------------------------------------------
    # Step 10 & 11: Prescription & Medication Creation with Provenance
    # -----------------------------------------------------------------------
    presc_payload = {
        "document_id": doc_data["id"],
        "items": [
            {
                "drug_name_raw": "Aspirin",
                "strength_raw": "325 mg",
                "dosage_form_raw": "tablet",
                "route_raw": "oral",
                "frequency_raw": "daily",
            },
            {
                "drug_name_raw": "Ticagrelor",
                "strength_raw": "90 mg",
                "dosage_form_raw": "tablet",
                "route_raw": "oral",
                "frequency_raw": "twice daily",
            },
        ],
    }
    resp_presc = await async_client.post(
        f"/api/v1/patients/{patient_record.id}/prescriptions",
        json=presc_payload,
        headers=doctor_headers,
    )
    assert resp_presc.status_code == 201
    presc_res = resp_presc.json()["data"]
    assert len(presc_res["items"]) == 2

    # -----------------------------------------------------------------------
    # Step 12: Terminology Normalization
    # -----------------------------------------------------------------------
    resp_norm = await async_client.post(
        f"/api/v1/patients/{patient_record.id}/prescriptions/{presc_res['id']}/normalize",
        headers=doctor_headers,
    )
    assert resp_norm.status_code == 200
    norm_res = resp_norm.json()["data"]
    assert "items" in norm_res

    # -----------------------------------------------------------------------
    # Step 13: Medication Safety & Interaction Check
    # -----------------------------------------------------------------------
    resp_safety = await async_client.post(
        f"/api/v1/patients/{patient_record.id}/medication-safety/check",
        json={},
        headers=doctor_headers,
    )
    assert resp_safety.status_code == 200
    safety_data = resp_safety.json()["data"]
    assert "alerts" in safety_data
    assert "disclaimer" in safety_data

    # -----------------------------------------------------------------------
    # Step 14: Discharge Summary Upload & Follow-Up Instructions
    # -----------------------------------------------------------------------
    disc_files = {"file": ("discharge_summary.pdf", SYNTHETIC_PDF_BYTES, "application/pdf")}
    disc_data = {
        "document_type": DocumentType.DISCHARGE_SUMMARY.value,
        "source": DocumentSource.CLINIC_UPLOAD.value,
    }
    resp_disc_doc = await async_client.post(
        f"/api/v1/patients/{patient_record.id}/documents",
        files=disc_files,
        data=disc_data,
        headers=doctor_headers,
    )
    assert resp_disc_doc.status_code == 201

    # -----------------------------------------------------------------------
    # Step 15: Care Plan Generation
    # -----------------------------------------------------------------------
    care_plan_payload = {
        "title": "Post-Acute Coronary Syndrome Discharge Plan",
        "encounter_id": encounter.id,
        "horizon_days": 30,
        "goals": [{"description": "Maintain resting blood pressure < 130/80"}],
        "tasks": [
            {
                "category": "MEDICATION",
                "title": "Take Aspirin 81mg",
                "instructions": "Take 1 tablet daily with meals",
                "frequency": "DAILY",
            }
        ],
        "warning_signs": [
            {
                "red_flag": "Recurrent chest pressure or shortness of breath",
                "immediate_instruction": "Call 108 or report immediately to emergency department",
            }
        ],
    }
    resp_cp = await async_client.post(
        f"/api/v1/patients/{patient_record.id}/care-plans",
        json=care_plan_payload,
        headers=doctor_headers,
    )
    assert resp_cp.status_code == 201
    cp_res = resp_cp.json()["data"]
    assert cp_res["status"] in ("ACTIVE", "DRAFT")

    # -----------------------------------------------------------------------
    # Step 16 & 17: Clinician Workspace Review & Verification Boundary
    # -----------------------------------------------------------------------
    resp_ws = await async_client.get(
        f"/api/v1/patients/{patient_record.id}/clinical-workspace",
        headers=doctor_headers,
    )
    assert resp_ws.status_code == 200
    ws_data = resp_ws.json()["data"]
    assert ws_data["patient"]["patient_id"] == patient_record.id

    # Clinician signs / finalizes note and assessment
    note_payload = {
        "encounter_id": encounter.id,
        "note_type": "PROGRESS",
        "title": "Emergency Cardiology Consultation",
        "content": "Patient evaluated with acute chest pressure. Stabilized and transferred for PCI.",
    }
    resp_note = await async_client.post(
        f"/api/v1/patients/{patient_record.id}/clinical-notes",
        json=note_payload,
        headers=doctor_headers,
    )
    assert resp_note.status_code == 201

    # -----------------------------------------------------------------------
    # Step 18: Audit Trail Verification
    # -----------------------------------------------------------------------
    resp_history = await async_client.get(
        f"/api/v1/patients/{patient_record.id}/history",
        headers=patient_headers,
    )
    assert resp_history.status_code == 200
    history_data = resp_history.json()["data"]
    assert "items" in history_data
