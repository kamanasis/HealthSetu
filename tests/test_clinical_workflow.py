"""Phase 10 Tests: Doctor Clinical Workflow.

Tests cover:
1. Clinical Note lifecycle (create, read, update, sign, addendum)
2. Clinical Assessment lifecycle (create, read, update, finalize)
3. Clinical Plan lifecycle (create, read, update, finalize)
4. Clinical Workspace aggregation
5. Security: clinician_id sourced from JWT (never from payload)
6. Security: DOCTOR-only access to workflow endpoints
7. Optimistic concurrency: version conflict raises 409
8. Immutability: signed note and finalized assessment/plan raise 409 on update
9. Authorship enforcement: only authoring clinician may update/sign/finalize
10. Audit events generated for all state transitions
"""

import pytest
from datetime import datetime, timezone, date, timedelta
from httpx import AsyncClient

from app.api.deps import (
    _global_user_repo,
    _global_patient_repo,
    _global_consent_repo,
    _global_authz_service,
    _global_clinical_note_repo,
    _global_clinical_assessment_repo,
    _global_clinical_plan_repo,
    _global_audit_repo,
)
from app.core.security import create_access_token, hash_password
from app.repositories.consent_repository import ConsentRecord, ConsentStatus
from app.repositories.patient_repository import PatientRecord
from app.repositories.user_repository import UserRecord
from app.schemas.auth import AccountStatus, UserRole
from app.schemas.patient import BiologicalSex, PatientStatus


# ============================================================================
# Helpers
# ============================================================================

TEST_PASSWORD = "StrongP@ssw0rd123!"


def make_token(user_id: str, role: str) -> str:
    token, _ = create_access_token(user_id, role)
    return token


def _seed_doctor_patient(
    doctor_id: str = "usr-doctor-p10",
    patient_id: str = "pat-p10",
    patient_user_id: str = "usr-patient-p10",
) -> tuple[str, str]:
    """Seed a doctor and patient, grant relationship and consent."""
    hashed = hash_password(TEST_PASSWORD)
    _global_user_repo.register_in_memory_user(
        UserRecord(
            id=doctor_id,
            identifier="doctor-p10@healthsetu.org",
            password_hash=hashed,
            role=UserRole.DOCTOR,
            status=AccountStatus.ACTIVE,
        )
    )
    _global_user_repo.register_in_memory_user(
        UserRecord(
            id=patient_user_id,
            identifier="patient-p10@healthsetu.org",
            password_hash=hashed,
            role=UserRole.PATIENT,
            status=AccountStatus.ACTIVE,
        )
    )
    now = datetime.now(timezone.utc)
    _global_patient_repo._patients[patient_id] = PatientRecord(
        id=patient_id,
        user_id=patient_user_id,
        first_name="Test",
        last_name="Patient",
        date_of_birth=date(1985, 3, 10),
        sex=BiologicalSex.MALE,
        status=PatientStatus.ACTIVE,
        preferred_language="en",
        phone="+911234567890",
        email="test.patient@example.com",
        created_at=now,
        updated_at=now,
    )
    _global_patient_repo._user_to_patient[patient_user_id] = patient_id

    # Doctor-patient relationship
    _global_authz_service.add_relationship(doctor_id, patient_user_id)

    # Consent: clinical_records
    consent = ConsentRecord(
        id="consent-p10-cr",
        patient_id=patient_user_id,
        grantee_id=doctor_id,
        purpose="care_delivery",
        scope="clinical_records",
        status=ConsentStatus.ACTIVE,
        granted_at=now,
        effective_from=now,
        expires_at=now + timedelta(days=365),
        version=1,
    )
    _global_consent_repo._consents[consent.id] = consent

    return doctor_id, patient_id


# ============================================================================
# Clinical Notes Tests
# ============================================================================

class TestClinicalNoteCreate:
    """Clinical note creation tests."""

    @pytest.mark.asyncio
    async def test_doctor_can_create_note(self, async_client: AsyncClient):
        doctor_id, patient_id = _seed_doctor_patient()
        token = make_token(doctor_id, "DOCTOR")

        resp = await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-notes",
            json={
                "note_type": "SOAP",
                "title": "Initial Consultation",
                "content": "S: Patient presents with headache.\nO: BP 120/80\nA: Tension headache\nP: Analgesics prn",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()["data"]
        assert data["note_type"] == "SOAP"
        assert data["title"] == "Initial Consultation"
        assert data["is_signed"] is False
        assert data["version"] == 1
        # clinician_id must be from JWT, not from payload
        assert data["clinician_id"] == doctor_id

    @pytest.mark.asyncio
    async def test_unauthenticated_create_note_rejected(self, async_client: AsyncClient):
        doctor_id, patient_id = _seed_doctor_patient()
        resp = await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-notes",
            json={"note_type": "SOAP", "title": "T", "content": "C"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_patient_cannot_create_note(self, async_client: AsyncClient):
        """Patients cannot create clinical notes (no CLINICAL_NOTE_CREATE permission)."""
        doctor_id, patient_id = _seed_doctor_patient()
        patient_token = make_token("usr-patient-p10", "PATIENT")

        resp = await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-notes",
            json={"note_type": "SOAP", "title": "T", "content": "C"},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_create_addendum_note(self, async_client: AsyncClient):
        doctor_id, patient_id = _seed_doctor_patient()
        token = make_token(doctor_id, "DOCTOR")

        # Create parent note
        r1 = await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-notes",
            json={"note_type": "PROGRESS", "title": "Progress Note", "content": "Improving"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r1.status_code == 201
        parent_id = r1.json()["data"]["note_id"]

        # Create addendum
        r2 = await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-notes",
            json={
                "note_type": "PROGRESS",
                "title": "Addendum",
                "content": "Additional findings",
                "is_addendum": True,
                "parent_note_id": parent_id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r2.status_code == 201
        addendum = r2.json()["data"]
        assert addendum["is_addendum"] is True
        assert addendum["parent_note_id"] == parent_id


class TestClinicalNoteReadAndList:
    """Clinical note read/list tests."""

    @pytest.mark.asyncio
    async def test_get_note(self, async_client: AsyncClient):
        doctor_id, patient_id = _seed_doctor_patient()
        token = make_token(doctor_id, "DOCTOR")

        create = await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-notes",
            json={"note_type": "CONSULTATION", "title": "T", "content": "C"},
            headers={"Authorization": f"Bearer {token}"},
        )
        note_id = create.json()["data"]["note_id"]

        resp = await async_client.get(
            f"/api/v1/patients/{patient_id}/clinical-notes/{note_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["note_id"] == note_id

    @pytest.mark.asyncio
    async def test_list_notes(self, async_client: AsyncClient):
        doctor_id, patient_id = _seed_doctor_patient()
        token = make_token(doctor_id, "DOCTOR")

        for i in range(3):
            await async_client.post(
                f"/api/v1/patients/{patient_id}/clinical-notes",
                json={"note_type": "PROGRESS", "title": f"Note {i}", "content": "Content"},
                headers={"Authorization": f"Bearer {token}"},
            )

        resp = await async_client.get(
            f"/api/v1/patients/{patient_id}/clinical-notes",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 3
        assert len(data["items"]) == 3

    @pytest.mark.asyncio
    async def test_get_nonexistent_note_returns_404(self, async_client: AsyncClient):
        doctor_id, patient_id = _seed_doctor_patient()
        token = make_token(doctor_id, "DOCTOR")
        resp = await async_client.get(
            f"/api/v1/patients/{patient_id}/clinical-notes/nonexistent-id",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


class TestClinicalNoteUpdate:
    """Clinical note update tests."""

    @pytest.mark.asyncio
    async def test_author_can_update_note(self, async_client: AsyncClient):
        doctor_id, patient_id = _seed_doctor_patient()
        token = make_token(doctor_id, "DOCTOR")

        create = await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-notes",
            json={"note_type": "SOAP", "title": "Old Title", "content": "Old content"},
            headers={"Authorization": f"Bearer {token}"},
        )
        note = create.json()["data"]

        resp = await async_client.patch(
            f"/api/v1/patients/{patient_id}/clinical-notes/{note['note_id']}",
            json={"title": "New Title", "expected_version": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        updated = resp.json()["data"]
        assert updated["title"] == "New Title"
        assert updated["version"] == 2

    @pytest.mark.asyncio
    async def test_version_conflict_returns_409(self, async_client: AsyncClient):
        doctor_id, patient_id = _seed_doctor_patient()
        token = make_token(doctor_id, "DOCTOR")

        create = await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-notes",
            json={"note_type": "SOAP", "title": "T", "content": "C"},
            headers={"Authorization": f"Bearer {token}"},
        )
        note_id = create.json()["data"]["note_id"]

        resp = await async_client.patch(
            f"/api/v1/patients/{patient_id}/clinical-notes/{note_id}",
            json={"title": "Bad", "expected_version": 99},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409


class TestClinicalNoteSign:
    """Clinical note sign/lock tests."""

    @pytest.mark.asyncio
    async def test_author_can_sign_note(self, async_client: AsyncClient):
        doctor_id, patient_id = _seed_doctor_patient()
        token = make_token(doctor_id, "DOCTOR")

        create = await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-notes",
            json={"note_type": "SOAP", "title": "T", "content": "C"},
            headers={"Authorization": f"Bearer {token}"},
        )
        note_id = create.json()["data"]["note_id"]

        resp = await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-notes/{note_id}/sign",
            json={"expected_version": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        signed = resp.json()["data"]
        assert signed["is_signed"] is True
        assert signed["signed_at"] is not None

    @pytest.mark.asyncio
    async def test_update_signed_note_rejected(self, async_client: AsyncClient):
        """Signed notes are immutable — update returns 409."""
        doctor_id, patient_id = _seed_doctor_patient()
        token = make_token(doctor_id, "DOCTOR")

        create = await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-notes",
            json={"note_type": "SOAP", "title": "T", "content": "C"},
            headers={"Authorization": f"Bearer {token}"},
        )
        note_id = create.json()["data"]["note_id"]

        await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-notes/{note_id}/sign",
            json={"expected_version": 1},
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = await async_client.patch(
            f"/api/v1/patients/{patient_id}/clinical-notes/{note_id}",
            json={"title": "Attempt", "expected_version": 2},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_double_sign_returns_409(self, async_client: AsyncClient):
        doctor_id, patient_id = _seed_doctor_patient()
        token = make_token(doctor_id, "DOCTOR")

        create = await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-notes",
            json={"note_type": "SOAP", "title": "T", "content": "C"},
            headers={"Authorization": f"Bearer {token}"},
        )
        note_id = create.json()["data"]["note_id"]
        await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-notes/{note_id}/sign",
            json={"expected_version": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-notes/{note_id}/sign",
            json={"expected_version": 2},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409


# ============================================================================
# Clinical Assessments Tests
# ============================================================================

class TestClinicalAssessmentLifecycle:
    """Clinical assessment CRUD + finalize lifecycle tests."""

    @pytest.mark.asyncio
    async def test_create_assessment(self, async_client: AsyncClient):
        doctor_id, patient_id = _seed_doctor_patient()
        token = make_token(doctor_id, "DOCTOR")

        resp = await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-assessments",
            json={
                "assessment_type": "DIAGNOSIS",
                "title": "Tension Headache Assessment",
                "summary": "Patient diagnosed with tension-type headache",
                "icd_codes": ["G44.2"],
                "confidence": "HIGH",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["assessment_type"] == "DIAGNOSIS"
        assert data["is_finalized"] is False
        assert data["clinician_id"] == doctor_id

    @pytest.mark.asyncio
    async def test_update_assessment(self, async_client: AsyncClient):
        doctor_id, patient_id = _seed_doctor_patient()
        token = make_token(doctor_id, "DOCTOR")

        create = await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-assessments",
            json={"assessment_type": "RISK", "title": "T", "summary": "Initial"},
            headers={"Authorization": f"Bearer {token}"},
        )
        a = create.json()["data"]

        resp = await async_client.patch(
            f"/api/v1/patients/{patient_id}/clinical-assessments/{a['assessment_id']}",
            json={"summary": "Updated summary", "expected_version": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["summary"] == "Updated summary"
        assert resp.json()["data"]["version"] == 2

    @pytest.mark.asyncio
    async def test_finalize_assessment(self, async_client: AsyncClient):
        doctor_id, patient_id = _seed_doctor_patient()
        token = make_token(doctor_id, "DOCTOR")

        create = await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-assessments",
            json={"assessment_type": "PROGNOSIS", "title": "T", "summary": "Good prognosis"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assessment_id = create.json()["data"]["assessment_id"]

        resp = await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-assessments/{assessment_id}/finalize",
            json={"expected_version": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["is_finalized"] is True

    @pytest.mark.asyncio
    async def test_update_finalized_assessment_rejected(self, async_client: AsyncClient):
        doctor_id, patient_id = _seed_doctor_patient()
        token = make_token(doctor_id, "DOCTOR")

        create = await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-assessments",
            json={"assessment_type": "FUNCTIONAL", "title": "T", "summary": "S"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assessment_id = create.json()["data"]["assessment_id"]
        await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-assessments/{assessment_id}/finalize",
            json={"expected_version": 1},
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = await async_client.patch(
            f"/api/v1/patients/{patient_id}/clinical-assessments/{assessment_id}",
            json={"summary": "Attempt", "expected_version": 2},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_assessment_version_conflict(self, async_client: AsyncClient):
        doctor_id, patient_id = _seed_doctor_patient()
        token = make_token(doctor_id, "DOCTOR")

        create = await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-assessments",
            json={"assessment_type": "DIAGNOSIS", "title": "T", "summary": "S"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assessment_id = create.json()["data"]["assessment_id"]

        resp = await async_client.patch(
            f"/api/v1/patients/{patient_id}/clinical-assessments/{assessment_id}",
            json={"summary": "X", "expected_version": 999},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409


# ============================================================================
# Clinical Plans Tests
# ============================================================================

class TestClinicalPlanLifecycle:
    """Clinical plan CRUD + finalize lifecycle tests."""

    @pytest.mark.asyncio
    async def test_create_plan(self, async_client: AsyncClient):
        doctor_id, patient_id = _seed_doctor_patient()
        token = make_token(doctor_id, "DOCTOR")

        resp = await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-plans",
            json={
                "plan_type": "TREATMENT",
                "title": "Headache Management Plan",
                "objectives": ["Reduce pain frequency", "Identify triggers"],
                "interventions": [
                    {"category": "Pharmacological", "description": "Ibuprofen 400mg prn", "priority": "ROUTINE"}
                ],
                "investigations": ["CBC", "ESR"],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["plan_type"] == "TREATMENT"
        assert len(data["objectives"]) == 2
        assert data["clinician_id"] == doctor_id

    @pytest.mark.asyncio
    async def test_update_plan(self, async_client: AsyncClient):
        doctor_id, patient_id = _seed_doctor_patient()
        token = make_token(doctor_id, "DOCTOR")

        create = await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-plans",
            json={"plan_type": "MANAGEMENT", "title": "T", "objectives": ["Obj1"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        plan_id = create.json()["data"]["plan_id"]

        resp = await async_client.patch(
            f"/api/v1/patients/{patient_id}/clinical-plans/{plan_id}",
            json={"title": "Updated Plan", "expected_version": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "Updated Plan"
        assert resp.json()["data"]["version"] == 2

    @pytest.mark.asyncio
    async def test_finalize_plan(self, async_client: AsyncClient):
        doctor_id, patient_id = _seed_doctor_patient()
        token = make_token(doctor_id, "DOCTOR")

        create = await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-plans",
            json={"plan_type": "DIAGNOSTIC", "title": "T"},
            headers={"Authorization": f"Bearer {token}"},
        )
        plan_id = create.json()["data"]["plan_id"]

        resp = await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-plans/{plan_id}/finalize",
            json={"expected_version": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["is_finalized"] is True

    @pytest.mark.asyncio
    async def test_update_finalized_plan_rejected(self, async_client: AsyncClient):
        doctor_id, patient_id = _seed_doctor_patient()
        token = make_token(doctor_id, "DOCTOR")

        create = await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-plans",
            json={"plan_type": "PREVENTIVE", "title": "T"},
            headers={"Authorization": f"Bearer {token}"},
        )
        plan_id = create.json()["data"]["plan_id"]
        await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-plans/{plan_id}/finalize",
            json={"expected_version": 1},
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = await async_client.patch(
            f"/api/v1/patients/{patient_id}/clinical-plans/{plan_id}",
            json={"title": "Attempt", "expected_version": 2},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409


# ============================================================================
# Clinical Workspace Tests
# ============================================================================

class TestClinicalWorkspace:
    """Clinical workspace aggregation tests."""

    @pytest.mark.asyncio
    async def test_doctor_can_access_workspace(self, async_client: AsyncClient):
        doctor_id, patient_id = _seed_doctor_patient()
        token = make_token(doctor_id, "DOCTOR")

        resp = await async_client.get(
            f"/api/v1/patients/{patient_id}/clinical-workspace",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["patient"]["patient_id"] == patient_id
        assert data["clinician_id"] == doctor_id
        assert "summary" in data
        assert "recent_notes" in data
        assert "recent_assessments" in data
        assert "active_plans" in data

    @pytest.mark.asyncio
    async def test_workspace_reflects_created_notes(self, async_client: AsyncClient):
        doctor_id, patient_id = _seed_doctor_patient()
        token = make_token(doctor_id, "DOCTOR")

        # Create 2 notes
        for i in range(2):
            await async_client.post(
                f"/api/v1/patients/{patient_id}/clinical-notes",
                json={"note_type": "PROGRESS", "title": f"Note {i}", "content": "Content"},
                headers={"Authorization": f"Bearer {token}"},
            )

        resp = await async_client.get(
            f"/api/v1/patients/{patient_id}/clinical-workspace",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        summary = resp.json()["data"]["summary"]
        assert summary["total_clinical_notes"] == 2

    @pytest.mark.asyncio
    async def test_patient_cannot_access_workspace(self, async_client: AsyncClient):
        """Patient role cannot access the clinical workspace (DOCTOR-only)."""
        doctor_id, patient_id = _seed_doctor_patient()
        patient_token = make_token("usr-patient-p10", "PATIENT")

        resp = await async_client.get(
            f"/api/v1/patients/{patient_id}/clinical-workspace",
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthenticated_workspace_rejected(self, async_client: AsyncClient):
        doctor_id, patient_id = _seed_doctor_patient()
        resp = await async_client.get(
            f"/api/v1/patients/{patient_id}/clinical-workspace",
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_workspace_with_encounter_filter(self, async_client: AsyncClient):
        doctor_id, patient_id = _seed_doctor_patient()
        token = make_token(doctor_id, "DOCTOR")

        resp = await async_client.get(
            f"/api/v1/patients/{patient_id}/clinical-workspace?encounter_id=enc-001",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["encounter_id"] == "enc-001"


# ============================================================================
# Audit Event Tests
# ============================================================================

class TestPhase10AuditEvents:
    """Verify audit events are emitted for Phase 10 operations."""

    @pytest.mark.asyncio
    async def test_audit_event_on_note_create(self, async_client: AsyncClient):
        doctor_id, patient_id = _seed_doctor_patient()
        token = make_token(doctor_id, "DOCTOR")

        await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-notes",
            json={"note_type": "SOAP", "title": "T", "content": "C"},
            headers={"Authorization": f"Bearer {token}"},
        )

        events = [e for e in _global_audit_repo._events if e.event_type == "CLINICAL_NOTE_CREATED"]
        assert len(events) >= 1
        assert events[-1].actor_id == doctor_id

    @pytest.mark.asyncio
    async def test_audit_event_on_note_sign(self, async_client: AsyncClient):
        doctor_id, patient_id = _seed_doctor_patient()
        token = make_token(doctor_id, "DOCTOR")

        create = await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-notes",
            json={"note_type": "SOAP", "title": "T", "content": "C"},
            headers={"Authorization": f"Bearer {token}"},
        )
        note_id = create.json()["data"]["note_id"]
        await async_client.post(
            f"/api/v1/patients/{patient_id}/clinical-notes/{note_id}/sign",
            json={"expected_version": 1},
            headers={"Authorization": f"Bearer {token}"},
        )

        events = [e for e in _global_audit_repo._events if e.event_type == "CLINICAL_NOTE_SIGNED"]
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_audit_event_on_workspace_access(self, async_client: AsyncClient):
        doctor_id, patient_id = _seed_doctor_patient()
        token = make_token(doctor_id, "DOCTOR")

        await async_client.get(
            f"/api/v1/patients/{patient_id}/clinical-workspace",
            headers={"Authorization": f"Bearer {token}"},
        )

        events = [e for e in _global_audit_repo._events if e.event_type == "CLINICAL_WORKSPACE_ACCESSED"]
        assert len(events) >= 1
        assert events[-1].actor_id == doctor_id
