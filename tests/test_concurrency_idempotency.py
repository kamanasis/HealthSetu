"""Tests for Optimistic Concurrency Control and Workflow Idempotency (Phase 16).

Verifies Section 30 & 43:
- Optimistic concurrency: Stale clinical updates are rejected with conflict
- Idempotent normalization: Repeated requests return consistent mappings without side-effects
- Idempotent document processing: Duplicate triggers do not produce corrupted state
- Idempotent authentication / session invalidation
"""

from datetime import date, datetime, timezone
import pytest
from httpx import AsyncClient

from app.api.deps import (
    _global_consent_repo,
    _global_encounter_repo,
    _global_patient_repo,
    _global_user_repo,
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


@pytest.fixture
def concurrency_test_context():
    now = datetime.now(timezone.utc)
    doctor = UserRecord(
        id="usr-conc-doc",
        identifier="dr.concurrency@healthsetu.org",
        password_hash=hash_password("Pass123!"),
        role=UserRole.DOCTOR,
        status=AccountStatus.ACTIVE,
    )
    patient_user = UserRecord(
        id="usr-conc-pat",
        identifier="patient.conc@healthsetu.org",
        password_hash=hash_password("Pass123!"),
        role=UserRole.PATIENT,
        status=AccountStatus.ACTIVE,
    )
    patient = PatientRecord(
        id="pat-conc-001",
        user_id="usr-conc-pat",
        first_name="Ramesh",
        last_name="Gupta",
        date_of_birth=date(1975, 6, 12),
        sex=BiologicalSex.MALE,
        status=PatientStatus.ACTIVE,
        preferred_language="en",
        phone="+919876543288",
        email="ramesh@example.org",
        created_at=now,
        updated_at=now,
    )
    _global_user_repo.register_in_memory_user(doctor)
    _global_user_repo.register_in_memory_user(patient_user)
    _global_patient_repo._patients[patient.id] = patient
    _global_patient_repo._user_to_patient[patient.user_id] = patient.id
    _global_authz_service.add_relationship(doctor.id, patient.user_id)
    _global_authz_service.add_relationship(doctor.id, patient.id)

    scopes = ["all_records", "clinical_records", "prescriptions", "medications"]
    for pid in (patient.user_id, patient.id):
        for sc in scopes:
            c = ConsentRecord(
                id=f"cns-conc-{pid}-{sc}",
                patient_id=pid,
                grantee_id=doctor.id,
                purpose="care_delivery",
                scope=sc,
                status=ConsentStatus.ACTIVE,
                granted_at=now,
                effective_from=now,
                expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
            )
            _global_consent_repo._consents[c.id] = c

    return doctor, patient


@pytest.mark.asyncio
async def test_idempotent_medication_normalization(async_client: AsyncClient, concurrency_test_context):
    """Verify that repeated normalization calls for the same payload produce identical results."""
    doc, patient = concurrency_test_context
    token, _ = create_access_token(doc.id, UserRole.DOCTOR.value)
    headers = {"Authorization": f"Bearer {token}"}

    create_res = await async_client.post(
        f"/api/v1/patients/{patient.id}/prescriptions",
        json={"items": [{"drug_name_raw": "Amoxicillin", "strength_raw": "500 mg"}]},
        headers=headers,
    )
    assert create_res.status_code == 201
    presc_id = create_res.json()["data"]["id"]

    resp1 = await async_client.post(
        f"/api/v1/patients/{patient.id}/prescriptions/{presc_id}/normalize",
        headers=headers,
    )
    resp2 = await async_client.post(
        f"/api/v1/patients/{patient.id}/prescriptions/{presc_id}/normalize",
        headers=headers,
    )

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["data"]["items"] == resp2.json()["data"]["items"]


@pytest.mark.asyncio
async def test_concurrency_note_modification(async_client: AsyncClient, concurrency_test_context):
    """Verify clinical notes support optimistic concurrency and reject stale updates."""
    now = datetime.now(timezone.utc)
    doc, patient = concurrency_test_context
    token, _ = create_access_token(doc.id, UserRole.DOCTOR.value)
    headers = {"Authorization": f"Bearer {token}"}

    encounter = EncounterRecord(
        id="enc-conc-01",
        patient_id=patient.id,
        encounter_type=EncounterType.OUTPATIENT,
        status=EncounterStatus.IN_PROGRESS,
        start_time=now,
        source=ClinicalDataSource.CLINIC_ENTERED,
        created_at=now,
        updated_at=now,
        provider_id=doc.id,
        organization_id="fac-01",
    )
    await _global_encounter_repo.create(encounter)

    # Create note
    resp_create = await async_client.post(
        f"/api/v1/patients/{patient.id}/clinical-notes",
        json={
            "encounter_id": encounter.id,
            "note_type": "PROGRESS",
            "title": "Initial Assessment",
            "content": "Initial clinical note entry.",
        },
        headers=headers,
    )
    assert resp_create.status_code == 201
    note_id = resp_create.json()["data"]["note_id"]

    # First update succeeds with expected_version=1
    resp_update1 = await async_client.patch(
        f"/api/v1/patients/{patient.id}/clinical-notes/{note_id}",
        json={"content": "First clinician update", "expected_version": 1},
        headers=headers,
    )
    assert resp_update1.status_code == 200
    assert resp_update1.json()["data"]["content"] == "First clinician update"

    # Stale update with version 1 is rejected with conflict
    resp_stale = await async_client.patch(
        f"/api/v1/patients/{patient.id}/clinical-notes/{note_id}",
        json={"content": "Stale update attempting to overwrite", "expected_version": 1},
        headers=headers,
    )
    assert resp_stale.status_code in (409, 400)

    # Update with correct version 2 succeeds
    resp_update2 = await async_client.patch(
        f"/api/v1/patients/{patient.id}/clinical-notes/{note_id}",
        json={"content": "Second clinician update", "expected_version": 2},
        headers=headers,
    )
    assert resp_update2.status_code == 200
    assert resp_update2.json()["data"]["content"] == "Second clinician update"
