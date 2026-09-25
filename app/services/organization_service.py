"""Organization Service (Phase 11).

Business logic for healthcare organizations, status validation, filtering,
and clinician organization context.
"""

from app.core.exceptions import (
    OrganizationInactiveException,
    OrganizationNotFoundException,
)
from app.core.logging import get_logger
from app.repositories.facility_repository import FacilityRepository
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.audit import AuditEventType
from app.schemas.facility import FacilityResponse, FacilityStatus, FacilityType
from app.schemas.organization import (
    OrganizationListResponse,
    OrganizationRecord,
    OrganizationResponse,
    OrganizationStatus,
    OrganizationType,
)
from app.schemas.organization_context import (
    ClinicianOrganizationContextResponse,
    ClinicianOrganizationRelationship,
)
from app.schemas.user import AuthenticatedUserContext
from app.services.audit_service import AuditService
from app.services.organization_access_service import OrganizationAccessService

logger = get_logger("app.services.organization")


class OrganizationService:
    """Service managing healthcare organizations and organization context."""

    def __init__(
        self,
        organization_repo: OrganizationRepository,
        facility_repo: FacilityRepository,
        organization_access_service: OrganizationAccessService,
        audit_service: AuditService,
    ) -> None:
        self.organization_repo = organization_repo
        self.facility_repo = facility_repo
        self.organization_access_service = organization_access_service
        self.audit_service = audit_service

    async def list_organizations(
        self,
        user_context: AuthenticatedUserContext,
        limit: int = 50,
        offset: int = 0,
        name: str | None = None,
        status: OrganizationStatus | None = None,
        org_type: OrganizationType | None = None,
    ) -> tuple[list[OrganizationResponse], int]:
        """List paginated organizations with optional filtering."""
        records, total = await self.organization_repo.list_organizations(
            limit=limit,
            offset=offset,
            name=name,
            status=status,
            org_type=org_type,
        )

        await self.audit_service.record(
            event_type=AuditEventType.ORGANIZATION_LIST_VIEWED,
            outcome="ALLOW",
            actor_id=user_context.user_id,
            action="organization:list",
            resource_type="organization",
            metadata={"limit": limit, "offset": offset, "total": total},
        )

        responses = [OrganizationResponse.model_validate(r) for r in records]
        return responses, total

    async def get_organization(
        self,
        organization_id: str,
        user_context: AuthenticatedUserContext,
        require_active: bool = False,
    ) -> OrganizationResponse:
        """Retrieve organization details."""
        org = await self.organization_repo.get_by_id(organization_id)
        if not org:
            raise OrganizationNotFoundException(
                message=f"Healthcare organization '{organization_id}' not found."
            )

        if require_active and org.status != OrganizationStatus.ACTIVE:
            raise OrganizationInactiveException(
                message=f"Organization '{org.name}' status is {org.status.value}; operation requires an active organization."
            )

        await self.audit_service.record(
            event_type=AuditEventType.ORGANIZATION_VIEWED,
            outcome="ALLOW",
            actor_id=user_context.user_id,
            action="organization:read",
            resource_type="organization",
            resource_id=organization_id,
        )

        return OrganizationResponse.model_validate(org)

    async def get_organization_facilities(
        self,
        organization_id: str,
        user_context: AuthenticatedUserContext,
        limit: int = 50,
        offset: int = 0,
        status: FacilityStatus | None = None,
        facility_type: FacilityType | None = None,
    ) -> tuple[list[FacilityResponse], int]:
        """Return facilities belonging to the organization after validating organization status."""
        org = await self.organization_repo.get_by_id(organization_id)
        if not org:
            raise OrganizationNotFoundException(
                message=f"Healthcare organization '{organization_id}' not found."
            )

        if org.status != OrganizationStatus.ACTIVE:
            raise OrganizationInactiveException(
                message=f"Organization '{org.name}' status is {org.status.value}; cannot retrieve facilities."
            )

        fac_records, total = await self.facility_repo.list_by_organization(
            organization_id=organization_id,
            limit=limit,
            offset=offset,
            status=status,
            facility_type=facility_type,
        )

        await self.audit_service.record(
            event_type=AuditEventType.FACILITY_LIST_VIEWED,
            outcome="ALLOW",
            actor_id=user_context.user_id,
            action="organization:facilities_list",
            resource_type="organization",
            resource_id=organization_id,
            metadata={"total": total, "limit": limit, "offset": offset},
        )

        responses = [FacilityResponse.model_validate(f) for f in fac_records]
        return responses, total

    async def get_clinician_organizations(
        self,
        clinician_id: str,
        user_context: AuthenticatedUserContext,
    ) -> list[OrganizationResponse]:
        """Return organizations associated with the authenticated clinician."""
        accessible = await self.organization_access_service.get_accessible_organizations(clinician_id)

        await self.audit_service.record(
            event_type=AuditEventType.CLINICIAN_ORGANIZATIONS_VIEWED,
            outcome="ALLOW",
            actor_id=user_context.user_id,
            action="clinician:organizations_view",
            resource_type="clinician",
            resource_id=clinician_id,
            metadata={"count": len(accessible)},
        )

        return [OrganizationResponse.model_validate(org) for org, _ in accessible]

    async def get_clinician_organization_context(
        self,
        clinician_id: str,
        organization_id: str,
        user_context: AuthenticatedUserContext,
    ) -> ClinicianOrganizationContextResponse:
        """Return consolidated organization context for the authenticated clinician."""
        org, membership = await self.organization_access_service.check_clinician_access(
            clinician_id=clinician_id,
            organization_id=organization_id,
            require_active=True,
        )

        # Get facilities under this organization accessible to this clinician
        fac_records, _ = await self.facility_repo.list_by_organization(
            organization_id=organization_id,
            status=FacilityStatus.ACTIVE,
        )
        accessible_facilities = [FacilityResponse.model_validate(f) for f in fac_records]

        await self.audit_service.record(
            event_type=AuditEventType.ORGANIZATION_CONTEXT_VIEWED,
            outcome="ALLOW",
            actor_id=user_context.user_id,
            action="clinician:organization_context_view",
            resource_type="organization",
            resource_id=organization_id,
        )

        return ClinicianOrganizationContextResponse(
            organization=OrganizationResponse.model_validate(org),
            organization_status=org.status,
            clinician_relationship=ClinicianOrganizationRelationship(
                clinician_id=membership.clinician_id,
                organization_id=membership.organization_id,
                role_title=membership.role_title,
                status=membership.status,
                joined_at=membership.joined_at,
            ),
            accessible_facilities=accessible_facilities,
        )
