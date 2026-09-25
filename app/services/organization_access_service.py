"""Clinician Organization Access Service (Phase 11).

Validates organization status and clinician-organization memberships.
Enforces multi-organization access boundaries without assuming 1 clinician = 1 organization.
"""

from app.core.exceptions import (
    ClinicianOrganizationAccessDeniedException,
    OrganizationInactiveException,
    OrganizationNotFoundException,
)
from app.core.logging import get_logger
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.organization import (
    ClinicianOrganizationMembershipRecord,
    OrganizationRecord,
    OrganizationStatus,
)
from app.services.audit_service import AuditService

logger = get_logger("app.services.organization_access")


class OrganizationAccessService:
    """Evaluates and validates clinician access to healthcare organizations."""

    def __init__(
        self,
        organization_repo: OrganizationRepository,
        audit_service: AuditService,
    ) -> None:
        self.organization_repo = organization_repo
        self.audit_service = audit_service

    async def check_clinician_access(
        self,
        clinician_id: str,
        organization_id: str,
        require_active: bool = True,
    ) -> tuple[OrganizationRecord, ClinicianOrganizationMembershipRecord]:
        """Validate that the clinician has active membership in the organization.

        Raises:
            OrganizationNotFoundException: if organization does not exist.
            OrganizationInactiveException: if organization is not ACTIVE.
            ClinicianOrganizationAccessDeniedException: if clinician does not belong to organization.
        """
        org = await self.organization_repo.get_by_id(organization_id)
        if not org:
            raise OrganizationNotFoundException(
                message=f"Healthcare organization '{organization_id}' not found."
            )

        if require_active and org.status != OrganizationStatus.ACTIVE:
            raise OrganizationInactiveException(
                message=f"Organization '{org.name}' status is {org.status.value}; operational access denied."
            )

        membership = await self.organization_repo.get_clinician_membership(
            clinician_id=clinician_id,
            organization_id=organization_id,
        )

        if not membership or membership.status != "ACTIVE":
            logger.warning(
                f"Clinician '{clinician_id}' denied access to organization '{organization_id}'"
            )
            await self.audit_service.record_access_denied(
                actor_id=clinician_id,
                action="organization:access",
                reason_code="CLINICIAN_ORGANIZATION_ACCESS_DENIED",
                resource_type="organization",
                resource_id=organization_id,
            )
            raise ClinicianOrganizationAccessDeniedException(
                message=f"Clinician is not an active member of organization '{org.name}'."
            )

        return org, membership

    async def get_accessible_organizations(
        self,
        clinician_id: str,
    ) -> list[tuple[OrganizationRecord, ClinicianOrganizationMembershipRecord]]:
        """Return all active organizations accessible to the authenticated clinician."""
        memberships = await self.organization_repo.get_clinician_memberships(clinician_id)
        accessible: list[tuple[OrganizationRecord, ClinicianOrganizationMembershipRecord]] = []

        for m in memberships:
            if m.status != "ACTIVE":
                continue
            org = await self.organization_repo.get_by_id(m.organization_id)
            if org and org.status == OrganizationStatus.ACTIVE:
                accessible.append((org, m))

        return accessible
