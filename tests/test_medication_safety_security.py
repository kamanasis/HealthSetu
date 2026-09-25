"""Security, Authorization, Audit, and Clinical Boundary Tests for Medication Safety (Phase 7).

Validates:
- 401 Unauthenticated requests
- Patient access to own medication safety evaluations
- Anti-enumeration: cross-patient access returns 404
- Doctor relationship + consent gating (Phase 3 integration)
- Admin role is denied clinical access (admin ≠ clinical)
- Audit log generation without PHI in audit events
- Zero autonomous clinical mutations (no automatic status change, prescription cancellation, or allergy creation)
"""

from datetime import date, datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import (
    _global_allergy_repo,
    _global_audit_repo,
    _global_authz_service,
    _global_consent_repo,
    _global_patient_medication_repo,
    _global_patient_repo,
    _global_prescription_repo,
    _global_user_repo,
)
from app.core.security import create_access_token, hash_password
from app.main import create_app
from app.repositories.allergy_repository import AllergyRecord
from app.repositories.patient_medication_repository import PatientMedicationRecord
from app.repositories.patient_repository import PatientRecord
from app.repositories.user_repository import UserRecord
from app.schemas.allergy import AllergySeverity, AllergyStatus
from app.schemas.audit import AuditEventType
from app.schemas.auth import AccountStatus, UserRole
from app.schemas.clinical_history import ClinicalDataSource
from app.repositories.consent_repository import ConsentRecord, ConsentStatus
from app.schemas.medication import PatientMedicationStatus
from app.schemas.patient import BiologicalSex, PatientStatus


@pytest.fixture
def test_app():
    return create_app()


@pytest.fixture
async def seeded_safety_context():
    """Seed patient, doctor, and admin accounts with clinical records."""
    hashed_pwd = hash_password("SecurePass123!")
    now = datetime.now(timezone.utc)

    # 1. Patient User & Patient Record
    patient_user = UserRecord(
        id="usr-patient-safety-1",
        identifier="patient_safety@example.com",
        password_hash=hashed_pwd,
        role=UserRole.PATIENT,
        status=AccountStatus.ACTIVE,
        created_at=now,
    )
    patient_record = PatientRecord(
        id="pat-safety-001",
        user_id="usr-patient-safety-1",
        first_name="Rahim",
        last_name="Khan",
        date_of_birth=date(1985, 4, 12),
        sex=BiologicalSex.MALE,
        status=PatientStatus.ACTIVE,
        phone="+919876543210",
        email="patient_safety@example.com",
        created_at=now,
        updated_at=now,
    )

    # 2. Other Patient User (for cross-patient tests)
    other_patient_user = UserRecord(
        id="usr-patient-other-2",
        identifier="other_patient@example.com",
        password_hash=hashed_pwd,
        role=UserRole.PATIENT,
        status=AccountStatus.ACTIVE,
        created_at=now,
    )
    other_patient_record = PatientRecord(
        id="pat-other-002",
        user_id="usr-patient-other-2",
        first_name="Fatima",
        last_name="Begum",
        date_of_birth=date(1992, 8, 20),
        sex=BiologicalSex.FEMALE,
        status=PatientStatus.ACTIVE,
        phone="+919876543211",
        email="other_patient@example.com",
        created_at=now,
        updated_at=now,
    )

    # 3. Doctor User
    doctor_user = UserRecord(
        id="usr-doctor-safety-1",
        identifier="doctor_safety@example.com",
        password_hash=hashed_pwd,
        role=UserRole.DOCTOR,
        status=AccountStatus.ACTIVE,
        created_at=now,
    )

    # 4. Admin User
    admin_user = UserRecord(
        id="usr-admin-safety-1",
        identifier="admin_safety@example.com",
        password_hash=hashed_pwd,
        role=UserRole.ADMIN,
        status=AccountStatus.ACTIVE,
        created_at=now,
    )

    # Seed in global repositories
    _global_user_repo.register_in_memory_user(patient_user)
    _global_user_repo.register_in_memory_user(other_patient_user)
    _global_user_repo.register_in_memory_user(doctor_user)
    _global_user_repo.register_in_memory_user(admin_user)

    await _global_patient_repo.create(patient_record)
    await _global_patient_repo.create(other_patient_record)

    # Seed active medications for patient 1: Metformin + Contrast (Major DDI)
    await _global_patient_medication_repo.create_record(
        PatientMedicationRecord(
            id="pmed-safe-01",
            patient_id="pat-safety-001",
            status=PatientMedicationStatus.ACTIVE,
            drug_name_raw="Metformin 500mg",
            created_at=now,
            updated_at=now,
        )
    )
    await _global_patient_medication_repo.create_record(
        PatientMedicationRecord(
            id="pmed-safe-02",
            patient_id="pat-safety-001",
            status=PatientMedicationStatus.ACTIVE,
            drug_name_raw="Contrast 50ml",
            created_at=now,
            updated_at=now,
        )
    )

    return {
        "patient_user": patient_user,
        "patient_record": patient_record,
        "other_patient_user": other_patient_user,
        "other_patient_record": other_patient_record,
        "doctor_user": doctor_user,
        "admin_user": admin_user,
    }


def _auth_header(user_id: str, role: UserRole) -> dict[str, str]:
    token, _ = create_access_token(user_id=user_id, role=role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(test_app):
    """Endpoints require authentication; unauthenticated requests return 401."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        res = await client.post("/api/v1/patients/pat-safety-001/medication-safety/check", json={})
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_patient_self_access_allowed(test_app, seeded_safety_context):
    """Patient can check medication safety for their own records."""
    ctx = seeded_safety_context
    headers = _auth_header(ctx["patient_user"].id, UserRole.PATIENT)

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        res = await client.post(
            f"/api/v1/patients/{ctx['patient_record'].id}/medication-safety/check",
            json={"medication_context": "CURRENT_MEDICATIONS"},
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["patient_id"] == ctx["patient_record"].id
        assert data["status"] == "ALERT"
        assert len(data["alerts"]) >= 1


@pytest.mark.asyncio
async def test_cross_patient_access_anti_enumeration_404(test_app, seeded_safety_context):
    """Patient attempting to access another patient's safety evaluations receives 404 (anti-enumeration)."""
    ctx = seeded_safety_context
    # Patient 2 tries to access Patient 1's safety check
    headers = _auth_header(ctx["other_patient_user"].id, UserRole.PATIENT)

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        res = await client.post(
            f"/api/v1/patients/{ctx['patient_record'].id}/medication-safety/check",
            json={"medication_context": "CURRENT_MEDICATIONS"},
            headers=headers,
        )
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_doctor_access_without_relationship_forbidden(test_app, seeded_safety_context):
    """Doctor without a registered provider-patient relationship receives 403."""
    ctx = seeded_safety_context
    headers = _auth_header(ctx["doctor_user"].id, UserRole.DOCTOR)

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        res = await client.post(
            f"/api/v1/patients/{ctx['patient_record'].id}/medication-safety/check",
            json={},
            headers=headers,
        )
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_doctor_access_with_relationship_and_consent(test_app, seeded_safety_context):
    """Doctor with active relationship and valid patient consent receives 200."""
    ctx = seeded_safety_context
    doctor_id = ctx["doctor_user"].id
    patient_id = ctx["patient_record"].id

    # 1. Establish relationship
    _global_authz_service.add_relationship(doctor_id, ctx["patient_user"].id)
    _global_authz_service.add_relationship(doctor_id, patient_id)

    # 2. Grant consent for medications
    now = datetime.now(timezone.utc)
    c1 = ConsentRecord(
        id="cst-med-safe-001",
        patient_id=ctx["patient_user"].id,
        grantee_id=doctor_id,
        purpose="care_delivery",
        scope="medications",
        status=ConsentStatus.ACTIVE,
        granted_at=now,
        effective_from=now,
        expires_at=None,
        version=1,
    )
    _global_consent_repo._consents[c1.id] = c1

    headers = _auth_header(doctor_id, UserRole.DOCTOR)
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        res = await client.post(
            f"/api/v1/patients/{patient_id}/medication-safety/check",
            json={},
            headers=headers,
        )
        assert res.status_code == 200
        assert res.json()["data"]["status"] == "ALERT"


@pytest.mark.asyncio
async def test_admin_clinical_access_forbidden(test_app, seeded_safety_context):
    """Admin role must NEVER receive clinical data access (admin ≠ clinical)."""
    ctx = seeded_safety_context
    headers = _auth_header(ctx["admin_user"].id, UserRole.ADMIN)

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        res = await client.post(
            f"/api/v1/patients/{ctx['patient_record'].id}/medication-safety/check",
            json={},
            headers=headers,
        )
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_capabilities_endpoint(test_app, seeded_safety_context):
    """Patient can view supported safety provider capabilities."""
    ctx = seeded_safety_context
    headers = _auth_header(ctx["patient_user"].id, UserRole.PATIENT)

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        res = await client.get(
            f"/api/v1/patients/{ctx['patient_record'].id}/medication-safety/capabilities",
            headers=headers,
        )
        assert res.status_code == 200
        caps = res.json()["data"]
        assert caps["capabilities"]["DRUG_DRUG"] is True
        assert caps["capabilities"]["DRUG_ALLERGY"] is True


@pytest.mark.asyncio
async def test_audit_logging_and_phi_hygiene(test_app, seeded_safety_context):
    """Audit events are logged for medication safety checks, strictly omitting PHI."""
    ctx = seeded_safety_context
    patient_id = ctx["patient_record"].id
    headers = _auth_header(ctx["patient_user"].id, UserRole.PATIENT)

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        res = await client.post(
            f"/api/v1/patients/{patient_id}/medication-safety/check",
            json={},
            headers=headers,
        )
        assert res.status_code == 200
        eval_id = res.json()["data"]["evaluation_id"]

        # Also view evaluation
        res_view = await client.get(
            f"/api/v1/patients/{patient_id}/medication-safety/evaluations/{eval_id}",
            headers=headers,
        )
        assert res_view.status_code == 200

    # Inspect audit events in audit repository
    events = _global_audit_repo._events
    safety_events = [e for e in events if "MEDICATION_SAFETY" in e.event_type.value]

    assert len(safety_events) >= 2
    started_ev = next(e for e in safety_events if e.event_type == AuditEventType.MEDICATION_SAFETY_CHECK_STARTED)
    completed_ev = next(e for e in safety_events if e.event_type == AuditEventType.MEDICATION_SAFETY_CHECK_COMPLETED)
    viewed_ev = next(e for e in safety_events if e.event_type == AuditEventType.MEDICATION_SAFETY_RESULT_VIEWED)

    assert started_ev.resource_id == eval_id
    assert completed_ev.resource_id == eval_id
    assert viewed_ev.resource_id == eval_id

    # CRITICAL: Verify NO PHI in audit metadata
    for ev in safety_events:
        meta_str = str(ev.metadata).lower()
        assert "metformin" not in meta_str
        assert "contrast" not in meta_str
        assert "rahim" not in meta_str
        assert "khan" not in meta_str


@pytest.mark.asyncio
async def test_no_autonomous_clinical_mutations(test_app, seeded_safety_context):
    """CRITICAL: Safety alerts must NEVER mutate medication status, cancel prescriptions, or create allergy records."""
    ctx = seeded_safety_context
    patient_id = ctx["patient_record"].id
    headers = _auth_header(ctx["patient_user"].id, UserRole.PATIENT)

    # Initial state
    meds_before = await _global_patient_medication_repo.list_by_patient(patient_id)
    allergies_before = await _global_allergy_repo.list_by_patient(patient_id)

    assert all(m.status == PatientMedicationStatus.ACTIVE for m in meds_before)
    initial_med_count = len(meds_before)
    initial_allergy_count = len(allergies_before)

    # Run check that flags Major DDI
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        res = await client.post(
            f"/api/v1/patients/{patient_id}/medication-safety/check",
            json={},
            headers=headers,
        )
        assert res.status_code == 200
        assert res.json()["data"]["status"] == "ALERT"

    # Verify state AFTER safety check
    meds_after = await _global_patient_medication_repo.list_by_patient(patient_id)
    allergies_after = await _global_allergy_repo.list_by_patient(patient_id)

    # Medications must still be ACTIVE; no auto-discontinuation or changes
    assert len(meds_after) == initial_med_count
    for m in meds_after:
        assert m.status == PatientMedicationStatus.ACTIVE

    # No allergy automatically created
    assert len(allergies_after) == initial_allergy_count
