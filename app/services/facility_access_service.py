"""Clinician Facility Access Service (Phase 11).

Validates facility status, organization-facility relationships, and clinician-facility memberships.
Enforces multi-facility access boundaries without assuming 1 clinician = 1 facility.
"""

from app.core.exceptions import (
    ClinicianFacilityAccessDeniedException,
    FacilityInactiveException,
    FacilityNotFoundException,
    FacilityOrganizationMismatchException,
    OrganizationInactiveException,
    OrganizationNotFoundException,
)
from app.core.logging import get_logger
from app.repositories.facility_repository import FacilityRepository
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.facility import (
    ClinicianFacilityMembershipRecord,
    FacilityRecord,
    FacilityStatus,
)
from app.schemas.organization import OrganizationStatus
from app.services.audit_service import AuditService

logger = get_logger("app.services.facility_access")


class FacilityAccessService:
    """Evaluates and validates clinician access to healthcare facilities."""

    def __init__(
        self,
        facility_repo: FacilityRepository,
        organization_repo: OrganizationRepository,
        audit_service: AuditService,
    ) -> None:
        self.facility_repo = facility_repo
        self.organization_repo = organization_repo
        self.audit_service = audit_service

    async def validate_organization_facility_relationship(
        self,
        facility_id: str,
        organization_id: str,
    ) -> FacilityRecord:
        """Validate that a facility exists and actually belongs to the given organization.

        Raises:
            FacilityNotFoundException: if facility does not exist.
            FacilityOrganizationMismatchException: if facility does not belong to organization_id.
        """
        facility = await self.facility_repo.get_by_id(facility_id)
        if not facility:
            raise FacilityNotFoundException(
                message=f"Healthcare facility '{facility_id}' not found."
            )

        if facility.organization_id != organization_id:
            logger.warning(
                f"Facility organization mismatch: facility '{facility_id}' belongs to "
                f"'{facility.organization_id}', not '{organization_id}'"
            )
            raise FacilityOrganizationMismatchException(
                message=f"Facility '{facility.name}' does not belong to organization '{organization_id}'."
            )

        return facility

    async def check_clinician_access(
        self,
        clinician_id: str,
        facility_id: str,
        expected_organization_id: str | None = None,
        require_active: bool = True,
    ) -> tuple[FacilityRecord, ClinicianFacilityMembershipRecord]:
        """Validate that the clinician has active privileges/membership in the facility.

        Validates:
        1. Facility exists
        2. Facility belongs to expected organization (if specified)
        3. Facility status is ACTIVE
        4. Parent organization status is ACTIVE
        5. Clinician has an active membership record

        Raises:
            FacilityNotFoundException
            FacilityOrganizationMismatchException
            FacilityInactiveException
            OrganizationInactiveException
            ClinicianFacilityAccessDeniedException
        """
        facility = await self.facility_repo.get_by_id(facility_id)
        if not facility:
            raise FacilityNotFoundException(
                message=f"Healthcare facility '{facility_id}' not found."
            )

        if expected_organization_id and facility.organization_id != expected_organization_id:
            raise FacilityOrganizationMismatchException(
                message=f"Facility '{facility.name}' does not belong to organization '{expected_organization_id}'."
            )

        if require_active and facility.status != FacilityStatus.ACTIVE:
            raise FacilityInactiveException(
                message=f"Facility '{facility.name}' status is {facility.status.value}; operational access denied."
            )

        # Validate parent organization status
        org = await self.organization_repo.get_by_id(facility.organization_id)
        if require_active and org and org.status != OrganizationStatus.ACTIVE:
            raise OrganizationInactiveException(
                message=f"Parent organization '{org.name}' status is {org.status.value}; facility access denied."
            )

        membership = await self.facility_repo.get_clinician_membership(
            clinician_id=clinician_id,
            facility_id=facility_id,
        )

        if not membership or membership.status != "ACTIVE":
            logger.warning(
                f"Clinician '{clinician_id}' denied access to facility '{facility_id}'"
            )
            await self.audit_service.record_access_denied(
                actor_id=clinician_id,
                action="facility:access",
                reason_code="CLINICIAN_FACILITY_ACCESS_DENIED",
                resource_type="facility",
                resource_id=facility_id,
            )
            raise ClinicianFacilityAccessDeniedException(
                message=f"Clinician does not have active privileges at facility '{facility.name}'."
            )

        return facility, membership

    async def get_accessible_facilities(
        self,
        clinician_id: str,
    ) -> list[tuple[FacilityRecord, ClinicianFacilityMembershipRecord]]:
        """Return all active facilities accessible to the clinician."""
        memberships = await self.facility_repo.get_clinician_memberships(clinician_id)
        accessible: list[tuple[FacilityRecord, ClinicianFacilityMembershipRecord]] = []

        for m in memberships:
            if m.status != "ACTIVE":
                continue
            fac = await self.facility_repo.get_by_id(m.facility_id)
            if not fac or fac.status != FacilityStatus.ACTIVE:
                continue
            org = await self.organization_repo.get_by_id(fac.organization_id)
            if not org or org.status != OrganizationStatus.ACTIVE:
                continue
            accessible.append((fac, m))

        return accessible
