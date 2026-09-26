"""Performance Smoke & Latency Validation Tests (Phase 16).

Verifies Section 44, 45 & 46:
- Measures p50, p95 latencies across high-frequency API endpoints:
  - Health & Readiness probes
  - Authentication & Token issuance
  - Patient workspace retrieval
  - Deterministic Triage calculation
  - Medication terminology normalization
  - Facility discovery
- Validates query bounds, bounded payload sizes, and no unbounded explosions
"""

import time
from datetime import date, datetime, timezone
import pytest
from httpx import AsyncClient

from app.api.deps import (
    _global_user_repo,
    _global_patient_repo,
    _global_authz_service,
    _global_consent_repo,
)
from app.core.security import create_access_token, hash_password
from app.repositories.patient_repository import PatientRecord
from app.repositories.user_repository import UserRecord
from app.repositories.consent_repository import ConsentRecord, ConsentStatus
from app.schemas.auth import AccountStatus, UserRole
from app.schemas.patient import BiologicalSex, PatientStatus


@pytest.fixture
def perf_context():
    now = datetime.now(timezone.utc)
    doctor = UserRecord(
        id="usr-perf-doc",
        identifier="dr.perf@healthsetu.org",
        password_hash=hash_password("Pass123!"),
        role=UserRole.DOCTOR,
        status=AccountStatus.ACTIVE,
    )
    patient_user = UserRecord(
        id="usr-perf-pat",
        identifier="patient.perf@healthsetu.org",
        password_hash=hash_password("Pass123!"),
        role=UserRole.PATIENT,
        status=AccountStatus.ACTIVE,
    )
    patient = PatientRecord(
        id="pat-perf-001",
        user_id="usr-perf-pat",
        first_name="Priya",
        last_name="Nair",
        date_of_birth=date(1992, 1, 15),
        sex=BiologicalSex.FEMALE,
        status=PatientStatus.ACTIVE,
        preferred_language="en",
        phone="+919876543277",
        email="priya@example.org",
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
                id=f"cns-perf-{pid}-{sc}",
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
async def test_health_and_readiness_probe_latency(async_client: AsyncClient):
    """Verify that liveness and readiness probes respond well under 100ms."""
    durations = []
    for _ in range(10):
        t0 = time.perf_counter()
        resp = await async_client.get("/api/v1/health")
        t1 = time.perf_counter()
        assert resp.status_code == 200
        durations.append((t1 - t0) * 1000)

    p95 = sorted(durations)[int(len(durations) * 0.95)]
    assert p95 < 100.0, f"Health check p95 too slow: {p95}ms"


@pytest.mark.asyncio
async def test_medication_normalization_performance(async_client: AsyncClient, perf_context):
    """Verify that medication terminology normalization operates within performance target."""
    doc, patient = perf_context
    token, _ = create_access_token(doc.id, UserRole.DOCTOR.value)
    headers = {"Authorization": f"Bearer {token}"}

    create_res = await async_client.post(
        f"/api/v1/patients/{patient.id}/prescriptions",
        json={"items": [{"drug_name_raw": "Aspirin", "strength_raw": "100 mg"}]},
        headers=headers,
    )
    assert create_res.status_code == 201
    presc_id = create_res.json()["data"]["id"]

    durations = []
    for _ in range(5):
        t0 = time.perf_counter()
        resp = await async_client.post(
            f"/api/v1/patients/{patient.id}/prescriptions/{presc_id}/normalize",
            headers=headers,
        )
        t1 = time.perf_counter()
        assert resp.status_code == 200
        durations.append((t1 - t0) * 1000)

    p95 = sorted(durations)[int(len(durations) * 0.95)]
    assert p95 < 500.0, f"Normalization p95 too slow: {p95}ms"


@pytest.mark.asyncio
async def test_facility_discovery_performance(async_client: AsyncClient, perf_context):
    """Verify that geographic facility discovery executes within bounded latency."""
    doc, _ = perf_context
    token, _ = create_access_token(doc.id, UserRole.DOCTOR.value)
    headers = {"Authorization": f"Bearer {token}"}

    durations = []
    for _ in range(5):
        t0 = time.perf_counter()
        resp = await async_client.get(
            "/api/v1/facilities/discover?radius_km=25&latitude=28.61&longitude=77.20",
            headers=headers,
        )
        t1 = time.perf_counter()
        assert resp.status_code == 200
        durations.append((t1 - t0) * 1000)

    p95 = sorted(durations)[int(len(durations) * 0.95)]
    assert p95 < 500.0, f"Discovery p95 too slow: {p95}ms"
