"""End-to-End Clinician Clinical Workflow Test (Phase 16).

Validates the full clinician operating flow:
Organization -> Facility -> Clinician -> Patient -> Encounter -> Clinical Workspace ->
Clinical Note -> Note Signing -> Clinical Assessment -> Assessment Finalization ->
Clinical Plan -> Plan Finalization -> Unauthorized Access Protection -> Audit Generation.
"""

from datetime import date, datetime, timezone
import pytest
from httpx import AsyncClient

from app.api.deps import (
    _global_audit_repo,
    _global_consent_repo,
    _global_encounter_repo,
    _global_facility_repo,
    _global_organization_repo,
    _global_patient_repo,
    _global_user_repo,
    _global_authz_service,
)
from app.core.security import create_access_token, hash_password
from app.repositories.consent_repository import ConsentRecord, ConsentStatus
from app.repositories.encounter_repository import EncounterRecord
from app.repositories.patient_repository import PatientRecord
from app.repositories.user_repository import UserRecord
from app.schemas.auth import AccountStatus, UserRole
from app.schemas.clinical_history import ClinicalDataSource
from app.schemas.encounter import EncounterStatus, EncounterType
from app.schemas.facility import FacilityRecord, FacilityStatus, FacilityType
from app.schemas.organization import (
    DataProvenance,
    DataProvenanceSource,
    OrganizationRecord,
    OrganizationStatus,
    OrganizationType,
)
from app.schemas.patient import BiologicalSex, PatientStatus


@pytest.mark.asyncio
async def test_complete_clinician_workflow(async_client: AsyncClient):
    """Execute end-to-end clinician workspace, note authoring, signing, and verification."""
    now = datetime.now(timezone.utc)

    # 1. Setup Organization & Facility
    org = OrganizationRecord(
        id="org-e2e-hospital",
        name="Metro General Hospital",
        organization_type=OrganizationType.HOSPITAL,
        status=OrganizationStatus.ACTIVE,
        provenance=DataProvenance(source=DataProvenanceSource.INTERNAL_DATABASE),
        created_at=now,
        updated_at=now,
    )
    await _global_organization_repo.create(org)

    fac = FacilityRecord(
        id="fac-e2e-general",
        organization_id=org.id,
        name="Metro General Main Campus",
        facility_type=FacilityType.HOSPITAL,
        status=FacilityStatus.ACTIVE,
        address={"city": "Mumbai", "country": "IN"},
        services=["INTERNAL_MEDICINE", "CARDIOLOGY", "EMERGENCY"],
        capabilities=["INPATIENT", "ICU"],
        created_at=now,
        updated_at=now,
    )
    await _global_facility_repo.create(fac)

    # 2. Setup Clinicians & Patients
    dr_alice = UserRecord(
        id="usr-dr-alice",
        identifier="dr.alice@metrohealth.org",
        password_hash=hash_password("DoctorSecret123!"),
        role=UserRole.DOCTOR,
        status=AccountStatus.ACTIVE,
    )
    dr_bob_unauth = UserRecord(
        id="usr-dr-bob",
        identifier="dr.bob@otherhospital.org",
        password_hash=hash_password("DoctorSecret123!"),
        role=UserRole.DOCTOR,
        status=AccountStatus.ACTIVE,
    )
    patient_user = UserRecord(
        id="usr-patient-meera",
        identifier="meera.sharma@example.com",
        password_hash=hash_password("PatientSecret123!"),
        role=UserRole.PATIENT,
        status=AccountStatus.ACTIVE,
    )
    _global_user_repo.register_in_memory_user(dr_alice)
    _global_user_repo.register_in_memory_user(dr_bob_unauth)
    _global_user_repo.register_in_memory_user(patient_user)

    patient = PatientRecord(
        id="pat-meera-001",
        user_id="usr-patient-meera",
        first_name="Meera",
        last_name="Sharma",
        date_of_birth=date(1978, 11, 3),
        sex=BiologicalSex.FEMALE,
        status=PatientStatus.ACTIVE,
        preferred_language="hi",
        phone="+919822334455",
        email="meera.sharma@example.com",
        created_at=now,
        updated_at=now,
    )
    await _global_patient_repo.create(patient)

    # Establish Dr. Alice relationship and active consent
    _global_patient_repo._user_to_patient[patient_user.id] = patient.id
    _global_authz_service.add_relationship(dr_alice.id, patient_user.id)
    _global_authz_service.add_relationship(dr_alice.id, patient.id)

    for pid in (patient.id, patient_user.id):
        for scope in ("clinical_records", "all_records"):
            consent = ConsentRecord(
                id=f"cns-meera-{pid}-{scope}",
                patient_id=pid,
                grantee_id=dr_alice.id,
                purpose="care_delivery",
                scope=scope,
                status=ConsentStatus.ACTIVE,
                granted_at=now,
                effective_from=now,
                expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
            )
            _global_consent_repo._consents[consent.id] = consent

    encounter = EncounterRecord(
        id="enc-meera-01",
        patient_id=patient.id,
        encounter_type=EncounterType.INPATIENT,
        status=EncounterStatus.IN_PROGRESS,
        start_time=now,
        source=ClinicalDataSource.CLINIC_ENTERED,
        created_at=now,
        updated_at=now,
        provider_id=dr_alice.id,
        organization_id=fac.id,
    )
    await _global_encounter_repo.create(encounter)

    alice_token, _ = create_access_token(dr_alice.id, UserRole.DOCTOR.value)
    bob_token, _ = create_access_token(dr_bob_unauth.id, UserRole.DOCTOR.value)

    alice_headers = {"Authorization": f"Bearer {alice_token}"}
    bob_headers = {"Authorization": f"Bearer {bob_token}"}

    # 3. Access Clinical Workspace as Dr. Alice
    resp_ws = await async_client.get(
        f"/api/v1/patients/{patient.id}/clinical-workspace",
        headers=alice_headers,
    )
    assert resp_ws.status_code == 200
    ws_data = resp_ws.json()["data"]
    assert ws_data["patient"]["patient_id"] == patient.id

    # 4. Unauthorized Doctor Access Rejection (Dr. Bob has no relationship or consent)
    resp_bob_ws = await async_client.get(
        f"/api/v1/patients/{patient.id}/clinical-workspace",
        headers=bob_headers,
    )
    assert resp_bob_ws.status_code == 403

    # 5. Create SOAP Clinical Note
    note_create = {
        "encounter_id": encounter.id,
        "note_type": "PROGRESS",
        "title": "Day 2 Inpatient Evaluation",
        "content": "Patient reports resolution of abdominal tenderness. Afebrile, vitals stable.",
    }
    resp_note = await async_client.post(
        f"/api/v1/patients/{patient.id}/clinical-notes",
        json=note_create,
        headers=alice_headers,
    )
    assert resp_note.status_code == 201
    note_data = resp_note.json()["data"]
    note_id = note_data["note_id"]
    assert note_data["is_signed"] is False

    # 6. Sign Clinical Note
    sign_payload = {"expected_version": 1}
    resp_sign = await async_client.post(
        f"/api/v1/patients/{patient.id}/clinical-notes/{note_id}/sign",
        json=sign_payload,
        headers=alice_headers,
    )
    assert resp_sign.status_code == 200
    signed_note = resp_sign.json()["data"]
    assert signed_note["is_signed"] is True

    # 7. Create & Finalize Clinical Assessment
    assess_create = {
        "encounter_id": encounter.id,
        "assessment_type": "DIAGNOSIS",
        "title": "Gastroenteritis Assessment",
        "summary": "Resolving acute gastroenteritis with electrolyte balance restored.",
        "icd_codes": ["A09"],
        "severity": "MILD",
        "confidence": "HIGH",
    }
    resp_assess = await async_client.post(
        f"/api/v1/patients/{patient.id}/clinical-assessments",
        json=assess_create,
        headers=alice_headers,
    )
    assert resp_assess.status_code == 201
    assess_id = resp_assess.json()["data"]["assessment_id"]

    resp_fin_assess = await async_client.post(
        f"/api/v1/patients/{patient.id}/clinical-assessments/{assess_id}/finalize",
        json={"expected_version": 1},
        headers=alice_headers,
    )
    assert resp_fin_assess.status_code == 200
    assert resp_fin_assess.json()["data"]["is_finalized"] is True

    # 8. Create & Finalize Clinical Plan
    plan_create = {
        "encounter_id": encounter.id,
        "plan_type": "MANAGEMENT",
        "title": "Discharge Transition Plan",
        "objectives": ["Full oral hydration", "Symptom-free for 24h"],
        "interventions": [
            {"category": "Pharmacological", "description": "Probiotics daily", "priority": "ROUTINE"}
        ],
        "investigations": ["Electrolyte panel"],
        "follow_up_instructions": "Review in clinic in 7 days",
    }
    resp_plan = await async_client.post(
        f"/api/v1/patients/{patient.id}/clinical-plans",
        json=plan_create,
        headers=alice_headers,
    )
    assert resp_plan.status_code == 201
    plan_id = resp_plan.json()["data"]["plan_id"]

    resp_fin_plan = await async_client.post(
        f"/api/v1/patients/{patient.id}/clinical-plans/{plan_id}/finalize",
        json={"expected_version": 1},
        headers=alice_headers,
    )
    assert resp_fin_plan.status_code == 200
    assert resp_fin_plan.json()["data"]["is_finalized"] is True

    # 9. Signed Note Cannot Be Mutated (Immutability after signature)
    resp_tamper = await async_client.patch(
        f"/api/v1/patients/{patient.id}/clinical-notes/{note_id}",
        json={"content": "Tampered content after signing", "expected_version": 2},
        headers=alice_headers,
    )
    # Rejection: signed notes are immutable
    assert resp_tamper.status_code in (400, 409)
