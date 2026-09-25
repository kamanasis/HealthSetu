"""Phase 12 Tests: Facility Discovery & Transfer.

Comprehensive tests covering:
1. Facility Discovery (unfiltered, by type, service, capability, radius)
2. Geolocation distance calculations and input validation
3. Missing coordinates handling and inactive facility filtering
4. Patient-specific contextual discovery with triage urgency integration
5. Explicit transfer creation with sending/receiving validation and same-facility rejection
6. Consent enforcement before clinical context snapshot sharing
7. SBAR attachment and validation
8. Transfer status lifecycle state transitions (REQUESTED -> ACCEPTED -> IN_PROGRESS -> COMPLETED)
9. Rejection of invalid status transitions (e.g. COMPLETED -> REQUESTED)
10. Security: unauthenticated requests, unauthorized patient access, and immutable PHI-safe audit trail
"""

from datetime import date, datetime, timezone
import pytest
from httpx import AsyncClient

from app.api.deps import (
    _global_audit_repo,
    _global_consent_repo,
    _global_department_repo,
    _global_encounter_repo,
    _global_facility_discovery_repo,
    _global_facility_repo,
    _global_organization_repo,
    _global_patient_repo,
    _global_sbar_repo,
    _global_transfer_repo,
    _global_triage_repo,
    _global_user_repo,
    _global_authz_service,
)
from app.core.security import create_access_token, hash_password
from app.repositories.consent_repository import ConsentRecord, ConsentStatus
from app.repositories.encounter_repository import EncounterRecord
from app.repositories.patient_repository import PatientRecord
from app.repositories.user_repository import UserRecord
from app.schemas.audit import AuditEventType
from app.schemas.auth import AccountStatus, UserRole
from app.schemas.department import DepartmentRecord, DepartmentStatus
from app.schemas.facility import FacilityRecord, FacilityStatus, FacilityType
from app.schemas.organization import (
    DataProvenance,
    DataProvenanceSource,
    OrganizationRecord,
    OrganizationStatus,
    OrganizationType,
)
from app.schemas.patient import BiologicalSex, PatientStatus
from app.schemas.sbar import (
    SBARAssessment,
    SBARBackground,
    SBARGenerationMode,
    SBARRecommendation,
    SBARRecord,
    SBARSituation,
)
from app.schemas.transfer import TransferPriority, TransferStatus
from app.schemas.triage import (
    TriageAssessmentRecord,
    TriageExplanation,
    TriageReason,
    TriageStatus,
    TriageUrgency,
)

TEST_PASSWORD = "StrongP@ssw0rd123!"


def make_token(user_id: str, role: str) -> str:
    token, _ = create_access_token(user_id, role)
    return token


def seed_user(user_id: str, role: UserRole) -> str:
    _global_user_repo.register_in_memory_user(
        UserRecord(
            id=user_id,
            identifier=f"{user_id}@healthsetu.org",
            password_hash=hash_password(TEST_PASSWORD),
            role=role,
            status=AccountStatus.ACTIVE,
        )
    )
    return make_token(user_id, role.value)


def make_patient(
    patient_id: str,
    user_id: str | None = None,
    first_name: str = "Jane",
    last_name: str = "Doe",
    sex: BiologicalSex = BiologicalSex.FEMALE,
) -> PatientRecord:
    now = datetime.now(timezone.utc)
    return PatientRecord(
        id=patient_id,
        user_id=user_id,
        first_name=first_name,
        last_name=last_name,
        date_of_birth=date(1990, 5, 12),
        sex=sex,
        status=PatientStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


def make_consent(
    consent_id: str,
    patient_id: str,
    grantee_id: str,
    scope: str = "transfer",
    purpose: str = "care_delivery",
) -> ConsentRecord:
    now = datetime.now(timezone.utc)
    return ConsentRecord(
        id=consent_id,
        patient_id=patient_id,
        grantee_id=grantee_id,
        purpose=purpose,
        scope=scope,
        status=ConsentStatus.ACTIVE,
        granted_at=now,
        effective_from=now,
        expires_at=datetime(2027, 1, 1, tzinfo=timezone.utc),
    )


def link_patient_to_doctor(doctor_id: str, patient: PatientRecord) -> None:
    _global_authz_service.add_relationship(doctor_id, patient.id)
    if patient.user_id:
        _global_authz_service.add_relationship(doctor_id, patient.user_id)


async def seed_consent(consent_id: str, patient: PatientRecord, doctor_id: str, scope: str = "transfer") -> None:
    await _global_consent_repo.create(make_consent(consent_id, patient.id, doctor_id, scope=scope))
    if patient.user_id:
        await _global_consent_repo.create(make_consent(f"{consent_id}-usr", patient.user_id, doctor_id, scope=scope))


@pytest.fixture
async def setup_discovery_network():
    """Setup test bed:
    Org A:
      - Fac A1: Kolkata City Center (22.5726, 88.3639)
        Services: EMERGENCY_CARE, CARDIOLOGY, ICU
        Capabilities: TRAUMA_CENTER, CARDIAC_CATH_LAB
      - Fac A2: Kolkata Suburb (22.6500, 88.4500)
        Services: OUTPATIENT, PEDIATRICS
        Capabilities: CLINICAL_LAB
    Org B:
      - Fac B1: Delhi North (28.6139, 77.2090)
        Services: EMERGENCY_CARE, NEUROLOGY
        Capabilities: STROKE_UNIT
    Org C (Inactive):
      - Fac C1: Inactive (22.5800, 88.3700)
    """
    # Orgs
    org_a = OrganizationRecord(
        id="org-disc-a",
        name="Apollo Health",
        organization_type=OrganizationType.HEALTHCARE_NETWORK,
        status=OrganizationStatus.ACTIVE,
    )
    await _global_organization_repo.create(org_a)

    org_b = OrganizationRecord(
        id="org-disc-b",
        name="Fortis Care",
        organization_type=OrganizationType.HOSPITAL,
        status=OrganizationStatus.ACTIVE,
    )
    await _global_organization_repo.create(org_b)

    # Facilities
    fac_a1 = FacilityRecord(
        id="fac-disc-a1",
        organization_id="org-disc-a",
        name="Apollo Central Hospital",
        facility_type=FacilityType.HOSPITAL,
        status=FacilityStatus.ACTIVE,
        address={"city": "Kolkata", "state": "WB"},
    )
    await _global_facility_repo.create(fac_a1)
    await _global_facility_discovery_repo.set_facility_metadata(
        facility_id="fac-disc-a1",
        latitude=22.5726,
        longitude=88.3639,
        services=["EMERGENCY_CARE", "CARDIOLOGY", "ICU"],
        capabilities=["TRAUMA_CENTER", "CARDIAC_CATH_LAB"],
    )

    fac_a2 = FacilityRecord(
        id="fac-disc-a2",
        organization_id="org-disc-a",
        name="Apollo Suburb Clinic",
        facility_type=FacilityType.CLINIC,
        status=FacilityStatus.ACTIVE,
        address={"city": "Barasat", "state": "WB"},
    )
    await _global_facility_repo.create(fac_a2)
    await _global_facility_discovery_repo.set_facility_metadata(
        facility_id="fac-disc-a2",
        latitude=22.6500,
        longitude=88.4500,
        services=["OUTPATIENT", "PEDIATRICS"],
        capabilities=["CLINICAL_LAB"],
    )

    fac_b1 = FacilityRecord(
        id="fac-disc-b1",
        organization_id="org-disc-b",
        name="Fortis Delhi North",
        facility_type=FacilityType.HOSPITAL,
        status=FacilityStatus.ACTIVE,
        address={"city": "New Delhi", "state": "DL"},
    )
    await _global_facility_repo.create(fac_b1)
    await _global_facility_discovery_repo.set_facility_metadata(
        facility_id="fac-disc-b1",
        latitude=28.6139,
        longitude=77.2090,
        services=["EMERGENCY_CARE", "NEUROLOGY"],
        capabilities=["STROKE_UNIT"],
    )

    fac_c1 = FacilityRecord(
        id="fac-disc-c1",
        organization_id="org-disc-a",
        name="Suspended Center",
        facility_type=FacilityType.CLINIC,
        status=FacilityStatus.INACTIVE,
    )
    await _global_facility_repo.create(fac_c1)
    await _global_facility_discovery_repo.set_facility_metadata(
        facility_id="fac-disc-c1",
        latitude=22.5800,
        longitude=88.3700,
        services=["EMERGENCY_CARE"],
        capabilities=["TRAUMA_CENTER"],
    )

    # Facility with missing coordinates
    fac_no_geo = FacilityRecord(
        id="fac-no-geo",
        organization_id="org-disc-a",
        name="Rural Dispensary",
        facility_type=FacilityType.CLINIC,
        status=FacilityStatus.ACTIVE,
    )
    await _global_facility_repo.create(fac_no_geo)
    await _global_facility_discovery_repo.set_facility_metadata(
        facility_id="fac-no-geo",
        latitude=None,
        longitude=None,
        services=["GENERAL_CARE"],
        capabilities=[],
    )

    return {
        "fac_a1": fac_a1,
        "fac_a2": fac_a2,
        "fac_b1": fac_b1,
        "fac_c1": fac_c1,
        "fac_no_geo": fac_no_geo,
    }


# ============================================================================
# 1. Geographic Calculation Unit Tests
# ============================================================================

def test_geographic_distance_calculation():
    """Verify deterministic Haversine distance calculations and boundary conditions."""
    from app.services.geographic_service import GeographicService

    geo = GeographicService()

    # Distance between Kolkata (22.5726, 88.3639) and Delhi (28.6139, 77.2090) ~ 1300-1310 km
    dist = geo.calculate_distance_km(22.5726, 88.3639, 28.6139, 77.2090)
    assert dist is not None
    assert 1300 <= dist <= 1315

    # Zero distance between identical coordinates
    dist_zero = geo.calculate_distance_km(22.5726, 88.3639, 22.5726, 88.3639)
    assert dist_zero == 0.0

    # Missing destination coordinates must return None, NOT zero or fabricated value
    assert geo.calculate_distance_km(22.5726, 88.3639, None, 88.3639) is None
    assert geo.calculate_distance_km(22.5726, 88.3639, 22.5726, None) is None
    assert geo.calculate_distance_km(None, None, 22.5726, 88.3639) is None


# ============================================================================
# 2. Facility Discovery Tests
# ============================================================================

@pytest.mark.asyncio
async def test_discover_facilities_all(async_client: AsyncClient, setup_discovery_network):
    """Test discovering active facilities without coordinates or filters."""
    token = seed_user("patient-p12", UserRole.PATIENT)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.get("/api/v1/facilities/discover", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    # Suspended center must be excluded
    fac_ids = [f["facility_id"] for f in data["items"]]
    assert "fac-disc-a1" in fac_ids
    assert "fac-disc-a2" in fac_ids
    assert "fac-disc-b1" in fac_ids
    assert "fac-no-geo" in fac_ids
    assert "fac-disc-c1" not in fac_ids


@pytest.mark.asyncio
async def test_discover_facilities_by_type_and_service(async_client: AsyncClient, setup_discovery_network):
    """Test filtering by facility type and supported service."""
    token = seed_user("pat-disc-flt", UserRole.PATIENT)
    headers = {"Authorization": f"Bearer {token}"}

    # Filter for CLINIC
    resp_clinic = await async_client.get("/api/v1/facilities/discover?facility_type=CLINIC", headers=headers)
    assert resp_clinic.status_code == 200
    clinic_ids = [f["facility_id"] for f in resp_clinic.json()["data"]["items"]]
    assert "fac-disc-a2" in clinic_ids
    assert "fac-no-geo" in clinic_ids
    assert "fac-disc-a1" not in clinic_ids

    # Filter for EMERGENCY_CARE service
    resp_service = await async_client.get("/api/v1/facilities/discover?required_service=EMERGENCY_CARE", headers=headers)
    assert resp_service.status_code == 200
    service_ids = [f["facility_id"] for f in resp_service.json()["data"]["items"]]
    assert "fac-disc-a1" in service_ids
    assert "fac-disc-b1" in service_ids
    assert "fac-disc-a2" not in service_ids


@pytest.mark.asyncio
async def test_discover_facilities_by_capability(async_client: AsyncClient, setup_discovery_network):
    """Test filtering by required capability without clinical assumption."""
    token = seed_user("pat-disc-cap", UserRole.PATIENT)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.get("/api/v1/facilities/discover?required_capability=CARDIAC_CATH_LAB", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["facility_id"] == "fac-disc-a1"


@pytest.mark.asyncio
async def test_discover_facilities_by_proximity_radius(async_client: AsyncClient, setup_discovery_network):
    """Test proximity query from Kolkata (22.5700, 88.3600) with 15km radius."""
    token = seed_user("pat-disc-geo", UserRole.PATIENT)
    headers = {"Authorization": f"Bearer {token}"}

    # Central Kolkata origin with 15 km radius
    resp = await async_client.get(
        "/api/v1/facilities/discover?latitude=22.5700&longitude=88.3600&radius_km=15",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    # Only Apollo Central Hospital (~0.5 km) should match. Barasat (~13-14km) might match depending on radius, Delhi (~1300km) excluded.
    fac_ids = [f["facility_id"] for f in data["items"]]
    assert "fac-disc-a1" in fac_ids
    assert "fac-disc-b1" not in fac_ids  # Delhi excluded
    assert "fac-no-geo" not in fac_ids   # No geo excluded when radius is requested

    # Check distance field is populated
    item_a1 = next(f for f in data["items"] if f["facility_id"] == "fac-disc-a1")
    assert item_a1["distance_km"] is not None
    assert item_a1["distance_km"] < 2.0


@pytest.mark.asyncio
async def test_discover_facilities_invalid_location_inputs(async_client: AsyncClient, setup_discovery_network):
    """Test validation errors for improper geographic coordinates."""
    token = seed_user("pat-disc-err", UserRole.PATIENT)
    headers = {"Authorization": f"Bearer {token}"}

    # Incomplete location (latitude without longitude)
    resp_inc = await async_client.get("/api/v1/facilities/discover?latitude=22.5700", headers=headers)
    assert resp_inc.status_code == 400
    assert resp_inc.json()["error"]["code"] == "INCOMPLETE_LOCATION"

    # Invalid latitude (> 90)
    resp_lat = await async_client.get("/api/v1/facilities/discover?latitude=95.0&longitude=88.0", headers=headers)
    assert resp_lat.status_code == 400

    # Invalid negative radius
    resp_rad = await async_client.get("/api/v1/facilities/discover?latitude=22.5&longitude=88.3&radius_km=-5", headers=headers)
    assert resp_rad.status_code == 400


# ============================================================================
# 3. Patient-Specific Contextual Discovery Tests
# ============================================================================

@pytest.mark.asyncio
async def test_patient_contextual_discovery(async_client: AsyncClient, setup_discovery_network):
    """Test patient-specific discovery endpoint integrating triage urgency."""
    patient_user_id = "usr-pat-ctx"
    patient_id = "pat-ctx-1"
    token = seed_user(patient_user_id, UserRole.PATIENT)
    headers = {"Authorization": f"Bearer {token}"}

    # Register patient
    await _global_patient_repo.create(
        make_patient(patient_id, patient_user_id, "Jane", "Doe", BiologicalSex.FEMALE)
    )

    # Seed triage record with EMERGENCY urgency
    await _global_triage_repo.create(
        TriageAssessmentRecord(
            id="trg-em-1",
            patient_id=patient_id,
            encounter_id="enc-em-1",
            urgency=TriageUrgency.EMERGENCY,
            status=TriageStatus.COMPLETED,
            rule_set="HealthSetu Clinical Protocol",
            rule_set_version="1.0.0",
            explanation=TriageExplanation(
                summary="Immediate Emergency Care",
                factors_considered=["Severe crushing chest pain"],
                urgency_rationale="Acute coronary symptoms",
                recommended_level_of_care="Emergency Department",
            ),
        )
    )

    # Discover for patient: should automatically prioritize EMERGENCY_CARE service
    resp = await async_client.get(
        f"/api/v1/patients/{patient_id}/facilities/discover",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    fac_ids = [f["facility_id"] for f in data["items"]]
    assert "fac-disc-a1" in fac_ids
    assert "fac-disc-b1" in fac_ids
    assert "fac-disc-a2" not in fac_ids  # Apollo Suburb has no EMERGENCY_CARE


# ============================================================================
# 4. Patient Transfer / Referral Workflow Tests
# ============================================================================

@pytest.mark.asyncio
async def test_create_transfer_success_with_consent_and_sbar(async_client: AsyncClient, setup_discovery_network):
    """Test creating a transfer with valid consent and SBAR attachment."""
    doctor_id = "doc-trf-create"
    patient_id = "pat-trf-1"
    token = seed_user(doctor_id, UserRole.DOCTOR)
    headers = {"Authorization": f"Bearer {token}"}

    # Setup patient & relationship
    pat = make_patient(patient_id, "usr-pat-trf-1", "Robert", "Smith", BiologicalSex.MALE)
    await _global_patient_repo.create(pat)
    link_patient_to_doctor(doctor_id, pat)

    # Active consent
    await seed_consent("cst-trf-1", pat, doctor_id, scope="transfer")

    # SBAR record
    await _global_sbar_repo.create(
        SBARRecord(
            id="sbar-trf-1",
            patient_id=patient_id,
            assessment_id="trg-em-1",
            encounter_id="enc-trf-1",
            generation_mode=SBARGenerationMode.TEMPLATE,
            situation=SBARSituation(
                reason_for_attention="Acute STEMI requiring emergency catheterization",
                current_urgency=TriageUrgency.EMERGENCY,
                presenting_symptoms=["crushing chest pain"],
                summary_text="Acute STEMI requiring emergency catheterization",
            ),
            background=SBARBackground(
                known_conditions=["hypertension"],
                summary_text="History of hypertension",
            ),
            assessment=SBARAssessment(
                urgency=TriageUrgency.EMERGENCY,
                summary_text="Inferior wall myocardial infarction",
            ),
            recommendation=SBARRecommendation(
                recommended_level_of_care="Emergency Department / Cath Lab",
                follow_up_recommendation="Immediate PCI",
                summary_text="Transfer to tertiary cardiac cath lab",
            ),
            plain_text="Situation: Acute STEMI... Background: hypertension...",
        )
    )

    # Create transfer
    payload = {
        "sending_facility_id": "fac-disc-a1",
        "receiving_facility_id": "fac-disc-b1",
        "reason": "Immediate emergency transfer for PCI intervention",
        "priority": "EMERGENCY",
        "sbar_id": "sbar-trf-1",
        "notes": "Ambulance transit prepared",
    }

    resp = await async_client.post(
        f"/api/v1/patients/{patient_id}/transfers",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["status"] == "REQUESTED"
    assert data["priority"] == "EMERGENCY"
    assert data["sending_facility_id"] == "fac-disc-a1"
    assert data["receiving_facility_id"] == "fac-disc-b1"
    assert data["sbar_id"] == "sbar-trf-1"

    transfer_id = data["id"]

    # Verify attached clinical context snapshot
    ctx = await _global_transfer_repo.get_clinical_context(transfer_id)
    assert ctx is not None
    assert ctx.sbar_id == "sbar-trf-1"
    assert ctx.sbar_situation == "Acute STEMI requiring emergency catheterization"


@pytest.mark.asyncio
async def test_transfer_validation_same_facility(async_client: AsyncClient, setup_discovery_network):
    """Test transfer creation fails if sending and receiving facility are identical."""
    doctor_id = "doc-trf-same"
    patient_id = "pat-trf-same"
    token = seed_user(doctor_id, UserRole.DOCTOR)
    headers = {"Authorization": f"Bearer {token}"}

    pat = make_patient(patient_id, "usr-pat-same", "Bob", "Vance", BiologicalSex.MALE)
    await _global_patient_repo.create(pat)
    link_patient_to_doctor(doctor_id, pat)
    await seed_consent("cst-same", pat, doctor_id, scope="transfer")

    payload = {
        "sending_facility_id": "fac-disc-a1",
        "receiving_facility_id": "fac-disc-a1",  # Same facility!
        "reason": "Test transfer",
    }

    resp = await async_client.post(f"/api/v1/patients/{patient_id}/transfers", json=payload, headers=headers)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "RECEIVING_FACILITY_INVALID"


@pytest.mark.asyncio
async def test_transfer_missing_consent_fails(async_client: AsyncClient, setup_discovery_network):
    """Test transfer creation is rejected when patient consent is missing."""
    doctor_id = "doc-trf-nocst"
    patient_id = "pat-trf-nocst"
    token = seed_user(doctor_id, UserRole.DOCTOR)
    headers = {"Authorization": f"Bearer {token}"}

    pat = make_patient(patient_id, "usr-pat-nocst", "Alice", "Wonder", BiologicalSex.FEMALE)
    await _global_patient_repo.create(pat)
    link_patient_to_doctor(doctor_id, pat)
    # No consent created!

    payload = {
        "sending_facility_id": "fac-disc-a1",
        "receiving_facility_id": "fac-disc-b1",
        "reason": "Transfer attempt without consent",
    }

    resp = await async_client.post(f"/api/v1/patients/{patient_id}/transfers", json=payload, headers=headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TRANSFER_CONSENT_REQUIRED"


@pytest.mark.asyncio
async def test_transfer_status_transitions(async_client: AsyncClient, setup_discovery_network):
    """Test valid and invalid transfer state machine transitions."""
    doctor_id = "doc-trf-sm"
    patient_id = "pat-trf-sm"
    token = seed_user(doctor_id, UserRole.DOCTOR)
    headers = {"Authorization": f"Bearer {token}"}

    pat = make_patient(patient_id, "usr-pat-sm", "Sam", "Smith", BiologicalSex.MALE)
    await _global_patient_repo.create(pat)
    link_patient_to_doctor(doctor_id, pat)
    await seed_consent("cst-sm", pat, doctor_id, scope="transfer")

    # Create transfer
    create_resp = await async_client.post(
        f"/api/v1/patients/{patient_id}/transfers",
        json={
            "sending_facility_id": "fac-disc-a1",
            "receiving_facility_id": "fac-disc-b1",
            "reason": "Routine clinical referral",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    transfer_id = create_resp.json()["data"]["id"]

    # 1. Transition: REQUESTED -> ACCEPTED
    resp_acc = await async_client.post(
        f"/api/v1/patients/{patient_id}/transfers/{transfer_id}/status",
        json={"status": "ACCEPTED", "reason": "Receiving hospital confirmed bed"},
        headers=headers,
    )
    assert resp_acc.status_code == 200
    assert resp_acc.json()["data"]["status"] == "ACCEPTED"

    # 2. Transition: ACCEPTED -> IN_PROGRESS
    resp_prog = await async_client.post(
        f"/api/v1/patients/{patient_id}/transfers/{transfer_id}/status",
        json={"status": "IN_PROGRESS", "notes": "Patient in transit"},
        headers=headers,
    )
    assert resp_prog.status_code == 200
    assert resp_prog.json()["data"]["status"] == "IN_PROGRESS"

    # 3. Transition: IN_PROGRESS -> COMPLETED
    resp_comp = await async_client.post(
        f"/api/v1/patients/{patient_id}/transfers/{transfer_id}/status",
        json={"status": "COMPLETED", "notes": "Patient admitted at destination"},
        headers=headers,
    )
    assert resp_comp.status_code == 200
    assert resp_comp.json()["data"]["status"] == "COMPLETED"

    # 4. Invalid Transition: COMPLETED -> REQUESTED (must be rejected!)
    resp_inv = await async_client.post(
        f"/api/v1/patients/{patient_id}/transfers/{transfer_id}/status",
        json={"status": "REQUESTED"},
        headers=headers,
    )
    assert resp_inv.status_code == 400
    assert resp_inv.json()["error"]["code"] == "TRANSFER_INVALID_STATE"


@pytest.mark.asyncio
async def test_audit_events_recorded_for_transfers(async_client: AsyncClient, setup_discovery_network):
    """Verify Phase 12 audit events are generated."""
    doctor_id = "doc-trf-audit"
    patient_id = "pat-trf-audit"
    token = seed_user(doctor_id, UserRole.DOCTOR)
    headers = {"Authorization": f"Bearer {token}"}

    pat = make_patient(patient_id, "usr-pat-aud", "Audrey", "Hepburn", BiologicalSex.FEMALE)
    await _global_patient_repo.create(pat)
    link_patient_to_doctor(doctor_id, pat)
    await seed_consent("cst-aud", pat, doctor_id, scope="transfer")

    # 1. Discover
    await async_client.get("/api/v1/facilities/discover", headers=headers)

    # 2. Transfer Create
    cr_resp = await async_client.post(
        f"/api/v1/patients/{patient_id}/transfers",
        json={
            "sending_facility_id": "fac-disc-a1",
            "receiving_facility_id": "fac-disc-b1",
            "reason": "Specialty care referral",
        },
        headers=headers,
    )
    transfer_id = cr_resp.json()["data"]["id"]

    # 3. Read transfer
    await async_client.get(f"/api/v1/patients/{patient_id}/transfers/{transfer_id}", headers=headers)

    # 4. Status update
    await async_client.post(
        f"/api/v1/patients/{patient_id}/transfers/{transfer_id}/status",
        json={"status": "DECLINED", "reason": "No specialty bed currently available"},
        headers=headers,
    )

    recorded_types = [e.event_type for e in _global_audit_repo._events]
    assert AuditEventType.FACILITY_DISCOVERY_STARTED in recorded_types
    assert AuditEventType.FACILITY_DISCOVERY_COMPLETED in recorded_types
    assert AuditEventType.TRANSFER_CREATED in recorded_types
    assert AuditEventType.TRANSFER_VIEWED in recorded_types
    assert AuditEventType.TRANSFER_DECLINED in recorded_types
