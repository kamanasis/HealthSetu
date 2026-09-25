"""Tests for Personalized Care Plan Service and Synthesis from Discharge (Phase 9).

Validates:
- Direct creation of personalized care plans
- Synthesis of actionable daily schedule from discharge instructions
- Clinical verification boundary enforcement:
  - UNVERIFIED discharge instructions rejected with CARE_PLAN_UNVERIFIED_DISCHARGE
  - Verified discharge instructions synthesize medication, activity, and follow-up tasks
- Task completion and progress tracking
- Audit event generation
- API endpoint integration
"""

from datetime import date, datetime, timedelta, timezone
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import (
    _global_audit_repo,
    _global_authz_service,
    _global_care_plan_repo,
    _global_consent_repo,
    _global_discharge_repo,
    _global_patient_repo,
    _global_user_repo,
)
from app.core.exceptions import AppException, ErrorCode
from app.core.security import create_access_token, hash_password
from app.main import create_app
from app.repositories.consent_repository import ConsentRecord, ConsentStatus
from app.repositories.patient_repository import PatientRecord
from app.repositories.user_repository import UserRecord
from app.schemas.audit import AuditEventType
from app.schemas.auth import AccountStatus, UserRole
from app.schemas.care_plan import (
    CARE_PLAN_CLINICAL_DISCLAIMER,
    CarePlanCreate,
    CarePlanGenerateFromDischargeRequest,
    CarePlanGoal,
    CarePlanStatus,
    CarePlanTask,
    CarePlanTaskCategory,
    CarePlanTaskStatus,
    CarePlanUpdate,
    CarePlanWarningSignGuidance,
)
from app.schemas.discharge import (
    DischargeActivityInstruction,
    DischargeFollowUpItem,
    DischargeInstructionRecord,
    DischargeMedicationItem,
    DischargeVerificationStatus,
    DischargeWarningSign,
    DischargeWoundCareInstruction,
)
from app.schemas.patient import BiologicalSex, PatientStatus
from app.services.audit_service import AuditService
from app.services.care_plan_service import CarePlanService


@pytest.fixture
def test_app():
    return create_app()


@pytest.fixture
async def care_plan_context():
    """Seed patient, doctor, discharge instructions, and care plan setup."""
    hashed_pwd = hash_password("CarePlanSecure123!")
    now = datetime.now(timezone.utc)

    # 1. Patient User & Record
    pat_user = UserRecord(
        id="usr-pat-cp-001",
        identifier="cp_patient@example.com",
        password_hash=hashed_pwd,
        role=UserRole.PATIENT,
        status=AccountStatus.ACTIVE,
        created_at=now,
    )
    pat_record = PatientRecord(
        id="pat-cp-001",
        user_id="usr-pat-cp-001",
        first_name="Rohan",
        last_name="Gupta",
        date_of_birth=date(1978, 11, 25),
        sex=BiologicalSex.MALE,
        status=PatientStatus.ACTIVE,
        phone="+919876543202",
        email="cp_patient@example.com",
        created_at=now,
        updated_at=now,
    )

    # 2. Doctor User
    doc_user = UserRecord(
        id="usr-doc-cp-001",
        identifier="cp_doctor@example.com",
        password_hash=hashed_pwd,
        role=UserRole.DOCTOR,
        status=AccountStatus.ACTIVE,
        created_at=now,
    )

    _global_user_repo.register_in_memory_user(pat_user)
    _global_user_repo.register_in_memory_user(doc_user)
    await _global_patient_repo.create(pat_record)

    _global_authz_service.add_relationship(doc_user.id, pat_user.id)
    _global_authz_service.add_relationship(doc_user.id, pat_record.id)

    # Grant consent for both care_plan and discharge_summary
    for scope in ["care_plan", "discharge_summary"]:
        c_user = ConsentRecord(
            id=f"cns-cp-{scope}-u",
            patient_id=pat_user.id,
            grantee_id=doc_user.id,
            purpose="care_delivery",
            scope=scope,
            status=ConsentStatus.ACTIVE,
            granted_at=now,
            effective_from=now,
            revoked_at=None,
        )
        await _global_consent_repo.create(c_user)
        c_pat = ConsentRecord(
            id=f"cns-cp-{scope}-p",
            patient_id=pat_record.id,
            grantee_id=doc_user.id,
            purpose="care_delivery",
            scope=scope,
            status=ConsentStatus.ACTIVE,
            granted_at=now,
            effective_from=now,
            revoked_at=None,
        )
        await _global_consent_repo.create(c_pat)

    # 3. Unverified Discharge Record
    unverified_discharge = DischargeInstructionRecord(
        id="disc-rec-unverified-001",
        patient_id=pat_record.id,
        document_id="doc-test-001",
        encounter_id="enc-test-001",
        verification_status=DischargeVerificationStatus.UNVERIFIED,
        discharge_diagnoses=["Post-Appendectomy"],
        medications=[
            DischargeMedicationItem(
                drug_name="Amoxicillin-Clavulanate",
                dosage="875-125 mg",
                frequency="Twice daily",
                route="Oral",
                instructions="Take with food for 7 days",
            )
        ],
        activity_instructions=[
            DischargeActivityInstruction(category="RESTRICTION", description="No heavy lifting > 15 lbs for 2 weeks")
        ],
        diet_instructions=[],
        wound_care_instructions=[
            DischargeWoundCareInstruction(site="Abdomen", dressing_instructions="Keep incision clean and dry")
        ],
        warning_signs=[
            DischargeWarningSign(symptom="Fever > 101F or spreading erythema", action_required="Contact surgical team immediately")
        ],
        follow_up_instructions=[
            DischargeFollowUpItem(provider_or_specialty="General Surgery Clinic", recommended_timeframe="10-14 days", purpose="Incision check")
        ],
        clinician_notes=None,
        verified_by=None,
        verified_at=None,
        created_at=now,
        updated_at=now,
    )
    await _global_discharge_repo.create(unverified_discharge)

    # 4. Verified Discharge Record
    verified_discharge = DischargeInstructionRecord(
        id="disc-rec-verified-001",
        patient_id=pat_record.id,
        document_id="doc-test-002",
        encounter_id="enc-test-002",
        verification_status=DischargeVerificationStatus.VERIFIED,
        discharge_diagnoses=["Post-CABG Recovery", "Coronary Artery Disease"],
        medications=[
            DischargeMedicationItem(
                drug_name="Metoprolol Succinate",
                dosage="50 mg",
                frequency="Daily",
                route="Oral",
                instructions="Take in morning with breakfast",
            ),
            DischargeMedicationItem(
                drug_name="Aspirin",
                dosage="81 mg",
                frequency="Daily",
                route="Oral",
                instructions="Indefinitely",
            ),
        ],
        activity_instructions=[
            DischargeActivityInstruction(category="RESTRICTION", description="Avoid sternal strain; daily flat walk 15 mins")
        ],
        diet_instructions=[],
        wound_care_instructions=[
            DischargeWoundCareInstruction(site="Sternal incision", dressing_instructions="Wash gently with soap and water")
        ],
        warning_signs=[
            DischargeWarningSign(symptom="Severe chest pain or clicking sensation in sternum", action_required="Call 911 or return to ER")
        ],
        follow_up_instructions=[
            DischargeFollowUpItem(provider_or_specialty="Cardiac Rehabilitation", recommended_timeframe="21 days", purpose="Initial intake evaluation")
        ],
        clinician_notes="Patient educated on sternal precautions.",
        verified_by=doc_user.id,
        verified_at=now,
        created_at=now,
        updated_at=now,
    )
    await _global_discharge_repo.create(verified_discharge)

    pat_token, _ = create_access_token(pat_user.id, pat_user.role)
    doc_token, _ = create_access_token(doc_user.id, doc_user.role)

    return {
        "pat_user": pat_user,
        "pat_record": pat_record,
        "doc_user": doc_user,
        "unverified_discharge": unverified_discharge,
        "verified_discharge": verified_discharge,
        "pat_token": pat_token,
        "doc_token": doc_token,
    }


@pytest.mark.asyncio
async def test_care_plan_verification_boundary_enforcement(care_plan_context):
    """Enforce that unverified discharge summaries CANNOT generate an active care plan."""
    ctx = care_plan_context
    pat_record = ctx["pat_record"]
    doc_user = ctx["doc_user"]
    unverified_discharge = ctx["unverified_discharge"]
    verified_discharge = ctx["verified_discharge"]

    audit_svc = AuditService(audit_repository=_global_audit_repo)
    cp_svc = CarePlanService(
        care_plan_repo=_global_care_plan_repo,
        discharge_repo=_global_discharge_repo,
        audit_service=audit_svc,
    )

    # 1. Attempting synthesis from UNVERIFIED discharge instructions must raise CARE_PLAN_UNVERIFIED_DISCHARGE
    req_unverified = CarePlanGenerateFromDischargeRequest(
        discharge_id=unverified_discharge.id,
        horizon_days=14,
        require_verified=True,
    )

    with pytest.raises(AppException) as exc_info:
        await cp_svc.generate_from_discharge(
            patient_id=pat_record.id,
            payload=req_unverified,
            actor_id=doc_user.id,
        )
    assert exc_info.value.code == ErrorCode.CARE_PLAN_UNVERIFIED_DISCHARGE
    assert exc_info.value.status_code == 400

    # 2. Generating from VERIFIED discharge instructions succeeds
    req_verified = CarePlanGenerateFromDischargeRequest(
        discharge_id=verified_discharge.id,
        horizon_days=21,
        require_verified=True,
    )

    plan = await cp_svc.generate_from_discharge(
        patient_id=pat_record.id,
        payload=req_verified,
        actor_id=doc_user.id,
    )

    assert plan.id is not None
    assert plan.patient_id == pat_record.id
    assert plan.discharge_id == verified_discharge.id
    assert plan.status == CarePlanStatus.ACTIVE
    assert plan.disclaimer == CARE_PLAN_CLINICAL_DISCLAIMER

    # Check tasks generated
    categories = [t.category for t in plan.tasks]
    assert CarePlanTaskCategory.MEDICATION in categories
    assert CarePlanTaskCategory.ACTIVITY in categories
    assert CarePlanTaskCategory.WOUND_CARE in categories
    assert CarePlanTaskCategory.FOLLOW_UP_APPOINTMENT in categories

    # Check warning sign red flags preserved
    assert len(plan.warning_signs) >= 1
    assert any("sternum" in ws.red_flag.lower() for ws in plan.warning_signs)


@pytest.mark.asyncio
async def test_care_plan_task_completion_and_update(care_plan_context):
    """Test updating care plan status and completing daily tasks."""
    ctx = care_plan_context
    pat_record = ctx["pat_record"]
    doc_user = ctx["doc_user"]
    pat_user = ctx["pat_user"]
    verified_discharge = ctx["verified_discharge"]

    audit_svc = AuditService(audit_repository=_global_audit_repo)
    cp_svc = CarePlanService(
        care_plan_repo=_global_care_plan_repo,
        discharge_repo=_global_discharge_repo,
        audit_service=audit_svc,
    )

    # 1. Generate plan
    plan = await cp_svc.generate_from_discharge(
        patient_id=pat_record.id,
        payload=CarePlanGenerateFromDischargeRequest(
            discharge_id=verified_discharge.id,
            horizon_days=14,
        ),
        actor_id=doc_user.id,
    )

    first_task_id = plan.tasks[0].id

    # 2. Update: patient completes the first task
    update_res = await cp_svc.update_care_plan(
        patient_id=pat_record.id,
        care_plan_id=plan.id,
        payload=CarePlanUpdate(
            complete_task_ids=[first_task_id],
            notes="Morning dose taken on time.",
        ),
        actor_id=pat_user.id,
    )

    assert update_res.version == 2
    # Verify task status is now COMPLETED
    updated_first_task = next(t for t in update_res.tasks if t.id == first_task_id)
    assert updated_first_task.status == CarePlanTaskStatus.COMPLETED
    assert updated_first_task.completed_at is not None

    # Check audit log
    events = [e for e in _global_audit_repo._events if (e.metadata or {}).get("patient_id") == pat_record.id]
    types = [e.event_type for e in events]
    assert AuditEventType.CARE_PLAN_CREATED in types
    assert AuditEventType.CARE_PLAN_UPDATED in types


@pytest.mark.asyncio
async def test_care_plan_api_endpoints(test_app, care_plan_context):
    """Test Care Plan FastAPI endpoints."""
    ctx = care_plan_context
    pat_record = ctx["pat_record"]
    doc_token = ctx["doc_token"]
    pat_token = ctx["pat_token"]
    unverified_discharge = ctx["unverified_discharge"]
    verified_discharge = ctx["verified_discharge"]

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Attempt synthesis from unverified discharge -> Expect 400
        unverified_resp = await client.post(
            f"/api/v1/patients/{pat_record.id}/care-plans/from-discharge",
            headers={"Authorization": f"Bearer {doc_token}"},
            json={
                "discharge_id": unverified_discharge.id,
                "horizon_days": 14,
                "require_verified": True,
            },
        )
        assert unverified_resp.status_code == 400
        assert unverified_resp.json()["error"]["code"] == "CARE_PLAN_UNVERIFIED_DISCHARGE"

        # 2. Synthesis from verified discharge -> Expect 201
        verified_resp = await client.post(
            f"/api/v1/patients/{pat_record.id}/care-plans/from-discharge",
            headers={"Authorization": f"Bearer {doc_token}"},
            json={
                "discharge_id": verified_discharge.id,
                "horizon_days": 14,
                "require_verified": True,
            },
        )
        assert verified_resp.status_code == 201
        plan_data = verified_resp.json()["data"]
        plan_id = plan_data.get("care_plan_id") or plan_data.get("id")
        assert plan_data["status"] == "ACTIVE"
        assert len(plan_data["tasks"]) >= 3

        # 3. List care plans for patient
        list_resp = await client.get(
            f"/api/v1/patients/{pat_record.id}/care-plans",
            headers={"Authorization": f"Bearer {pat_token}"},
        )
        assert list_resp.status_code == 200
        list_data = list_resp.json()["data"]
        assert list_data["total"] >= 1
        assert any(p["id"] == plan_id for p in list_data["items"])

        # 4. Get specific care plan
        get_resp = await client.get(
            f"/api/v1/patients/{pat_record.id}/care-plans/{plan_id}",
            headers={"Authorization": f"Bearer {pat_token}"},
        )
        assert get_resp.status_code == 200
        retrieved_id = get_resp.json()["data"].get("care_plan_id") or get_resp.json()["data"].get("id")
        assert retrieved_id == plan_id

        # 5. Patch task completion (Patient updates task)
        task_id = plan_data["tasks"][0]["id"]
        patch_resp = await client.patch(
            f"/api/v1/patients/{pat_record.id}/care-plans/{plan_id}",
            headers={"Authorization": f"Bearer {pat_token}"},
            json={"complete_task_ids": [task_id]},
        )
        assert patch_resp.status_code == 200
        patched_data = patch_resp.json()["data"]
        t = next(x for x in patched_data["tasks"] if x["id"] == task_id)
        assert t["status"] == "COMPLETED"
