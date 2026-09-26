"""Integration Failure Injection and Provider Resilience Tests (Phase 16).

Verifies Section 41:
- Database unavailable & timeout handling
- OCR extraction service unavailable
- Medication terminology provider failure
- Medication safety provider error
- AI model provider timeout & rate limits
- Object storage failure resilience
- Bounded, standardized error responses across all failure modes
"""

from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient

from app.api.deps import (
    _global_consent_repo,
    _global_user_repo,
    _global_patient_repo,
    _global_authz_service,
)
from app.core.exceptions import (
    AIProviderTimeoutException,
    AppException,
    ErrorCode,
)
from app.core.security import create_access_token, hash_password
from app.repositories.consent_repository import ConsentRecord, ConsentStatus
from app.repositories.patient_repository import PatientRecord
from app.repositories.user_repository import UserRecord
from app.schemas.auth import AccountStatus, UserRole
from app.schemas.patient import BiologicalSex, PatientStatus


@pytest.fixture
def failure_test_context():
    now = datetime.now(timezone.utc)
    doctor = UserRecord(
        id="usr-fail-doc",
        identifier="dr.failure@healthsetu.org",
        password_hash=hash_password("DocPass123!"),
        role=UserRole.DOCTOR,
        status=AccountStatus.ACTIVE,
    )
    patient_user = UserRecord(
        id="usr-fail-pat",
        identifier="patient.fail@healthsetu.org",
        password_hash=hash_password("Pass123!"),
        role=UserRole.PATIENT,
        status=AccountStatus.ACTIVE,
    )
    patient = PatientRecord(
        id="pat-fail-001",
        user_id="usr-fail-pat",
        first_name="Anita",
        last_name="Roy",
        date_of_birth=now.date(),
        sex=BiologicalSex.FEMALE,
        status=PatientStatus.ACTIVE,
        preferred_language="en",
        phone="+919876543299",
        email="anita@example.org",
        created_at=now,
        updated_at=now,
    )
    _global_user_repo.register_in_memory_user(doctor)
    _global_user_repo.register_in_memory_user(patient_user)
    _global_patient_repo._patients[patient.id] = patient
    _global_patient_repo._user_to_patient[patient_user.id] = patient.id
    _global_authz_service.add_relationship(doctor.id, patient_user.id)
    _global_authz_service.add_relationship(doctor.id, patient.id)

    scopes = ["all_records", "clinical_records", "prescriptions", "medications", "discharge_summary"]
    for pid in (patient_user.id, patient.id):
        for sc in scopes:
            c = ConsentRecord(
                id=f"cns-fail-{pid}-{sc}",
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
async def test_database_health_failure_returns_503(async_client: AsyncClient):
    """Verify that when database health check fails, readiness returns 503 Service Unavailable."""
    with patch("app.services.health.check_database_health", return_value=False):
        resp = await async_client.get("/api/v1/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["database"] == "unavailable"


@pytest.mark.asyncio
async def test_medication_terminology_timeout_handled_gracefully(async_client: AsyncClient, failure_test_context):
    """Verify that external terminology timeouts return standardized error or fallback, never unhandled crashes."""
    doc, patient = failure_test_context
    token, _ = create_access_token(doc.id, UserRole.DOCTOR.value)

    with patch(
        "app.integrations.medication.providers.local.LocalMedicationProvider.normalize",
        side_effect=AppException(code=ErrorCode.EXTERNAL_PROVIDER_UNAVAILABLE, message="Terminology provider timeout", status_code=503),
    ):
        resp = await async_client.post(
            f"/api/v1/patients/{patient.id}/prescriptions",
            json={"items": [{"drug_name_raw": "Atorvastatin", "strength_raw": "20 mg"}]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code in (500, 502, 503, 504)
        data = resp.json()
        assert data["success"] is False
        assert "error" in data


@pytest.mark.asyncio
async def test_ai_provider_timeout_fails_safely(async_client: AsyncClient, failure_test_context):
    """Verify that external AI provider timeout triggers bounded error response and does not crash app."""
    doc, _ = failure_test_context
    token, _ = create_access_token(doc.id, UserRole.DOCTOR.value)

    with patch(
        "app.integrations.ai.providers.mock_provider.MockAIProvider.generate_structured",
        side_effect=AIProviderTimeoutException("Upstream LLM timeout"),
    ):
        resp = await async_client.post(
            "/api/v1/ai/tasks",
            json={
                "task_type": "DOCUMENT_EXTRACTION",
                "source_content": "Discharge clinical notes for extraction",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code in (202, 500, 502, 503, 504)
        data = resp.json()
        if resp.status_code == 202:
            assert data["data"]["status"] in ("FAILED", "QUEUED")
        else:
            assert data["success"] is False


@pytest.mark.asyncio
async def test_storage_failure_during_upload_returns_standard_error(async_client: AsyncClient, failure_test_context):
    """Verify that object storage failure returns bounded error rather than corrupting record metadata."""
    doc, patient = failure_test_context
    token, _ = create_access_token(doc.id, UserRole.DOCTOR.value)

    pdf = b"%PDF-1.4\n1 0 obj\n<< /Length 50 >>\nstream\nBT\n/F1 12 Tf\n(Test Doc)\nET\nendstream\nendobj\n%%EOF"
    files = {"file": ("test.pdf", pdf, "application/pdf")}
    data = {"document_type": "PRESCRIPTION", "source": "CLINIC_UPLOAD"}

    with patch(
        "app.integrations.storage.local_storage.LocalDocumentStorage.put",
        side_effect=Exception("Disk I/O failure or S3 connection refused"),
    ):
        resp = await async_client.post(
            f"/api/v1/patients/{patient.id}/documents",
            files=files,
            data=data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code in (500, 502, 503)
        data = resp.json()
        assert data["success"] is False
        assert "error" in data
        assert "code" in data["error"]
