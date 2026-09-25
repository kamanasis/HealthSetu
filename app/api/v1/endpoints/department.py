"""Healthcare Department API Endpoints (Phase 11).

Provides routes for individual healthcare departments.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, Request, status

from app.api.deps import (
    get_current_user,
    get_department_service,
    require_permission,
)
from app.core.logging import request_id_ctx_var
from app.core.policies import Permission
from app.schemas.department import DepartmentResponse
from app.schemas.response import StandardSuccessResponse
from app.schemas.user import AuthenticatedUserContext
from app.services.department_service import DepartmentService

router = APIRouter(tags=["Healthcare Departments"])


def _req_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request_id_ctx_var.get() or "unknown"


@router.get(
    "/departments/{department_id}",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[DepartmentResponse],
    summary="Get department details",
    description="Return details of a specific healthcare department.",
)
async def get_department(
    request: Request,
    department_id: str,
    current_user: Annotated[AuthenticatedUserContext, Depends(require_permission(Permission.DEPARTMENT_READ))],
    department_service: Annotated[DepartmentService, Depends(get_department_service)],
) -> StandardSuccessResponse[DepartmentResponse]:
    department = await department_service.get_department(
        department_id=department_id,
        user_context=current_user,
    )
    return StandardSuccessResponse(data=department, request_id=_req_id(request))
