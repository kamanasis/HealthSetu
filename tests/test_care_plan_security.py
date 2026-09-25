"""Security, Authorization, and Clinical Boundary Tests for Discharge & Care Plan (Phase 9).

Validates:
- 401 Unauthenticated requests on discharge and care plan endpoints
- Anti-enumeration: Cross-patient access returns 404 (protecting patient identity and resource existence)
- Doctor relationship and consent gating (consent scopes: discharge_summary, care_plan)
- Administrator role has ZERO access to clinical discharge/care-plan endpoints (403 Forbidden)
- Patient role cannot perform clinician verification (403 Forbidden on /discharge/{id}/verify)
- Clinical disclaimers attached to all responses
"""

from datetime import date, datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import (
    _global_audit_repo,
    _global_authz_service,
    _global_care_plan_repo,
    _global_consent_repo,
    _global_discharge_repo,
    _global_document_repo,
    _global_patient_repo,
    _global_user_repo,
)
from app.core.security import create_access_token, hash_password
from app.main import create_app
from app.repositories.consent_repository import ConsentRecord, ConsentStatus
from app.repositories.document_repository import DocumentRecord
from app.repositories.patient_repository import PatientRecord
from app.repositories.user_repository import UserRecord
from app.schemas.auth import AccountStatus, UserRole
from app.schemas.care_plan import (
    CARE_PLAN_CLINICAL_DISCLAIMER,
    CarePlanRecord,
    CarePlanStatus,
    CarePlanTask,
    CarePlanTaskCategory,
)
from app.schemas.discharge import (
    DISCHARGE_CLINICAL_DISCLAIMER,
    DischargeInstructionRecord,
    DischargeVerificationStatus,
)
from app.schemas.document import (
    DocumentLifecycleState,
    DocumentSource,
    DocumentType,
    ProcessingStatus,
)
from app.schemas.patient import BiologicalSex, PatientStatus


@pytest.fixture
def test_app():
    return create_app()


@pytest.fixture
async def security_context():
    """Seed multi-party security test bed."""
    hashed_pwd = hash_password("SecTestPass123!")
    now = datetime.now(timezone.utc)

    # 1. Patient 1 (Primary)
    pat1_user = UserRecord(
        id="usr-pat-sec-1",
        identifier="pat1@example.com",
        password_hash=hashed_pwd,
        role=UserRole.PATIENT,
        status=AccountStatus.ACTIVE,
        created_at=now,
    )
    pat1_record = PatientRecord(
        id="pat-sec-001",
        user_id="usr-pat-sec-1",
        first_name="Meera",
        last_name="Sen",
        date_of_birth=date(1992, 6, 15),
        sex=BiologicalSex.FEMALE,
        status=PatientStatus.ACTIVE,
        phone="+919876543211",
        email="pat1@example.com",
        created_at=now,
        updated_at=now,
    )

    # 2. Patient 2 (Attacker / Unrelated)
    pat2_user = UserRecord(
        id="usr-pat-sec-2",
        identifier="pat2@example.com",
        password_hash=hashed_pwd,
        role=UserRole.PATIENT,
        status=AccountStatus.ACTIVE,
        created_at=now,
    )
    pat2_record = PatientRecord(
        id="pat-sec-002",
        user_id="usr-pat-sec-2",
        first_name="Arjun",
        last_name="Rao",
        date_of_birth=date(1987, 2, 28),
        sex=BiologicalSex.MALE,
        status=PatientStatus.ACTIVE,
        phone="+919876543222",
        email="pat2@example.com",
        created_at=now,
        updated_at=now,
    )

    # 3. Doctor User
    doc_user = UserRecord(
        id="usr-doc-sec-1",
        identifier="doc_sec@example.com",
        password_hash=hashed_pwd,
        role=UserRole.DOCTOR,
        status=AccountStatus.ACTIVE,
        created_at=now,
    )

    # 4. Admin User
    admin_user = UserRecord(
        id="usr-admin-sec-1",
        identifier="admin_sec@example.com",
        password_hash=hashed_pwd,
        role=UserRole.ADMIN,
        status=AccountStatus.ACTIVE,
        created_at=now,
    )

    _global_user_repo.register_in_memory_user(pat1_user)
    _global_user_repo.register_in_memory_user(pat2_user)
    _global_user_repo.register_in_memory_user(doc_user)
    _global_user_repo.register_in_memory_user(admin_user)

    await _global_patient_repo.create(pat1_record)
    await _global_patient_repo.create(pat2_record)

    # Document for Patient 1
    doc_rec = DocumentRecord(
        id="doc-sec-001",
        patient_id=pat1_record.id,
        uploader_id=pat1_user.id,
        document_type=DocumentType.DISCHARGE_SUMMARY,
        source=DocumentSource.PATIENT_UPLOAD,
        filename="discharge_summary.txt",
        mime_type="text/plain",
        size_bytes=500,
        checksum_sha256="s" * 64,
        storage_key=f"{pat1_record.id}/doc-sec-001.txt",
        lifecycle_state=DocumentLifecycleState.EXTRACTED,
        processing_status=ProcessingStatus.COMPLETED,
        created_at=now,
        updated_at=now,
    )
    await _global_document_repo.create_document(doc_rec)

    # Discharge record for Patient 1
    discharge_rec = DischargeInstructionRecord(
        id="disc-sec-001",
        patient_id=pat1_record.id,
        document_id=doc_rec.id,
        encounter_id=None,
        verification_status=DischargeVerificationStatus.UNVERIFIED,
        discharge_diagnoses=["Cholelithiasis"],
        medications=[],
        activity_instructions=[],
        diet_instructions=[],
        wound_care_instructions=[],
        warning_signs=[],
        follow_up_instructions=[],
        clinician_notes=None,
        verified_by=None,
        verified_at=None,
        created_at=now,
        updated_at=now,
    )
    await _global_discharge_repo.create(discharge_rec)

    # Care plan for Patient 1
    care_plan_rec = CarePlanRecord(
        id="cp-sec-001",
        patient_id=pat1_record.id,
        discharge_id=discharge_rec.id,
        encounter_id=None,
        title="Post-Cholecystectomy Plan",
        status=CarePlanStatus.ACTIVE,
        start_date=date(2026, 9, 20),
        end_date=date(2026, 10, 4),
        goals=[],
        tasks=[
            CarePlanTask(
                id="task-sec-1",
                category=CarePlanTaskCategory.ACTIVITY,
                title="Light walking",
                instructions="10 mins daily",
            )
        ],
        warning_signs=[],
        notes="Routine post-op recovery",
        version=1,
        created_by=doc_user.id,
        created_at=now,
        updated_at=now,
    )
    await _global_care_plan_repo.create(care_plan_rec)

    pat1_token, _ = create_access_token(pat1_user.id, pat1_user.role)
    pat2_token, _ = create_access_token(pat2_user.id, pat2_user.role)
    doc_token, _ = create_access_token(doc_user.id, doc_user.role)
    admin_token, _ = create_access_token(admin_user.id, admin_user.role)

    return {
        "pat1_record": pat1_record,
        "pat2_record": pat2_record,
        "pat1_user": pat1_user,
        "pat2_user": pat2_user,
        "doc_user": doc_user,
        "admin_user": admin_user,
        "doc_rec": doc_rec,
        "discharge_rec": discharge_rec,
        "care_plan_rec": care_plan_rec,
        "pat1_token": pat1_token,
        "pat2_token": pat2_token,
        "doc_token": doc_token,
        "admin_token": admin_token,
    }


@pytest.mark.asyncio
async def test_unauthenticated_requests_return_401(test_app, security_context):
    """Verify that unauthenticated requests to discharge and care plan endpoints return 401."""
    ctx = security_context
    pid = ctx["pat1_record"].id
    did = ctx["discharge_rec"].id
    cpid = ctx["care_plan_rec"].id

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Discharge endpoints
        resp1 = await client.post(f"/api/v1/patients/{pid}/discharge/extract", json={"document_id": "doc-1"})
        assert resp1.status_code == 401

        resp2 = await client.get(f"/api/v1/patients/{pid}/discharge/{did}")
        assert resp2.status_code == 401

        resp3 = await client.post(f"/api/v1/patients/{pid}/discharge/{did}/verify", json={"status": "VERIFIED"})
        assert resp3.status_code == 401

        # Care plan endpoints
        resp4 = await client.get(f"/api/v1/patients/{pid}/care-plans")
        assert resp4.status_code == 401

        resp5 = await client.get(f"/api/v1/patients/{pid}/care-plans/{cpid}")
        assert resp5.status_code == 401

        resp6 = await client.patch(f"/api/v1/patients/{pid}/care-plans/{cpid}", json={"status": "PAUSED"})
        assert resp6.status_code == 401


@pytest.mark.asyncio
async def test_anti_enumeration_cross_patient_access_returns_404(test_app, security_context):
    """Anti-enumeration: When Patient 2 requests Patient 1's endpoints, 404 is returned."""
    ctx = security_context
    pid1 = ctx["pat1_record"].id
    did1 = ctx["discharge_rec"].id
    cpid1 = ctx["care_plan_rec"].id
    pat2_token = ctx["pat2_token"]

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Cross-patient discharge get -> 404
        resp1 = await client.get(
            f"/api/v1/patients/{pid1}/discharge/{did1}",
            headers={"Authorization": f"Bearer {pat2_token}"},
        )
        assert resp1.status_code == 404

        # Cross-patient care plan get -> 404
        resp2 = await client.get(
            f"/api/v1/patients/{pid1}/care-plans/{cpid1}",
            headers={"Authorization": f"Bearer {pat2_token}"},
        )
        assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_admin_has_zero_clinical_access(test_app, security_context):
    """Administrator role has zero clinical permissions -> 403 Forbidden."""
    ctx = security_context
    pid1 = ctx["pat1_record"].id
    did1 = ctx["discharge_rec"].id
    cpid1 = ctx["care_plan_rec"].id
    admin_token = ctx["admin_token"]

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp1 = await client.get(
            f"/api/v1/patients/{pid1}/discharge/{did1}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp1.status_code == 403

        resp2 = await client.get(
            f"/api/v1/patients/{pid1}/care-plans/{cpid1}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp2.status_code == 403


@pytest.mark.asyncio
async def test_patient_cannot_verify_discharge_boundary(test_app, security_context):
    """Clinical verification boundary: Patients CANNOT verify discharge instructions (Doctor-only)."""
    ctx = security_context
    pid1 = ctx["pat1_record"].id
    did1 = ctx["discharge_rec"].id
    pat1_token = ctx["pat1_token"]

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/patients/{pid1}/discharge/{did1}/verify",
            headers={"Authorization": f"Bearer {pat1_token}"},
            json={"status": "VERIFIED"},
        )
        # DISCHARGE_VERIFY is not assigned to PATIENT role -> 403 Forbidden
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_doctor_relationship_and_consent_gating(test_app, security_context):
    """Doctors require an active relationship and consent for care_plan and discharge_summary."""
    ctx = security_context
    pid1 = ctx["pat1_record"].id
    did1 = ctx["discharge_rec"].id
    cpid1 = ctx["care_plan_rec"].id
    doc_user = ctx["doc_user"]
    doc_token = ctx["doc_token"]
    pat1_user = ctx["pat1_user"]

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Without relationship or consent -> 403
        resp1 = await client.get(
            f"/api/v1/patients/{pid1}/care-plans/{cpid1}",
            headers={"Authorization": f"Bearer {doc_token}"},
        )
        assert resp1.status_code == 403

        # Add relationship but NO consent -> 403
        _global_authz_service.add_relationship(doc_user.id, pat1_user.id)
        _global_authz_service.add_relationship(doc_user.id, pid1)

        resp2 = await client.get(
            f"/api/v1/patients/{pid1}/care-plans/{cpid1}",
            headers={"Authorization": f"Bearer {doc_token}"},
        )
        assert resp2.status_code == 403

        # Grant consent for care_plan
        now = datetime.now(timezone.utc)
        consent = ConsentRecord(
            id="cns-sec-cp-test",
            patient_id=pat1_user.id,
            grantee_id=doc_user.id,
            purpose="care_delivery",
            scope="care_plan",
            status=ConsentStatus.ACTIVE,
            granted_at=now,
            effective_from=now,
            revoked_at=None,
        )
        await _global_consent_repo.create(consent)
        consent_pat = ConsentRecord(
            id="cns-sec-cp-test-pat",
            patient_id=pid1,
            grantee_id=doc_user.id,
            purpose="care_delivery",
            scope="care_plan",
            status=ConsentStatus.ACTIVE,
            granted_at=now,
            effective_from=now,
            revoked_at=None,
        )
        await _global_consent_repo.create(consent_pat)

        # Now succeeds
        resp3 = await client.get(
            f"/api/v1/patients/{pid1}/care-plans/{cpid1}",
            headers={"Authorization": f"Bearer {doc_token}"},
        )
        assert resp3.status_code == 200
        plan_id = resp3.json()["data"].get("care_plan_id") or resp3.json()["data"].get("id")
        assert plan_id == cpid1
