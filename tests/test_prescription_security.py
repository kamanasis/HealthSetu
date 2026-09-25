"""Phase 6 security tests: RBAC isolation, consent gating, anti-enumeration, and audit PHI hygiene."""

from datetime import datetime, timezone
import pytest
from httpx import AsyncClient

from app.api.deps import _global_audit_repo, _global_authz_service, _global_consent_repo
from app.repositories.consent_repository import ConsentRecord, ConsentStatus
from app.repositories.patient_repository import PatientRecord


@pytest.fixture
def doctor_consent(seeded_patients):
    """Seed active consent and relationship for doctor on pat-001."""
    now = datetime.now(timezone.utc)
    c1 = ConsentRecord(
        id="cst-sec-presc-001",
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
    c2 = ConsentRecord(
        id="cst-sec-med-001",
        patient_id="usr-patient-001",
        grantee_id="usr-doctor-001",
        purpose="care_delivery",
        scope="medications",
        status=ConsentStatus.ACTIVE,
        granted_at=now,
        effective_from=now,
        expires_at=None,
        version=1,
    )
    _global_consent_repo._consents[c1.id] = c1
    _global_consent_repo._consents[c2.id] = c2
    _global_authz_service.add_relationship("usr-doctor-001", "usr-patient-001")
    return c1


async def test_patient_cannot_create_prescription_returns_403(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Patient role cannot create prescriptions (clinical boundary enforcement)."""
    token = make_token("usr-patient-001", "PATIENT")
    payload = {
        "items": [{"drug_name_raw": "Amoxicillin", "strength_raw": "500 mg"}]
    }
    response = await async_client.post(
        "/api/v1/patients/pat-001/prescriptions",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_doctor_without_consent_cannot_access_prescriptions(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Doctor without active consent receives 403 when trying to access prescriptions."""
    token = make_token("usr-doctor-001", "DOCTOR")
    response = await async_client.get(
        "/api/v1/patients/pat-001/prescriptions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_admin_cannot_access_prescriptions_or_medications(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Admin role has zero clinical access and receives 403 on prescriptions and medications."""
    token = make_token("usr-admin-001", "ADMIN")
    presc_res = await async_client.get(
        "/api/v1/patients/pat-001/prescriptions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert presc_res.status_code == 403

    med_res = await async_client.get(
        "/api/v1/patients/pat-001/medications",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert med_res.status_code == 403


async def test_cross_patient_access_returns_404_preventing_enumeration(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    make_token,
):
    """Patient 1 requesting Patient 2's prescriptions or medications receives generic 404."""
    token = make_token("usr-patient-001", "PATIENT")
    presc_res = await async_client.get(
        "/api/v1/patients/pat-002/prescriptions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert presc_res.status_code == 404

    med_res = await async_client.get(
        "/api/v1/patients/pat-002/medications",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert med_res.status_code == 404


async def test_audit_log_hygiene_no_medication_or_phi_leak(
    async_client: AsyncClient,
    seeded_patients: dict[str, PatientRecord],
    doctor_consent,
    make_token,
):
    """Audit events record non-clinical identifiers and exclude prescription texts and PHI."""
    token = make_token("usr-doctor-001", "DOCTOR")
    payload = {
        "prescriber_reference": "Dr. Confidential",
        "items": [{"drug_name_raw": "SecretExperimentalDrug", "strength_raw": "100 mg"}],
    }
    await async_client.post(
        "/api/v1/patients/pat-001/prescriptions",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    # Inspect all audit events recorded in repository
    events = _global_audit_repo._events
    for ev in events:
        # Check event string representation
        ev_str = str(ev.model_dump())
        assert "SecretExperimentalDrug" not in ev_str
        assert "Dr. Confidential" not in ev_str
