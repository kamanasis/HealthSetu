"""Interoperability & Healthcare Data Exchange API Endpoints (Phase 13).

Provides endpoints for:
- Standards-based external data import (FHIR R4 / HL7)
- External import status and metadata retrieval
- Scoped patient data export
- Export status and metadata retrieval
- Patient-specific export (POST /api/v1/patients/{patient_id}/interoperability/export)
"""

from typing import Annotated
from fastapi import APIRouter, Depends, Path, Query, Request, status

from app.api.deps import (
    get_authorization_service,
    get_current_user,
    get_interoperability_service,
    get_patient_service,
    require_permission,
    verify_patient_access,
)
from app.core.exceptions import (
    ExportNotFoundException,
    ForbiddenException,
    ImportNotFoundException,
)
from app.core.logging import request_id_ctx_var
from app.core.policies import Permission
from app.schemas.auth import UserRole
from app.schemas.interoperability import (
    InteroperabilityExportRecord,
    InteroperabilityExportRequest,
    InteroperabilityExportResponse,
    InteroperabilityImportRecord,
    InteroperabilityImportRequest,
    InteroperabilityImportResponse,
    PatientExportRequest,
)
from app.schemas.response import StandardSuccessResponse
from app.schemas.user import AuthenticatedUserContext
from app.services.authorization_service import AuthorizationService
from app.services.interoperability_service import InteroperabilityService
from app.services.patient_service import PatientService

router = APIRouter(tags=["Interoperability & Healthcare Data Exchange"])


def _req_id(request: Request) -> str:
    """Extract request ID from request state or context variable."""
    return getattr(request.state, "request_id", None) or request_id_ctx_var.get() or "unknown"


# ---------------------------------------------------------------------------
# POST /api/v1/interoperability/import
# ---------------------------------------------------------------------------

@router.post(
    "/interoperability/import",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardSuccessResponse[InteroperabilityImportResponse],
    summary="Import external healthcare data",
    description="Accept an authorized external healthcare resource/message for validation, identity resolution, and candidate staging.",
)
async def import_external_data(
    request: Request,
    payload: InteroperabilityImportRequest,
    current_user: Annotated[AuthenticatedUserContext, Depends(require_permission(Permission.INTEROPERABILITY_IMPORT))],
    interop_service: Annotated[InteroperabilityService, Depends(get_interoperability_service)],
) -> StandardSuccessResponse[InteroperabilityImportResponse]:
    """Import external healthcare data into HealthSetu candidate staging."""
    record = await interop_service.import_external_data(
        request=payload,
        current_user=current_user,
        request_id=_req_id(request),
    )

    response_data = InteroperabilityImportResponse(
        import_id=record.id,
        status=record.status,
        source_system=record.source_system,
        resource_type=record.resource_type,
        external_resource_id=record.external_resource_id,
        healthsetu_patient_id=record.healthsetu_patient_id,
        verification_status=record.verification_status,
        message=f"Resource {record.resource_type} received and placed in status {record.status.value}",
        created_at=record.created_at,
    )

    return StandardSuccessResponse(
        data=response_data,
        message="External healthcare data accepted successfully",
        request_id=_req_id(request),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/interoperability/imports/{import_id}
# ---------------------------------------------------------------------------

@router.get(
    "/interoperability/imports/{import_id}",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[InteroperabilityImportRecord],
    summary="Get import status and metadata",
    description="Return authorized import status and metadata without exposing raw clinical payloads to unauthorized callers.",
)
async def get_import_record(
    request: Request,
    import_id: Annotated[str, Path(description="Unique ID of the import record")],
    current_user: Annotated[AuthenticatedUserContext, Depends(require_permission(Permission.INTEROPERABILITY_READ))],
    interop_service: Annotated[InteroperabilityService, Depends(get_interoperability_service)],
) -> StandardSuccessResponse[InteroperabilityImportRecord]:
    """Retrieve import status and metadata by ID."""
    record = await interop_service.get_import_record(import_id)
    if not record:
        raise ImportNotFoundException(f"Import record '{import_id}' was not found.")

    # Access control: If caller is a patient, verify they own the record
    if current_user.role == UserRole.PATIENT and record.healthsetu_patient_id:
        if record.healthsetu_patient_id != current_user.user_id:
            raise ForbiddenException("Access denied: You cannot view import records for another patient.")

    # Audit resource viewed
    await interop_service.audit_resource_viewed(
        user_id=current_user.user_id,
        resource_type="interoperability_import",
        resource_id=import_id,
        request_id=_req_id(request),
    )

    return StandardSuccessResponse(
        data=record,
        message="Import record retrieved successfully",
        request_id=_req_id(request),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/interoperability/export
# ---------------------------------------------------------------------------

@router.post(
    "/interoperability/export",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=StandardSuccessResponse[InteroperabilityExportResponse],
    summary="Create authorized patient data export",
    description="Initiate an authorized patient clinical data export to a target provider with least-privilege scoping and consent verification.",
)
async def export_patient_data(
    request: Request,
    payload: InteroperabilityExportRequest,
    current_user: Annotated[AuthenticatedUserContext, Depends(require_permission(Permission.INTEROPERABILITY_EXPORT))],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    interop_service: Annotated[InteroperabilityService, Depends(get_interoperability_service)],
) -> StandardSuccessResponse[InteroperabilityExportResponse]:
    """Export authorized patient clinical data."""
    # Verify patient access for current caller
    await verify_patient_access(
        patient_id=payload.patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="interoperability:export",
        resource_type="patient",
        consent_scope="interoperability",
    )

    record = await interop_service.export_patient_data(
        request=payload,
        current_user=current_user,
        request_id=_req_id(request),
    )

    response_data = InteroperabilityExportResponse(
        export_id=record.id,
        status=record.status,
        patient_id=record.patient_id,
        format=record.format,
        scope=record.scope,
        target_system=record.target_system,
        delivered_bundle_id=record.delivered_bundle_id,
        message=f"Export request completed with status {record.status.value}",
        created_at=record.created_at,
    )

    return StandardSuccessResponse(
        data=response_data,
        message="Export processed successfully",
        request_id=_req_id(request),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/interoperability/exports/{export_id}
# ---------------------------------------------------------------------------

@router.get(
    "/interoperability/exports/{export_id}",
    status_code=status.HTTP_200_OK,
    response_model=StandardSuccessResponse[InteroperabilityExportRecord],
    summary="Get export status and metadata",
    description="Return authorized export status and metadata.",
)
async def get_export_record(
    request: Request,
    export_id: Annotated[str, Path(description="Unique ID of the export record")],
    current_user: Annotated[AuthenticatedUserContext, Depends(require_permission(Permission.INTEROPERABILITY_READ))],
    interop_service: Annotated[InteroperabilityService, Depends(get_interoperability_service)],
) -> StandardSuccessResponse[InteroperabilityExportRecord]:
    """Retrieve export status and metadata by ID."""
    record = await interop_service.get_export_record(export_id)
    if not record:
        raise ExportNotFoundException(f"Export record '{export_id}' was not found.")

    # Access control: If caller is a patient, verify they own the record
    if current_user.role == UserRole.PATIENT:
        if record.patient_id != current_user.user_id:
            raise ForbiddenException("Access denied: You cannot view export records for another patient.")

    # Audit resource viewed
    await interop_service.audit_resource_viewed(
        user_id=current_user.user_id,
        resource_type="interoperability_export",
        resource_id=export_id,
        request_id=_req_id(request),
    )

    return StandardSuccessResponse(
        data=record,
        message="Export record retrieved successfully",
        request_id=_req_id(request),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/patients/{patient_id}/interoperability/export
# ---------------------------------------------------------------------------

@router.post(
    "/patients/{patient_id}/interoperability/export",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=StandardSuccessResponse[InteroperabilityExportResponse],
    summary="Export specific patient data by patient ID",
    description="Convenience patient-specific export endpoint adhering to HealthSetu conventions.",
)
async def export_specific_patient(
    request: Request,
    patient_id: Annotated[str, Path(description="HealthSetu internal patient ID")],
    payload: PatientExportRequest,
    current_user: Annotated[AuthenticatedUserContext, Depends(require_permission(Permission.INTEROPERABILITY_EXPORT))],
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    interop_service: Annotated[InteroperabilityService, Depends(get_interoperability_service)],
) -> StandardSuccessResponse[InteroperabilityExportResponse]:
    """Export specific patient healthcare records."""
    # Verify caller access to patient
    await verify_patient_access(
        patient_id=patient_id,
        current_user=current_user,
        patient_service=patient_service,
        authz_service=authz_service,
        action="interoperability:export",
        resource_type="patient",
        consent_scope="interoperability",
    )

    full_request = InteroperabilityExportRequest(
        patient_id=patient_id,
        scope=payload.scope,
        resource_types=payload.resource_types,
        format=payload.format,
        target_system=payload.target_system,
        consent_id=payload.consent_id,
    )

    record = await interop_service.export_patient_data(
        request=full_request,
        current_user=current_user,
        request_id=_req_id(request),
    )

    response_data = InteroperabilityExportResponse(
        export_id=record.id,
        status=record.status,
        patient_id=record.patient_id,
        format=record.format,
        scope=record.scope,
        target_system=record.target_system,
        delivered_bundle_id=record.delivered_bundle_id,
        message=f"Export request completed with status {record.status.value}",
        created_at=record.created_at,
    )

    return StandardSuccessResponse(
        data=response_data,
        message="Patient export processed successfully",
        request_id=_req_id(request),
    )
