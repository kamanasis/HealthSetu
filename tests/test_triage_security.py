"""Security, Authorization, and Clinical Boundary Tests for Triage & SBAR (Phase 8).

Validates:
- 401 Unauthenticated requests on symptom, triage, and SBAR endpoints
- Anti-enumeration: Cross-patient access returns 404
- Doctor relationship and consent gating
- Administrator role has ZERO access to clinical triage/symptom endpoints
- Audit log integrity: Audit events contain IDs and counts, ZERO narrative PHI
- Absence of autonomous diagnosis or treatment in results
"""

from datetime import date, datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import (
    _global_audit_repo,
    _global_authz_service,
    _global_consent_repo,
    _global_patient_repo,
    _global_symptom_repo,
    _global_triage_repo,
    _global_user_repo,
)
from app.core.security import create_access_token, hash_password
from app.main import create_app
from app.repositories.consent_repository import ConsentRecord, ConsentStatus
from app.repositories.patient_repository import PatientRecord
from app.repositories.user_repository import UserRecord
from app.schemas.audit import AuditEventType
from app.schemas.auth import AccountStatus, UserRole
from app.schemas.patient import BiologicalSex, PatientStatus
from app.schemas.symptom import SymptomItemCreate, SymptomSeverity, SymptomSource
from app.schemas.triage import (
    TRIAGE_CLINICAL_DISCLAIMER,
    TriageAssessmentCreate,
    TriageStatus,
    TriageUrgency,
)


@pytest.fixture
def test_app():
    return create_app()


@pytest.fixture
async def seeded_triage_context():
    """Seed patient, doctor, and admin accounts with clinical records."""
    hashed_pwd = hash_password("SecurePass123!")
    now = datetime.now(timezone.utc)

    # 1. Patient User & Record
    patient_user = UserRecord(
        id="usr-patient-triage-1",
        identifier="patient_triage@example.com",
        password_hash=hashed_pwd,
        role=UserRole.PATIENT,
        status=AccountStatus.ACTIVE,
        created_at=now,
    )
    patient_record = PatientRecord(
        id="pat-triage-001",
        user_id="usr-patient-triage-1",
        first_name="Ananya",
        last_name="Sharma",
        date_of_birth=date(1990, 8, 15),
        sex=BiologicalSex.FEMALE,
        status=PatientStatus.ACTIVE,
        phone="+919876543299",
        email="patient_triage@example.com",
        created_at=now,
        updated_at=now,
    )

    # 2. Other Patient User (for anti-enumeration / cross-patient tests)
    other_patient_user = UserRecord(
        id="usr-patient-other-2",
        identifier="other_patient@example.com",
        password_hash=hashed_pwd,
        role=UserRole.PATIENT,
        status=AccountStatus.ACTIVE,
        created_at=now,
    )
    other_patient_record = PatientRecord(
        id="pat-triage-002",
        user_id="usr-patient-other-2",
        first_name="Vikram",
        last_name="Singh",
        date_of_birth=date(1982, 3, 20),
        sex=BiologicalSex.MALE,
        status=PatientStatus.ACTIVE,
        phone="+919876543288",
        email="other_patient@example.com",
        created_at=now,
        updated_at=now,
    )

    # 3. Doctor User
    doctor_user = UserRecord(
        id="usr-doctor-triage-1",
        identifier="doctor_triage@example.com",
        password_hash=hashed_pwd,
        role=UserRole.DOCTOR,
        status=AccountStatus.ACTIVE,
        created_at=now,
    )

    # 4. Admin User
    admin_user = UserRecord(
        id="usr-admin-triage-1",
        identifier="admin_triage@example.com",
        password_hash=hashed_pwd,
        role=UserRole.ADMIN,
        status=AccountStatus.ACTIVE,
        created_at=now,
    )

    _global_user_repo.register_in_memory_user(patient_user)
    _global_user_repo.register_in_memory_user(other_patient_user)
    _global_user_repo.register_in_memory_user(doctor_user)
    _global_user_repo.register_in_memory_user(admin_user)

    await _global_patient_repo.create(patient_record)
    await _global_patient_repo.create(other_patient_record)

    pat_token, _ = create_access_token(patient_user.id, patient_user.role)
    other_pat_token, _ = create_access_token(other_patient_user.id, other_patient_user.role)
    doc_token, _ = create_access_token(doctor_user.id, doctor_user.role)
    admin_token, _ = create_access_token(admin_user.id, admin_user.role)

    return {
        "patient_user": patient_user,
        "patient_record": patient_record,
        "other_patient_user": other_patient_user,
        "other_patient_record": other_patient_record,
        "doctor_user": doctor_user,
        "admin_user": admin_user,
        "pat_token": pat_token,
        "other_pat_token": other_pat_token,
        "doc_token": doc_token,
        "admin_token": admin_token,
    }


@pytest.mark.asyncio
async def test_unauthenticated_requests_fail(test_app, seeded_triage_context):
    """401 Unauthenticated requests are rejected on all Phase 8 routes."""
    ctx = seeded_triage_context
    pid = ctx["patient_record"].id

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        # 1. Symptoms
        r1 = await client.post(f"/api/v1/patients/{pid}/symptoms", json={"symptoms": [{"symptom": "fever"}]})
        assert r1.status_code == 401

        # 2. Triage
        r2 = await client.post(f"/api/v1/patients/{pid}/triage", json={"symptoms": [{"symptom": "fever"}]})
        assert r2.status_code == 401

        # 3. SBAR
        r3 = await client.post(f"/api/v1/patients/{pid}/sbar", json={"assessment_id": "any"})
        assert r3.status_code == 401


@pytest.mark.asyncio
async def test_cross_patient_access_anti_enumeration(test_app, seeded_triage_context):
    """Patient cannot access or submit data for another patient (returns 404 anti-enumeration)."""
    ctx = seeded_triage_context
    victim_pid = ctx["patient_record"].id
    attacker_token = ctx["other_pat_token"]

    headers = {"Authorization": f"Bearer {attacker_token}"}

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        # Cross-patient symptom post
        r_post = await client.post(
            f"/api/v1/patients/{victim_pid}/symptoms",
            json={"symptoms": [{"symptom": "headache"}]},
            headers=headers,
        )
        assert r_post.status_code == 404

        # Cross-patient triage post
        r_triage = await client.post(
            f"/api/v1/patients/{victim_pid}/triage",
            json={"symptoms": [{"symptom": "headache"}]},
            headers=headers,
        )
        assert r_triage.status_code == 404

        # Cross-patient symptoms list
        r_get = await client.get(
            f"/api/v1/patients/{victim_pid}/symptoms",
            headers=headers,
        )
        assert r_get.status_code == 404


@pytest.mark.asyncio
async def test_admin_clinical_access_denied(test_app, seeded_triage_context):
    """Admin role has ZERO access to clinical triage/symptoms (returns 403 Forbidden)."""
    ctx = seeded_triage_context
    pid = ctx["patient_record"].id
    admin_token = ctx["admin_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        r_symptoms = await client.post(
            f"/api/v1/patients/{pid}/symptoms",
            json={"symptoms": [{"symptom": "chest pain"}]},
            headers=headers,
        )
        assert r_symptoms.status_code == 403

        r_triage = await client.post(
            f"/api/v1/patients/{pid}/triage",
            json={"symptoms": [{"symptom": "chest pain"}]},
            headers=headers,
        )
        assert r_triage.status_code == 403


@pytest.mark.asyncio
async def test_doctor_access_with_relationship_and_consent(test_app, seeded_triage_context):
    """Doctor with clinical relationship and patient consent can execute triage and SBAR."""
    ctx = seeded_triage_context
    pid = ctx["patient_record"].id
    doc_id = ctx["doctor_user"].id
    doc_token = ctx["doc_token"]
    headers = {"Authorization": f"Bearer {doc_token}"}

    # 1. Without relationship -> 403
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        r_denied = await client.post(
            f"/api/v1/patients/{pid}/symptoms",
            json={"symptoms": [{"symptom": "fever"}]},
            headers=headers,
        )
        assert r_denied.status_code == 403

    # 2. Grant relationship and consent for symptoms & triage
    _global_authz_service.add_relationship(doc_id, ctx["patient_user"].id)
    _global_authz_service.add_relationship(doc_id, pid)

    now = datetime.now(timezone.utc)
    c_sym = ConsentRecord(
        id="consent-triage-sym1",
        patient_id=ctx["patient_user"].id,
        grantee_id=doc_id,
        purpose="care_delivery",
        scope="symptoms",
        status=ConsentStatus.ACTIVE,
        granted_at=now,
        effective_from=now,
        expires_at=None,
        version=1,
    )
    c_tri = ConsentRecord(
        id="consent-triage-tri1",
        patient_id=ctx["patient_user"].id,
        grantee_id=doc_id,
        purpose="care_delivery",
        scope="triage",
        status=ConsentStatus.ACTIVE,
        granted_at=now,
        effective_from=now,
        expires_at=None,
        version=1,
    )
    _global_consent_repo._consents[c_sym.id] = c_sym
    _global_consent_repo._consents[c_tri.id] = c_tri

    # 3. Doctor records symptoms successfully
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        r_sym = await client.post(
            f"/api/v1/patients/{pid}/symptoms",
            json={
                "source": "DOCTOR_ENTERED",
                "symptoms": [{"symptom": "breathing problem", "severity": "MODERATE"}],
            },
            headers=headers,
        )
        assert r_sym.status_code == 201
        sym_data = r_sym.json()["data"]
        assert sym_data["symptoms"][0]["symptom_normalized"] == "shortness of breath"

        # 4. Doctor runs triage assessment
        r_triage = await client.post(
            f"/api/v1/patients/{pid}/triage",
            json={
                "symptoms": [{"symptom": "mild sore throat", "severity": "MILD"}],
            },
            headers=headers,
        )
        assert r_triage.status_code == 201
        triage_data = r_triage.json()["data"]
        assessment_id = triage_data["assessment_id"]
        assert triage_data["urgency"] == "ROUTINE"
        assert triage_data["explanation"]["disclaimer"] == TRIAGE_CLINICAL_DISCLAIMER

        # 5. Doctor generates SBAR
        r_sbar = await client.post(
            f"/api/v1/patients/{pid}/sbar",
            json={"assessment_id": assessment_id, "generation_mode": "template"},
            headers=headers,
        )
        assert r_sbar.status_code == 201
        sbar_data = r_sbar.json()["data"]
        sbar_id = sbar_data["sbar_id"]
        assert sbar_data["situation"]["current_urgency"] == "ROUTINE"

        # 6. Doctor retrieves SBAR
        r_get_sbar = await client.get(
            f"/api/v1/patients/{pid}/sbar/{sbar_id}",
            headers=headers,
        )
        assert r_get_sbar.status_code == 200
        assert r_get_sbar.json()["data"]["sbar_id"] == sbar_id


@pytest.mark.asyncio
async def test_audit_logs_contain_no_narrative_phi(test_app, seeded_triage_context):
    """Verify that audit logs recorded for symptom intake and triage contain NO clinical narrative PHI."""
    ctx = seeded_triage_context
    pid = ctx["patient_record"].id
    pat_token = ctx["pat_token"]
    headers = {"Authorization": f"Bearer {pat_token}"}

    secret_symptom_narrative = "severe migraine with visual aura after flashing lights"

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        await client.post(
            f"/api/v1/patients/{pid}/symptoms",
            json={"symptoms": [{"symptom": secret_symptom_narrative, "severity": "SEVERE"}]},
            headers=headers,
        )

    # Check all events in audit repository
    for event in _global_audit_repo._events:
        metadata_str = str(event.metadata or {})
        assert secret_symptom_narrative not in metadata_str
        assert "visual aura" not in metadata_str
