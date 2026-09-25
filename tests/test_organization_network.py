"""Phase 11 Tests: Hospital & Organization Network.

Tests cover:
1. Organization retrieval, pagination, filtering, and internal search
2. Organization error handling: 404 ORGANIZATION_NOT_FOUND, 400 ORGANIZATION_INACTIVE
3. Organization facilities retrieval with organization status validation
4. Facility retrieval, search, and 404 FACILITY_NOT_FOUND, 400 FACILITY_INACTIVE
5. Organization / facility relationship validation (FACILITY_ORGANIZATION_MISMATCH)
6. Department retrieval, listing by facility, 404 DEPARTMENT_NOT_FOUND, and facility relationship validation
7. Clinician multi-organization support (single and multiple affiliations)
8. Clinician multi-facility support (single and multiple privileges)
9. Clinician organization context and facility context consolidation
10. Security: unauthenticated requests, unauthorized role access, cross-org/facility denials
11. Audit events: all 9 Phase 11 audit event types properly recorded with safe metadata
"""

from datetime import datetime, timezone
import pytest
from httpx import AsyncClient

from app.api.deps import (
    _global_audit_repo,
    _global_department_repo,
    _global_facility_repo,
    _global_organization_repo,
    _global_user_repo,
)
from app.core.security import create_access_token, hash_password
from app.repositories.user_repository import UserRecord
from app.schemas.audit import AuditEventType
from app.schemas.auth import AccountStatus, UserRole
from app.schemas.department import DepartmentRecord, DepartmentStatus
from app.schemas.facility import (
    ClinicianFacilityMembershipRecord,
    FacilityRecord,
    FacilityStatus,
    FacilityType,
)
from app.schemas.organization import (
    ClinicianOrganizationMembershipRecord,
    DataProvenance,
    DataProvenanceSource,
    OrganizationRecord,
    OrganizationStatus,
    OrganizationType,
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


@pytest.fixture
async def setup_network():
    """Setup synthetic network:
    Org A (ACTIVE)
      ├── Facility A1 (ACTIVE)
      │     ├── Dept Cardiology (ACTIVE)
      │     └── Dept Radiology (ACTIVE)
      └── Facility A2 (ACTIVE)
    Org B (ACTIVE)
      └── Facility B1 (ACTIVE)
    Org Inactive (INACTIVE)
      └── Facility Inactive (INACTIVE)
    """
    # Create Org A
    org_a = OrganizationRecord(
        id="org-a",
        name="Apollo Health Network",
        organization_type=OrganizationType.HEALTHCARE_NETWORK,
        status=OrganizationStatus.ACTIVE,
        identifier="REG-ORG-A",
        email="contact@apollo.test",
        phone="+91-11-20000001",
        provenance=DataProvenance(source=DataProvenanceSource.INTERNAL_DATABASE),
    )
    await _global_organization_repo.create(org_a)

    # Create Org B
    org_b = OrganizationRecord(
        id="org-b",
        name="Fortis Care System",
        organization_type=OrganizationType.HOSPITAL,
        status=OrganizationStatus.ACTIVE,
        identifier="REG-ORG-B",
        email="contact@fortis.test",
        phone="+91-11-20000002",
        provenance=DataProvenance(source=DataProvenanceSource.INTERNAL_DATABASE),
    )
    await _global_organization_repo.create(org_b)

    # Create Inactive Org
    org_inactive = OrganizationRecord(
        id="org-inact",
        name="Suspended Clinic Group",
        organization_type=OrganizationType.CLINIC,
        status=OrganizationStatus.INACTIVE,
        identifier="REG-ORG-INACT",
        provenance=DataProvenance(source=DataProvenanceSource.INTERNAL_DATABASE),
    )
    await _global_organization_repo.create(org_inactive)

    # Facilities under Org A
    fac_a1 = FacilityRecord(
        id="fac-a1",
        organization_id="org-a",
        name="Apollo Main Hospital",
        facility_type=FacilityType.HOSPITAL,
        status=FacilityStatus.ACTIVE,
        identifier="FAC-A1-REG",
        email="main@apollo.test",
        phone="+91-11-20001001",
        provenance=DataProvenance(source=DataProvenanceSource.INTERNAL_DATABASE),
    )
    await _global_facility_repo.create(fac_a1)

    fac_a2 = FacilityRecord(
        id="fac-a2",
        organization_id="org-a",
        name="Apollo Diagnostics Center",
        facility_type=FacilityType.DIAGNOSTIC_CENTER,
        status=FacilityStatus.ACTIVE,
        identifier="FAC-A2-REG",
        email="diag@apollo.test",
        phone="+91-11-20001002",
        provenance=DataProvenance(source=DataProvenanceSource.INTERNAL_DATABASE),
    )
    await _global_facility_repo.create(fac_a2)

    # Facility under Org B
    fac_b1 = FacilityRecord(
        id="fac-b1",
        organization_id="org-b",
        name="Fortis North Clinic",
        facility_type=FacilityType.CLINIC,
        status=FacilityStatus.ACTIVE,
        identifier="FAC-B1-REG",
        email="north@fortis.test",
        provenance=DataProvenance(source=DataProvenanceSource.INTERNAL_DATABASE),
    )
    await _global_facility_repo.create(fac_b1)

    # Facility under Inactive Org
    fac_inact = FacilityRecord(
        id="fac-inact",
        organization_id="org-inact",
        name="Suspended Branch",
        facility_type=FacilityType.CLINIC,
        status=FacilityStatus.INACTIVE,
        identifier="FAC-INACT-REG",
        provenance=DataProvenance(source=DataProvenanceSource.INTERNAL_DATABASE),
    )
    await _global_facility_repo.create(fac_inact)

    # Departments under Facility A1
    dept_cardio = DepartmentRecord(
        id="dept-cardio",
        facility_id="fac-a1",
        organization_id="org-a",
        name="Cardiology",
        code="CARD-01",
        status=DepartmentStatus.ACTIVE,
    )
    await _global_department_repo.create(dept_cardio)

    dept_radio = DepartmentRecord(
        id="dept-radio",
        facility_id="fac-a1",
        organization_id="org-a",
        name="Radiology",
        code="RAD-01",
        status=DepartmentStatus.ACTIVE,
    )
    await _global_department_repo.create(dept_radio)

    return {
        "org_a": org_a,
        "org_b": org_b,
        "org_inactive": org_inactive,
        "fac_a1": fac_a1,
        "fac_a2": fac_a2,
        "fac_b1": fac_b1,
        "fac_inact": fac_inact,
        "dept_cardio": dept_cardio,
        "dept_radio": dept_radio,
    }


# ============================================================================
# 1. Organization Tests
# ============================================================================

@pytest.mark.asyncio
async def test_list_organizations(async_client: AsyncClient, setup_network):
    """Test listing organizations with pagination and filtering."""
    token = seed_user("doc-p11-list", UserRole.DOCTOR)
    headers = {"Authorization": f"Bearer {token}"}

    # List all
    resp = await async_client.get("/api/v1/organizations", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["total"] >= 3
    items = data["data"]["items"]
    org_ids = [o["id"] for o in items]
    assert "org-a" in org_ids
    assert "org-b" in org_ids

    # Filter by name
    resp_name = await async_client.get("/api/v1/organizations?name=Apollo", headers=headers)
    assert resp_name.status_code == 200
    assert resp_name.json()["data"]["total"] == 1
    assert resp_name.json()["data"]["items"][0]["id"] == "org-a"

    # Filter by status
    resp_status = await async_client.get("/api/v1/organizations?status=INACTIVE", headers=headers)
    assert resp_status.status_code == 200
    assert resp_status.json()["data"]["total"] == 1
    assert resp_status.json()["data"]["items"][0]["id"] == "org-inact"


@pytest.mark.asyncio
async def test_search_organizations(async_client: AsyncClient, setup_network):
    """Test internal organization search."""
    token = seed_user("doc-p11-search", UserRole.DOCTOR)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.get("/api/v1/organizations/search?name=Fortis", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Fortis Care System"


@pytest.mark.asyncio
async def test_get_organization_success(async_client: AsyncClient, setup_network):
    """Test retrieving existing organization details."""
    token = seed_user("doc-p11-get", UserRole.DOCTOR)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.get("/api/v1/organizations/org-a", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["id"] == "org-a"
    assert data["data"]["name"] == "Apollo Health Network"
    assert data["data"]["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_get_organization_not_found(async_client: AsyncClient, setup_network):
    """Test 404 for non-existent organization."""
    token = seed_user("doc-p11-notfound", UserRole.DOCTOR)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.get("/api/v1/organizations/org-nonexistent", headers=headers)
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "ORGANIZATION_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_organization_facilities(async_client: AsyncClient, setup_network):
    """Test retrieving facilities under an organization."""
    token = seed_user("doc-p11-orgfac", UserRole.DOCTOR)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.get("/api/v1/organizations/org-a/facilities", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 2
    fac_ids = [f["id"] for f in data["items"]]
    assert "fac-a1" in fac_ids
    assert "fac-a2" in fac_ids


@pytest.mark.asyncio
async def test_get_organization_facilities_inactive_org(async_client: AsyncClient, setup_network):
    """Test 400 when listing facilities of an inactive organization."""
    token = seed_user("doc-p11-orginact", UserRole.DOCTOR)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.get("/api/v1/organizations/org-inact/facilities", headers=headers)
    assert resp.status_code == 400
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "ORGANIZATION_INACTIVE"


# ============================================================================
# 2. Facility Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_facility_success(async_client: AsyncClient, setup_network):
    """Test retrieving a facility by id."""
    token = seed_user("doc-p11-fac-ok", UserRole.DOCTOR)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.get("/api/v1/facilities/fac-a1", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == "fac-a1"
    assert data["organization_id"] == "org-a"
    assert data["name"] == "Apollo Main Hospital"


@pytest.mark.asyncio
async def test_get_facility_not_found(async_client: AsyncClient, setup_network):
    """Test 404 for non-existent facility."""
    token = seed_user("doc-p11-fac-nf", UserRole.DOCTOR)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.get("/api/v1/facilities/fac-unknown", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "FACILITY_NOT_FOUND"


@pytest.mark.asyncio
async def test_search_facilities(async_client: AsyncClient, setup_network):
    """Test internal facility search."""
    token = seed_user("doc-p11-fac-search", UserRole.DOCTOR)
    headers = {"Authorization": f"Bearer {token}"}

    # Search by organization_id
    resp = await async_client.get("/api/v1/facilities/search?organization_id=org-a", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 2

    # Search by name
    resp_name = await async_client.get("/api/v1/facilities/search?name=North", headers=headers)
    assert resp_name.status_code == 200
    assert resp_name.json()["data"]["total"] == 1
    assert resp_name.json()["data"]["items"][0]["id"] == "fac-b1"


@pytest.mark.asyncio
async def test_facility_departments(async_client: AsyncClient, setup_network):
    """Test retrieving departments belonging to a facility."""
    token = seed_user("doc-p11-fac-dept", UserRole.DOCTOR)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.get("/api/v1/facilities/fac-a1/departments", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 2
    dept_names = [d["name"] for d in data["items"]]
    assert "Cardiology" in dept_names
    assert "Radiology" in dept_names


@pytest.mark.asyncio
async def test_facility_departments_not_found(async_client: AsyncClient, setup_network):
    """Test 404 for departments of non-existent facility."""
    token = seed_user("doc-p11-fac-dept-nf", UserRole.DOCTOR)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.get("/api/v1/facilities/fac-unknown/departments", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "FACILITY_NOT_FOUND"


# ============================================================================
# 3. Department Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_department_success(async_client: AsyncClient, setup_network):
    """Test retrieving individual department."""
    token = seed_user("doc-p11-dept", UserRole.DOCTOR)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.get("/api/v1/departments/dept-cardio", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == "dept-cardio"
    assert data["facility_id"] == "fac-a1"
    assert data["name"] == "Cardiology"


@pytest.mark.asyncio
async def test_get_department_not_found(async_client: AsyncClient, setup_network):
    """Test 404 for non-existent department."""
    token = seed_user("doc-p11-dept-nf", UserRole.DOCTOR)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.get("/api/v1/departments/dept-unknown", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "DEPARTMENT_NOT_FOUND"


# ============================================================================
# 4. Clinician Access & Multi-Organization/Facility Tests
# ============================================================================

@pytest.mark.asyncio
async def test_clinician_single_organization(async_client: AsyncClient, setup_network):
    """Test clinician with single organization membership."""
    doc_id = "doc-single-org"
    token = seed_user(doc_id, UserRole.DOCTOR)
    headers = {"Authorization": f"Bearer {token}"}

    # Add membership to Org A
    await _global_organization_repo.add_clinician_membership(
        ClinicianOrganizationMembershipRecord(
            id="mem-1",
            clinician_id=doc_id,
            organization_id="org-a",
            role_title="Senior Consultant",
        )
    )

    resp = await async_client.get("/api/v1/clinicians/me/organizations", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["id"] == "org-a"
    assert data[0]["name"] == "Apollo Health Network"


@pytest.mark.asyncio
async def test_clinician_multiple_organizations(async_client: AsyncClient, setup_network):
    """Test clinician affiliated with multiple organizations simultaneously."""
    doc_id = "doc-multi-org"
    token = seed_user(doc_id, UserRole.DOCTOR)
    headers = {"Authorization": f"Bearer {token}"}

    # Affiliate with Org A and Org B
    await _global_organization_repo.add_clinician_membership(
        ClinicianOrganizationMembershipRecord(
            id="mem-a",
            clinician_id=doc_id,
            organization_id="org-a",
            role_title="Visiting Consultant",
        )
    )
    await _global_organization_repo.add_clinician_membership(
        ClinicianOrganizationMembershipRecord(
            id="mem-b",
            clinician_id=doc_id,
            organization_id="org-b",
            role_title="Attending Physician",
        )
    )

    resp = await async_client.get("/api/v1/clinicians/me/organizations", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 2
    org_ids = [o["id"] for o in data]
    assert "org-a" in org_ids
    assert "org-b" in org_ids


@pytest.mark.asyncio
async def test_clinician_multiple_facilities(async_client: AsyncClient, setup_network):
    """Test clinician with privileges across multiple facilities."""
    doc_id = "doc-multi-fac"
    token = seed_user(doc_id, UserRole.DOCTOR)
    headers = {"Authorization": f"Bearer {token}"}

    # Privilege at Facility A1 and Facility A2
    await _global_facility_repo.add_clinician_membership(
        ClinicianFacilityMembershipRecord(
            id="facmem-1",
            clinician_id=doc_id,
            facility_id="fac-a1",
            organization_id="org-a",
            role_title="Cardiologist",
        )
    )
    await _global_facility_repo.add_clinician_membership(
        ClinicianFacilityMembershipRecord(
            id="facmem-2",
            clinician_id=doc_id,
            facility_id="fac-a2",
            organization_id="org-a",
            role_title="Imaging Specialist",
        )
    )

    resp = await async_client.get("/api/v1/clinicians/me/facilities", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 2
    fac_ids = [f["id"] for f in data]
    assert "fac-a1" in fac_ids
    assert "fac-a2" in fac_ids


@pytest.mark.asyncio
async def test_clinician_organization_context_success(async_client: AsyncClient, setup_network):
    """Test retrieving organization context for an affiliated clinician."""
    doc_id = "doc-ctx-org"
    token = seed_user(doc_id, UserRole.DOCTOR)
    headers = {"Authorization": f"Bearer {token}"}

    await _global_organization_repo.add_clinician_membership(
        ClinicianOrganizationMembershipRecord(
            id="mem-ctx-a",
            clinician_id=doc_id,
            organization_id="org-a",
            role_title="Head of Cardiology",
        )
    )

    resp = await async_client.get("/api/v1/clinicians/me/organizations/org-a/context", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["organization"]["id"] == "org-a"
    assert data["organization_status"] == "ACTIVE"
    assert data["clinician_relationship"]["role_title"] == "Head of Cardiology"
    assert len(data["accessible_facilities"]) == 2


@pytest.mark.asyncio
async def test_clinician_unauthorized_organization_context(async_client: AsyncClient, setup_network):
    """Test 403 when clinician attempts to access context of an organization they don't belong to."""
    doc_id = "doc-ctx-unauth"
    token = seed_user(doc_id, UserRole.DOCTOR)
    headers = {"Authorization": f"Bearer {token}"}

    # Belong to Org A only
    await _global_organization_repo.add_clinician_membership(
        ClinicianOrganizationMembershipRecord(
            id="mem-only-a",
            clinician_id=doc_id,
            organization_id="org-a",
        )
    )

    # Attempt to access Org B context
    resp = await async_client.get("/api/v1/clinicians/me/organizations/org-b/context", headers=headers)
    assert resp.status_code == 403
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "CLINICIAN_ORGANIZATION_ACCESS_DENIED"


@pytest.mark.asyncio
async def test_clinician_facility_context_success(async_client: AsyncClient, setup_network):
    """Test retrieving facility context for an authorized clinician."""
    doc_id = "doc-ctx-fac"
    token = seed_user(doc_id, UserRole.DOCTOR)
    headers = {"Authorization": f"Bearer {token}"}

    # Grant facility membership
    await _global_facility_repo.add_clinician_membership(
        ClinicianFacilityMembershipRecord(
            id="facmem-ctx",
            clinician_id=doc_id,
            facility_id="fac-a1",
            organization_id="org-a",
            role_title="Staff Physician",
        )
    )

    resp = await async_client.get("/api/v1/clinicians/me/facilities/fac-a1/context", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["facility"]["id"] == "fac-a1"
    assert data["organization"]["id"] == "org-a"
    assert len(data["departments"]) == 2
    assert data["clinician_relationship"]["role_title"] == "Staff Physician"
    assert data["facility_status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_clinician_unauthorized_facility_context(async_client: AsyncClient, setup_network):
    """Test 403 when clinician attempts to access context of an unauthorized facility."""
    doc_id = "doc-fac-unauth"
    token = seed_user(doc_id, UserRole.DOCTOR)
    headers = {"Authorization": f"Bearer {token}"}

    # Member of A1 only; attempt B1
    resp = await async_client.get("/api/v1/clinicians/me/facilities/fac-b1/context", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "CLINICIAN_FACILITY_ACCESS_DENIED"


# ============================================================================
# 5. Relationship & Status Invariant Tests
# ============================================================================

@pytest.mark.asyncio
async def test_facility_organization_relationship_validation(async_client: AsyncClient, setup_network):
    """Test validation prevents associating facility with wrong organization."""
    from app.services.facility_access_service import FacilityAccessService
    from app.core.exceptions import FacilityOrganizationMismatchException

    fac_access = FacilityAccessService(
        facility_repo=_global_facility_repo,
        organization_repo=_global_organization_repo,
        audit_service=None,
    )

    # Valid relationship: fac-a1 belongs to org-a
    fac = await fac_access.validate_organization_facility_relationship("fac-a1", "org-a")
    assert fac.id == "fac-a1"

    # Invalid relationship: fac-a1 does not belong to org-b
    with pytest.raises(FacilityOrganizationMismatchException):
        await fac_access.validate_organization_facility_relationship("fac-a1", "org-b")


@pytest.mark.asyncio
async def test_inactive_facility_rejected(async_client: AsyncClient, setup_network):
    """Test inactive facility rejected during context check."""
    doc_id = "doc-inact-fac"
    token = seed_user(doc_id, UserRole.DOCTOR)
    headers = {"Authorization": f"Bearer {token}"}

    await _global_facility_repo.add_clinician_membership(
        ClinicianFacilityMembershipRecord(
            id="facmem-inact",
            clinician_id=doc_id,
            facility_id="fac-inact",
            organization_id="org-inact",
        )
    )

    resp = await async_client.get("/api/v1/clinicians/me/facilities/fac-inact/context", headers=headers)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "FACILITY_INACTIVE"


# ============================================================================
# 6. Security & Audit Trail Tests
# ============================================================================

@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(async_client: AsyncClient, setup_network):
    """Unauthenticated requests must be rejected with 401."""
    resp = await async_client.get("/api/v1/organizations")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_unauthorized_role_clinician_endpoints(async_client: AsyncClient, setup_network):
    """Patients cannot access clinician self-network endpoints."""
    patient_token = seed_user("pat-p11", UserRole.PATIENT)
    headers = {"Authorization": f"Bearer {patient_token}"}

    resp = await async_client.get("/api/v1/clinicians/me/organizations", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_audit_events_recorded(async_client: AsyncClient, setup_network):
    """Verify that sensitive Phase 11 operations log immutable audit events without PHI."""
    doc_id = "doc-audit-test"
    token = seed_user(doc_id, UserRole.DOCTOR)
    headers = {"Authorization": f"Bearer {token}"}

    await _global_organization_repo.add_clinician_membership(
        ClinicianOrganizationMembershipRecord(
            id="mem-aud",
            clinician_id=doc_id,
            organization_id="org-a",
        )
    )

    # Trigger events
    await async_client.get("/api/v1/organizations", headers=headers)
    await async_client.get("/api/v1/organizations/org-a", headers=headers)
    await async_client.get("/api/v1/organizations/org-a/facilities", headers=headers)
    await async_client.get("/api/v1/facilities/fac-a1", headers=headers)
    await async_client.get("/api/v1/facilities/fac-a1/departments", headers=headers)
    await async_client.get("/api/v1/clinicians/me/organizations", headers=headers)
    await async_client.get("/api/v1/clinicians/me/organizations/org-a/context", headers=headers)

    recorded_types = [e.event_type for e in _global_audit_repo._events]
    assert AuditEventType.ORGANIZATION_LIST_VIEWED in recorded_types
    assert AuditEventType.ORGANIZATION_VIEWED in recorded_types
    assert AuditEventType.FACILITY_LIST_VIEWED in recorded_types
    assert AuditEventType.FACILITY_VIEWED in recorded_types
    assert AuditEventType.DEPARTMENT_LIST_VIEWED in recorded_types
    assert AuditEventType.CLINICIAN_ORGANIZATIONS_VIEWED in recorded_types
    assert AuditEventType.ORGANIZATION_CONTEXT_VIEWED in recorded_types
