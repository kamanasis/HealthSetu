"""Department Service (Phase 11).

Business logic for healthcare departments, facility relationship validation,
and retrieval.
"""

from app.core.exceptions import (
    DepartmentNotFoundException,
    FacilityNotFoundException,
)
from app.core.logging import get_logger
from app.repositories.department_repository import DepartmentRepository
from app.repositories.facility_repository import FacilityRepository
from app.schemas.audit import AuditEventType
from app.schemas.department import DepartmentRecord, DepartmentResponse, DepartmentStatus
from app.schemas.user import AuthenticatedUserContext
from app.services.audit_service import AuditService

logger = get_logger("app.services.department")


class DepartmentService:
    """Service managing hospital and clinic departments."""

    def __init__(
        self,
        department_repo: DepartmentRepository,
        facility_repo: FacilityRepository,
        audit_service: AuditService,
    ) -> None:
        self.department_repo = department_repo
        self.facility_repo = facility_repo
        self.audit_service = audit_service

    async def get_department(
        self,
        department_id: str,
        user_context: AuthenticatedUserContext,
        expected_facility_id: str | None = None,
    ) -> DepartmentResponse:
        """Retrieve department details and optionally validate facility relationship.

        Raises:
            DepartmentNotFoundException: if department does not exist or does not belong to expected facility.
        """
        dept = await self.department_repo.get_by_id(department_id)
        if not dept:
            raise DepartmentNotFoundException(
                message=f"Department '{department_id}' not found."
            )

        if expected_facility_id and dept.facility_id != expected_facility_id:
            logger.warning(
                f"Department '{department_id}' facility mismatch: belongs to '{dept.facility_id}', "
                f"expected '{expected_facility_id}'"
            )
            raise DepartmentNotFoundException(
                message=f"Department '{dept.name}' does not belong to facility '{expected_facility_id}'."
            )

        return DepartmentResponse.model_validate(dept)

    async def list_facility_departments(
        self,
        facility_id: str,
        user_context: AuthenticatedUserContext,
        status: DepartmentStatus | None = None,
    ) -> list[DepartmentResponse]:
        """List departments belonging to a facility with existence check."""
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
            action="department:list",
            resource_type="facility",
            resource_id=facility_id,
            metadata={"count": len(dep_records)},
        )

        return [DepartmentResponse.model_validate(d) for d in dep_records]
