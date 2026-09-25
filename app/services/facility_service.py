"""Facility Service (Phase 11).

Business logic for healthcare facilities, status validation, department listing,
and clinician facility context.
"""

from app.core.exceptions import (
    FacilityInactiveException,
    FacilityNotFoundException,
    OrganizationNotFoundException,
)
from app.core.logging import get_logger
from app.repositories.department_repository import DepartmentRepository
from app.repositories.facility_repository import FacilityRepository
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.audit import AuditEventType
from app.schemas.department import DepartmentResponse, DepartmentStatus
from app.schemas.facility import (
    FacilityRecord,
    FacilityResponse,
    FacilityStatus,
    FacilityType,
)
from app.schemas.facility_context import (
    ClinicianFacilityContextResponse,
    ClinicianFacilityRelationship,
)
from app.schemas.organization import OrganizationResponse
from app.schemas.user import AuthenticatedUserContext
from app.services.audit_service import AuditService
from app.services.facility_access_service import FacilityAccessService

logger = get_logger("app.services.facility")


class FacilityService:
    """Service managing healthcare facilities, departments, and facility context."""

    def __init__(
        self,
        facility_repo: FacilityRepository,
        organization_repo: OrganizationRepository,
        department_repo: DepartmentRepository,
        facility_access_service: FacilityAccessService,
        audit_service: AuditService,
    ) -> None:
        self.facility_repo = facility_repo
        self.organization_repo = organization_repo
        self.department_repo = department_repo
        self.facility_access_service = facility_access_service
        self.audit_service = audit_service

    async def get_facility(
        self,
        facility_id: str,
        user_context: AuthenticatedUserContext,
        require_active: bool = False,
    ) -> FacilityResponse:
        """Retrieve facility details and validate status if required."""
        facility = await self.facility_repo.get_by_id(facility_id)
        if not facility:
            raise FacilityNotFoundException(
                message=f"Healthcare facility '{facility_id}' not found."
            )

        if require_active and facility.status != FacilityStatus.ACTIVE:
            raise FacilityInactiveException(
                message=f"Facility '{facility.name}' status is {facility.status.value}; operational access denied."
            )

        await self.audit_service.record(
            event_type=AuditEventType.FACILITY_VIEWED,
            outcome="ALLOW",
            actor_id=user_context.user_id,
            action="facility:read",
            resource_type="facility",
            resource_id=facility_id,
        )

        return FacilityResponse.model_validate(facility)

    async def list_facilities(
        self,
        user_context: AuthenticatedUserContext,
        limit: int = 50,
        offset: int = 0,
        name: str | None = None,
        organization_id: str | None = None,
        facility_type: FacilityType | None = None,
        status: FacilityStatus | None = None,
    ) -> tuple[list[FacilityResponse], int]:
        """Search and list facilities with optional filters."""
        records, total = await self.facility_repo.list_facilities(
            limit=limit,
            offset=offset,
            name=name,
            organization_id=organization_id,
            facility_type=facility_type,
            status=status,
        )

        await self.audit_service.record(
            event_type=AuditEventType.FACILITY_LIST_VIEWED,
            outcome="ALLOW",
            actor_id=user_context.user_id,
            action="facility:list",
            resource_type="facility",
            metadata={"limit": limit, "offset": offset, "total": total},
        )

        responses = [FacilityResponse.model_validate(r) for r in records]
        return responses, total

    async def get_facility_departments(
        self,
        facility_id: str,
        user_context: AuthenticatedUserContext,
        status: DepartmentStatus | None = None,
    ) -> list[DepartmentResponse]:
        """Return departments belonging to the requested facility."""
        facility = await self.facility_repo.get_by_id(facility_id)
        if not facility:
            raise FacilityNotFoundException(
                message=f"Healthcare facility '{facility_id}' not found."
            )

        dep_records = await self.department_repo.list_by_facility(
            facility_id=facility_id,
            status=status,
        )

        await self.audit_service.record(
            event_type=AuditEventType.DEPARTMENT_LIST_VIEWED,
            outcome="ALLOW",
            actor_id=user_context.user_id,
            action="facility:departments_list",
            resource_type="facility",
            resource_id=facility_id,
            metadata={"department_count": len(dep_records)},
        )

        return [DepartmentResponse.model_validate(d) for d in dep_records]

    async def get_clinician_facilities(
        self,
        clinician_id: str,
        user_context: AuthenticatedUserContext,
    ) -> list[FacilityResponse]:
        """Return facilities accessible to the authenticated clinician."""
        accessible = await self.facility_access_service.get_accessible_facilities(clinician_id)

        await self.audit_service.record(
            event_type=AuditEventType.CLINICIAN_FACILITIES_VIEWED,
            outcome="ALLOW",
            actor_id=user_context.user_id,
            action="clinician:facilities_view",
            resource_type="clinician",
            resource_id=clinician_id,
            metadata={"count": len(accessible)},
        )

        return [FacilityResponse.model_validate(fac) for fac, _ in accessible]

    async def get_clinician_facility_context(
        self,
        clinician_id: str,
        facility_id: str,
        user_context: AuthenticatedUserContext,
    ) -> ClinicianFacilityContextResponse:
        """Return consolidated facility context for the authenticated clinician."""
        facility, membership = await self.facility_access_service.check_clinician_access(
            clinician_id=clinician_id,
            facility_id=facility_id,
            require_active=True,
        )

        org = await self.organization_repo.get_by_id(facility.organization_id)
        if not org:
            raise OrganizationNotFoundException(
                message=f"Parent organization '{facility.organization_id}' not found for facility '{facility.id}'."
            )

        departments = await self.department_repo.list_by_facility(
            facility_id=facility_id,
            status=DepartmentStatus.ACTIVE,
        )

        await self.audit_service.record(
            event_type=AuditEventType.FACILITY_CONTEXT_VIEWED,
            outcome="ALLOW",
            actor_id=user_context.user_id,
            action="clinician:facility_context_view",
            resource_type="facility",
            resource_id=facility_id,
        )

        return ClinicianFacilityContextResponse(
            facility=FacilityResponse.model_validate(facility),
            organization=OrganizationResponse.model_validate(org),
            departments=[DepartmentResponse.model_validate(d) for d in departments],
            clinician_relationship=ClinicianFacilityRelationship(
                clinician_id=membership.clinician_id,
                facility_id=membership.facility_id,
                organization_id=membership.organization_id,
                role_title=membership.role_title,
                status=membership.status,
                joined_at=membership.joined_at,
            ),
            facility_status=facility.status,
        )
