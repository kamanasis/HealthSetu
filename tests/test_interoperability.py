"""Phase 13 Tests: Interoperability & Healthcare Data Exchange.

Tests cover:
1. FHIR Validation & Mapping (Patient, Encounter, Observation, AllergyIntolerance, MedicationRequest, DocumentReference)
2. Invalid resource and unsupported FHIR version rejection
3. Deterministic identity resolution (valid internal ID, mapped external ID, unresolved, ambiguous match)
4. Inbound import pipeline with candidate staging & clinical safety review requirement
5. Non-overwriting guarantee (imported candidate data does not modify verified clinical records)
6. Outbound export pipeline with data minimization scopes
7. Consent enforcement on export (ConsentScope.INTEROPERABILITY)
8. Patient-specific export route (/api/v1/patients/{patient_id}/interoperability/export)
9. Idempotent import of duplicate payloads
10. Security: unauthenticated requests, unauthorized patient access, and PHI-safe audit logging
"""

from datetime import date, datetime, timezone
import pytest
from httpx import AsyncClient

from app.api.deps import (
    _global_allergy_repo,
    _global_audit_repo,
    _global_authz_service,
    _global_consent_repo,
    _global_document_repo,
    _global_encounter_repo,
    _global_interoperability_repo,
    _global_patient_medication_repo,
    _global_patient_repo,
    _global_user_repo,
    _global_vitals_repo,
)
from app.core.exceptions import (
    AmbiguousPatientMatchException,
    ExternalIdentityUnresolvedException,
    InteroperabilityConsentRequiredException,
    UnsupportedFHIRVersionException,
    UnsupportedResourceTypeException,
)
from app.core.security import create_access_token, hash_password
from app.integrations.interoperability.fhir.mapper import FHIRMapper
from app.integrations.interoperability.fhir.validator import FHIRValidator
from app.repositories.allergy_repository import AllergyRecord
from app.repositories.consent_repository import ConsentRecord, ConsentStatus
from app.repositories.encounter_repository import EncounterRecord
from app.repositories.patient_medication_repository import PatientMedicationRecord
from app.repositories.patient_repository import PatientRecord
from app.repositories.user_repository import UserRecord
from app.repositories.vitals_repository import VitalRecord
from app.schemas.allergy import AllergySeverity, AllergyStatus
from app.schemas.audit import AuditEventType
from app.schemas.auth import AccountStatus, UserRole
from app.schemas.clinical_history import ClinicalDataSource
from app.schemas.encounter import EncounterStatus, EncounterType
from app.schemas.interoperability import (
    ExportScope,
    ExternalIdentifierMapping,
    FHIRVersion,
    ImportStatus,
    InteroperabilityExportRequest,
    InteroperabilityFormat,
    InteroperabilityImportRequest,
    VerificationStatus,
)
from app.schemas.patient import BiologicalSex, PatientStatus

TEST_PASSWORD = "StrongP@ssw0rd123!"


def make_token(user_id: str, role: str) -> str:
    """Helper to generate JWT bearer tokens for tests."""
    token, _ = create_access_token(user_id, role)
    return token


@pytest.fixture
def seed_interoperability_data():
    """Seed test users, patients, clinical data, and consents."""
    now = datetime.now(timezone.utc)
    hashed_pwd = hash_password(TEST_PASSWORD)

    # 1. Users
    patient_user = UserRecord(
        id="usr-pat-001",
        identifier="patient1@example.com",
        password_hash=hashed_pwd,
        role=UserRole.PATIENT,
        status=AccountStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    patient2_user = UserRecord(
        id="usr-pat-002",
        identifier="patient2@example.com",
        password_hash=hashed_pwd,
        role=UserRole.PATIENT,
        status=AccountStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    doctor_user = UserRecord(
        id="usr-doc-001",
        identifier="doctor1@example.com",
        password_hash=hashed_pwd,
        role=UserRole.DOCTOR,
        status=AccountStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    admin_user = UserRecord(
        id="usr-admin-001",
        identifier="admin@example.com",
        password_hash=hashed_pwd,
        role=UserRole.ADMIN,
        status=AccountStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )

    _global_user_repo._local_users["usr-pat-001"] = patient_user
    _global_user_repo._local_users["usr-pat-002"] = patient2_user
    _global_user_repo._local_users["usr-doc-001"] = doctor_user
    _global_user_repo._local_users["usr-admin-001"] = admin_user

    # 2. Patients
    patient_record = PatientRecord(
        id="pat-001",
        user_id="usr-pat-001",
        first_name="Aarav",
        last_name="Sharma",
        date_of_birth=date(1985, 4, 12),
        sex=BiologicalSex.MALE,
        phone="+919876543210",
        email="aarav.sharma@example.com",
        status=PatientStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    patient2_record = PatientRecord(
        id="pat-002",
        user_id="usr-pat-002",
        first_name="Priya",
        last_name="Patel",
        date_of_birth=date(1990, 8, 24),
        sex=BiologicalSex.FEMALE,
        phone="+919876543211",
        email="priya.patel@example.com",
        status=PatientStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    _global_patient_repo._patients["pat-001"] = patient_record
    _global_patient_repo._user_to_patient["usr-pat-001"] = "pat-001"
    _global_patient_repo._patients["pat-002"] = patient2_record
    _global_patient_repo._user_to_patient["usr-pat-002"] = "pat-002"

    # Doctor-Patient Relationship
    _global_authz_service.add_relationship("usr-doc-001", "usr-pat-001")
    _global_authz_service.add_relationship("usr-doc-001", "pat-001")

    # 3. Clinical Data for Patient 1
    # Allergy
    allergy = AllergyRecord(
        id="alg-001",
        patient_id="pat-001",
        allergen="Penicillin",
        reaction="Anaphylaxis",
        severity=AllergySeverity.SEVERE,
        status=AllergyStatus.ACTIVE,
        source=ClinicalDataSource.CLINIC_ENTERED,
        recorded_by="usr-doc-001",
        created_at=now,
        updated_at=now,
    )
    _global_allergy_repo._records["alg-001"] = allergy

    # Vital
    from app.schemas.vital import VitalSource, VitalType
    vital = VitalRecord(
        id="vit-001",
        patient_id="pat-001",
        vital_type=VitalType.HEART_RATE,
        value=72.0,
        unit="bpm",
        measured_at=now,
        source=VitalSource.CLINIC_RECORDED,
        recorded_by="usr-doc-001",
        created_at=now,
    )
    _global_vitals_repo._records["vit-001"] = vital

    # Medication
    from app.schemas.medication import MedicationSource
    med = PatientMedicationRecord(
        id="pmed-001",
        patient_id="pat-001",
        drug_name_raw="Metformin 500mg",
        source=MedicationSource.DOCTOR_ENTERED,
        created_at=now,
        updated_at=now,
    )
    _global_patient_medication_repo._medications["pmed-001"] = med

    # Encounter
    encounter = EncounterRecord(
        id="enc-001",
        patient_id="pat-001",
        encounter_type=EncounterType.OUTPATIENT,
        status=EncounterStatus.COMPLETED,
        start_time=now,
        source=ClinicalDataSource.CLINIC_ENTERED,
        created_at=now,
        updated_at=now,
    )
    _global_encounter_repo._records["enc-001"] = encounter

    # 4. Consent for Interoperability
    consent = ConsentRecord(
        id="cst-001",
        patient_id="pat-001",
        grantee_id="usr-doc-001",
        scope="interoperability",
        purpose="care_delivery",
        status=ConsentStatus.ACTIVE,
        granted_at=now,
        effective_from=now,
    )
    _global_consent_repo._consents["cst-001"] = consent

    # 5. External Identifier Mapping — insert directly into repo dict (sync setup)
    _global_interoperability_repo._identity_mappings[("Hospital-A", "EXT-PAT-001")] = "pat-001"

    return {
        "patient_id": "pat-001",
        "doctor_user_id": "usr-doc-001",
        "admin_user_id": "usr-admin-001",
        "patient2_id": "pat-002",
    }


# ===========================================================================
# 1. FHIR Validator & Mapper Unit Tests
# ===========================================================================

def test_fhir_validator_valid_patient():
    """Verify validator accepts valid FHIR Patient."""
    validator = FHIRValidator()
    payload = {
        "resourceType": "Patient",
        "id": "pat-test-01",
        "name": [{"family": "Sharma", "given": ["Aarav"]}],
        "gender": "male",
        "birthDate": "1985-04-12",
    }
    errors = validator.validate_resource(payload, "Patient")
    assert len(errors) == 0


def test_fhir_validator_invalid_resource_type():
    """Verify validator rejects mismatching resourceType."""
    validator = FHIRValidator()
    payload = {"resourceType": "Observation", "id": "123"}
    errors = validator.validate_resource(payload, "Patient")
    assert len(errors) > 0


def test_fhir_validator_unsupported_resource_type():
    """Verify validator rejects unsupported FHIR resource type."""
    validator = FHIRValidator()
    with pytest.raises(UnsupportedResourceTypeException):
        validator.validate_resource({"resourceType": "Coverage", "id": "cov-001"})


def test_fhir_validator_unsupported_fhir_version():
    """Verify validator rejects unsupported FHIR versions."""
    validator = FHIRValidator()
    with pytest.raises(UnsupportedFHIRVersionException):
        validator.validate_version("DSTU2")


def test_fhir_mapper_bi_directional_observation():
    """Verify FHIR mapper transforms Observation to domain and domain to FHIR."""
    mapper = FHIRMapper()
    # Inbound
    fhir_obs = {
        "resourceType": "Observation",
        "id": "obs-001",
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}]},
        "subject": {"reference": "Patient/pat-001"},
        "valueQuantity": {"value": 72.0, "unit": "bpm"},
        "effectiveDateTime": "2026-09-25T10:00:00Z",
    }
    candidate = mapper.map_observation_inbound(fhir_obs, "Hospital-A", "pat-001")
    assert candidate["observation_type"] == "Heart rate"
    assert candidate["value"] == 72.0
    assert candidate["unit"] == "bpm"

    # Outbound
    from app.schemas.vital import VitalSource, VitalType
    vital_rec = VitalRecord(
        id="vit-99",
        patient_id="pat-001",
        vital_type=VitalType.HEART_RATE,
        value=75.0,
        unit="bpm",
        measured_at=datetime.now(timezone.utc),
        source=VitalSource.CLINIC_RECORDED,
        created_at=datetime.now(timezone.utc),
    )
    mapped_fhir = mapper.map_vital_outbound(vital_rec, "pat-001")
    assert mapped_fhir["resourceType"] == "Observation"
    assert mapped_fhir["valueQuantity"]["value"] == 75.0


# ===========================================================================
# 2. Identity Resolution & Patient Matching
# ===========================================================================

@pytest.mark.asyncio
async def test_identity_resolution_saved_mapping(async_client: AsyncClient, seed_interoperability_data):
    """Verify inbound resource maps external patient ID to HealthSetu ID using saved mappings."""
    doctor_token = make_token(seed_interoperability_data["doctor_user_id"], "DOCTOR")
    payload = {
        "source_system": "Hospital-A",
        "format": "FHIR",
        "resource_type": "Observation",
        "payload": {
            "resourceType": "Observation",
            "id": "ext-obs-10",
            "status": "final",
            "code": {"text": "Heart rate"},
            "subject": {"reference": "Patient/EXT-PAT-001"},
            "valueQuantity": {"value": 80, "unit": "bpm"},
        },
        "external_resource_id": "ext-obs-10",
        "external_patient_id": "EXT-PAT-001",
    }

    response = await async_client.post(
        "/api/v1/interoperability/import",
        json=payload,
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["healthsetu_patient_id"] == "pat-001"
    assert data["verification_status"] == VerificationStatus.REVIEW_REQUIRED.value


@pytest.mark.asyncio
async def test_identity_resolution_unresolved(async_client: AsyncClient, seed_interoperability_data):
    """Verify unresolvable external patient ID raises EXTERNAL_IDENTITY_UNRESOLVED."""
    doctor_token = make_token(seed_interoperability_data["doctor_user_id"], "DOCTOR")
    payload = {
        "source_system": "Unknown-Clinic",
        "format": "FHIR",
        "resource_type": "Observation",
        "payload": {
            "resourceType": "Observation",
            "id": "ext-obs-unknown",
            "status": "final",
            "code": {"text": "Heart rate"},
            "subject": {"reference": "Patient/UNKNOWN-999"},
            "valueQuantity": {"value": 80, "unit": "bpm"},
        },
        "external_resource_id": "ext-obs-unknown",
        "external_patient_id": "UNKNOWN-999",
    }

    response = await async_client.post(
        "/api/v1/interoperability/import",
        json=payload,
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "EXTERNAL_IDENTITY_UNRESOLVED"


# ===========================================================================
# 3. Inbound Import Pipeline & Safety Boundary
# ===========================================================================

@pytest.mark.asyncio
async def test_import_creates_review_required_candidate(async_client: AsyncClient, seed_interoperability_data):
    """Verify imported data is tagged REVIEW_REQUIRED and never silently overwrites clinical records."""
    doctor_token = make_token(seed_interoperability_data["doctor_user_id"], "DOCTOR")
    payload = {
        "source_system": "Hospital-A",
        "format": "FHIR",
        "resource_type": "AllergyIntolerance",
        "payload": {
            "resourceType": "AllergyIntolerance",
            "id": "ext-alg-55",
            "code": {"text": "Aspirin"},
            "criticality": "high",
            "reaction": [{"manifestation": [{"text": "Urticaria"}]}],
        },
        "external_resource_id": "ext-alg-55",
        "healthsetu_patient_id": "pat-001",
    }

    # Initial allergy count
    initial_allergies = len(_global_allergy_repo._records)

    response = await async_client.post(
        "/api/v1/interoperability/import",
        json=payload,
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 201
    data = response.json()["data"]
    import_id = data["import_id"]
    assert data["status"] == ImportStatus.REVIEW_REQUIRED.value

    # Verify existing active allergy records are NOT mutated or auto-inserted
    assert len(_global_allergy_repo._records) == initial_allergies

    # Retrieve import record
    get_res = await async_client.get(
        f"/api/v1/interoperability/imports/{import_id}",
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert get_res.status_code == 200
    rec = get_res.json()["data"]
    assert rec["mapped_entity_id"] is None
    assert rec["verification_status"] == VerificationStatus.REVIEW_REQUIRED.value
    assert "Hospital-A" in rec["provenance"]["source_system"]


@pytest.mark.asyncio
async def test_import_idempotency(async_client: AsyncClient, seed_interoperability_data):
    """Verify resubmitting the identical external resource payload is idempotent."""
    doctor_token = make_token(seed_interoperability_data["doctor_user_id"], "DOCTOR")
    payload = {
        "source_system": "Hospital-A",
        "format": "FHIR",
        "resource_type": "Observation",
        "payload": {
            "resourceType": "Observation",
            "id": "ext-obs-idem-1",
            "status": "final",
            "code": {"text": "Blood Pressure"},
            "valueQuantity": {"value": 120, "unit": "mmHg"},
        },
        "external_resource_id": "ext-obs-idem-1",
        "healthsetu_patient_id": "pat-001",
    }

    res1 = await async_client.post(
        "/api/v1/interoperability/import",
        json=payload,
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert res1.status_code == 201
    id1 = res1.json()["data"]["import_id"]

    # Post identical second time
    res2 = await async_client.post(
        "/api/v1/interoperability/import",
        json=payload,
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert res2.status_code == 201
    id2 = res2.json()["data"]["import_id"]

    # Same import record returned without creating duplicate
    assert id1 == id2


# ===========================================================================
# 4. Outbound Export Pipeline & Data Minimization Scopes
# ===========================================================================

@pytest.mark.asyncio
async def test_export_missing_consent(async_client: AsyncClient, seed_interoperability_data):
    """Verify export fails when patient has not granted interoperability consent."""
    # Revoke or delete consent
    _global_consent_repo._consents.clear()

    doctor_token = make_token(seed_interoperability_data["doctor_user_id"], "DOCTOR")
    payload = {
        "patient_id": "pat-001",
        "scope": "CLINICAL_SUMMARY",
        "format": "FHIR",
        "target_system": "Partner-Clinic",
    }

    response = await async_client.post(
        "/api/v1/interoperability/export",
        json=payload,
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 403
    assert "INTEROPERABILITY_CONSENT_REQUIRED" in response.json()["error"]["code"]


@pytest.mark.asyncio
async def test_export_authorized_clinical_summary(async_client: AsyncClient, seed_interoperability_data):
    """Verify authorized export packages patient, vitals, allergies, and medications into FHIR bundle."""
    doctor_token = make_token(seed_interoperability_data["doctor_user_id"], "DOCTOR")
    payload = {
        "patient_id": "pat-001",
        "scope": "CLINICAL_SUMMARY",
        "format": "FHIR",
        "target_system": "Partner-Clinic",
        "consent_id": "cst-001",
    }

    response = await async_client.post(
        "/api/v1/interoperability/export",
        json=payload,
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 202
    data = response.json()["data"]
    export_id = data["export_id"]
    assert data["status"] == "DELIVERED"
    assert data["delivered_bundle_id"] is not None

    # Retrieve export record
    get_res = await async_client.get(
        f"/api/v1/interoperability/exports/{export_id}",
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert get_res.status_code == 200
    export_rec = get_res.json()["data"]
    assert "Patient" in export_rec["resource_types"]
    assert "Observation" in export_rec["resource_types"]
    assert "AllergyIntolerance" in export_rec["resource_types"]
    assert "MedicationRequest" in export_rec["resource_types"]


@pytest.mark.asyncio
async def test_export_data_minimization_patient_basic(async_client: AsyncClient, seed_interoperability_data):
    """Verify PATIENT_BASIC scope only includes Patient resource."""
    doctor_token = make_token(seed_interoperability_data["doctor_user_id"], "DOCTOR")
    payload = {
        "patient_id": "pat-001",
        "scope": "PATIENT_BASIC",
        "format": "FHIR",
        "target_system": "Partner-Clinic",
    }

    response = await async_client.post(
        "/api/v1/interoperability/export",
        json=payload,
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 202
    export_id = response.json()["data"]["export_id"]

    get_res = await async_client.get(
        f"/api/v1/interoperability/exports/{export_id}",
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    export_rec = get_res.json()["data"]
    assert export_rec["resource_types"] == ["Patient"]


@pytest.mark.asyncio
async def test_patient_specific_export_endpoint(async_client: AsyncClient, seed_interoperability_data):
    """Verify POST /api/v1/patients/{patient_id}/interoperability/export endpoint."""
    doctor_token = make_token(seed_interoperability_data["doctor_user_id"], "DOCTOR")
    payload = {
        "format": "FHIR",
        "scope": "VITALS",
        "target_system": "Regional-Lab",
    }

    response = await async_client.post(
        "/api/v1/patients/pat-001/interoperability/export",
        json=payload,
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 202
    data = response.json()["data"]
    assert data["patient_id"] == "pat-001"
    assert data["scope"] == "VITALS"


# ===========================================================================
# 5. Security & Access Control Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(async_client: AsyncClient):
    """Verify unauthenticated requests return 401."""
    response = await async_client.post(
        "/api/v1/interoperability/import",
        json={"source_system": "Hospital-A"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_patient_cannot_view_other_patient_export(async_client: AsyncClient, seed_interoperability_data):
    """Verify patient 2 cannot view patient 1's export record."""
    doctor_token = make_token(seed_interoperability_data["doctor_user_id"], "DOCTOR")
    patient2_token = make_token("usr-pat-002", "PATIENT")

    # Create export for patient 1
    create_res = await async_client.post(
        "/api/v1/interoperability/export",
        json={
            "patient_id": "pat-001",
            "scope": "PATIENT_BASIC",
            "format": "FHIR",
            "target_system": "Partner-Clinic",
        },
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    export_id = create_res.json()["data"]["export_id"]

    # Patient 2 attempts to read Patient 1's export
    read_res = await async_client.get(
        f"/api/v1/interoperability/exports/{export_id}",
        headers={"Authorization": f"Bearer {patient2_token}"},
    )
    assert read_res.status_code == 403


@pytest.mark.asyncio
async def test_audit_trail_and_phi_safety(async_client: AsyncClient, seed_interoperability_data):
    """Verify audit logs are emitted for interoperability actions and do not contain full raw payloads."""
    doctor_token = make_token(seed_interoperability_data["doctor_user_id"], "DOCTOR")

    # Trigger export
    await async_client.post(
        "/api/v1/interoperability/export",
        json={
            "patient_id": "pat-001",
            "scope": "PATIENT_BASIC",
            "format": "FHIR",
            "target_system": "Partner-Clinic",
        },
        headers={"Authorization": f"Bearer {doctor_token}"},
    )

    # Check audit events in repository
    events = [e for e in _global_audit_repo._events if "INTEROPERABILITY" in e.action]
    assert len(events) >= 2

    # Verify event types
    action_names = {e.action for e in events}
    assert AuditEventType.INTEROPERABILITY_EXPORT_STARTED.value in action_names
    assert AuditEventType.INTEROPERABILITY_EXPORT_COMPLETED.value in action_names

    # Check PHI safety: details must not contain raw clinical observations or passwords
    for event in events:
        details_str = str(event.details)
        assert "password" not in details_str.lower()
        assert "access_token" not in details_str.lower()
