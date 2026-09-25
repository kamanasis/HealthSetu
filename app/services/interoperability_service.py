"""Interoperability Service (Phase 13).

Coordinates healthcare data exchange, external identifier matching, FHIR validation,
consent verification, outbound bundle generation, and clinical review boundaries.

Architectural boundaries:
- Interoperability != Clinical Decision Support
- External Data != Automatically Verified Internal Data
- Does NOT silently overwrite verified clinical records
- Deterministic patient matching only — never guesses matches
"""

from datetime import datetime, timezone
import uuid
from typing import Any

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AmbiguousPatientMatchException,
    ExportNotFoundException,
    ExternalIdentityUnresolvedException,
    ImportNotFoundException,
    InteroperabilityConsentRequiredException,
    InteroperabilityDisabledException,
    InvalidFHIRResourceException,
    NotFoundException,
    UnsupportedFHIRVersionException,
    UnsupportedInteroperabilityFormatException,
    UnsupportedResourceTypeException,
)
from app.core.logging import get_logger
from app.integrations.interoperability.base import InteroperabilityProvider
from app.integrations.interoperability.fhir.mapper import FHIRMapper
from app.integrations.interoperability.fhir.validator import FHIRValidator
from app.repositories.allergy_repository import AllergyRepository
from app.repositories.consent_repository import ConsentRepository, ConsentStatus
from app.repositories.document_repository import DocumentRepository
from app.repositories.encounter_repository import EncounterRepository
from app.repositories.interoperability_repository import InteroperabilityRepository
from app.repositories.patient_medication_repository import PatientMedicationRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.vitals_repository import VitalsRepository
from app.schemas.audit import AuditEventType
from app.schemas.interoperability import (
    ExportScope,
    ExportStatus,
    ImportStatus,
    InteroperabilityExportRecord,
    InteroperabilityExportRequest,
    InteroperabilityExportResponse,
    InteroperabilityFormat,
    InteroperabilityImportRecord,
    InteroperabilityImportRequest,
    InteroperabilityImportResponse,
    SupportedFHIRResourceType,
    VerificationStatus,
)
from app.schemas.user import AuthenticatedUserContext
from app.services.audit_service import AuditService

logger = get_logger("app.services.interoperability")


class InteroperabilityService:
    """Service managing external healthcare data exchange and clinical boundaries."""

    def __init__(
        self,
        interop_repo: InteroperabilityRepository,
        patient_repo: PatientRepository,
        vitals_repo: VitalsRepository,
        allergy_repo: AllergyRepository,
        medication_repo: PatientMedicationRepository,
        encounter_repo: EncounterRepository,
        document_repo: DocumentRepository,
        consent_repo: ConsentRepository,
        fhir_mapper: FHIRMapper,
        fhir_validator: FHIRValidator,
        provider: InteroperabilityProvider,
        audit_service: AuditService,
        settings: Settings | None = None,
    ) -> None:
        self.interop_repo = interop_repo
        self.patient_repo = patient_repo
        self.vitals_repo = vitals_repo
        self.allergy_repo = allergy_repo
        self.medication_repo = medication_repo
        self.encounter_repo = encounter_repo
        self.document_repo = document_repo
        self.consent_repo = consent_repo
        self.fhir_mapper = fhir_mapper
        self.fhir_validator = fhir_validator
        self.provider = provider
        self.audit_service = audit_service
        self.settings = settings or get_settings()

    # ========================================================================
    # IMPORT PIPELINE
    # ========================================================================

    async def import_resource(
        self,
        request_data: InteroperabilityImportRequest,
        user_context: AuthenticatedUserContext,
    ) -> InteroperabilityImportResponse:
        """Receive, validate, resolve identity, and stage an external healthcare resource."""
        if not self.settings.INTEROPERABILITY_ENABLED:
            raise InteroperabilityDisabledException()

        # 1. Validate Format and Specification Version
        if request_data.format == InteroperabilityFormat.FHIR:
            if not self.settings.FHIR_ENABLED:
                raise UnsupportedInteroperabilityFormatException("FHIR exchange is disabled by configuration.")
            if request_data.format_version and request_data.format_version.upper() != self.settings.FHIR_VERSION.upper():
                raise UnsupportedFHIRVersionException(
                    f"FHIR version '{request_data.format_version}' is not supported. Configured version: '{self.settings.FHIR_VERSION}'."
                )
        elif request_data.format == InteroperabilityFormat.HL7:
            if not self.settings.HL7_ENABLED:
                raise UnsupportedInteroperabilityFormatException("HL7 message exchange is disabled by configuration.")
        else:
            raise UnsupportedInteroperabilityFormatException(f"Format '{request_data.format}' is not supported.")

        # 2. Idempotency Check: Don't re-import identical external resource without change
        existing_import = await self.interop_repo.find_import_by_source_resource(
            source_system=request_data.source_system,
            external_resource_id=request_data.external_resource_id,
        )
        if existing_import:
            logger.info(
                f"Idempotent hit: Resource '{request_data.external_resource_id}' from '{request_data.source_system}' already imported as '{existing_import.id}'"
            )
            return InteroperabilityImportResponse.model_validate(existing_import)

        await self.audit_service.record(
            event_type=AuditEventType.INTEROPERABILITY_IMPORT_STARTED,
            outcome="ALLOW",
            actor_id=user_context.user_id,
            action="interoperability:import",
            resource_type=request_data.resource_type,
            resource_id=request_data.external_resource_id,
            metadata={
                "source_system": request_data.source_system,
                "format": request_data.format.value,
            },
        )

        try:
            # 3. Structural & Schema Validation
            validation_errors: list[str] = []
            if request_data.format == InteroperabilityFormat.FHIR:
                validation_errors = self.fhir_validator.validate_resource(
                    payload=request_data.payload,
                    expected_type=request_data.resource_type,
                )
                if validation_errors:
                    raise InvalidFHIRResourceException(
                        message=f"FHIR validation failed: {'; '.join(validation_errors)}",
                        details={"errors": validation_errors},
                    )

            # 4. Resolve Patient Identity Deterministically
            resolved_patient_id = await self._resolve_patient_identity(
                source_system=request_data.source_system,
                external_patient_id=request_data.external_patient_id,
                healthsetu_patient_id=request_data.healthsetu_patient_id,
                payload=request_data.payload,
                resource_type=request_data.resource_type,
            )

            # 5. Map Resource to HealthSetu Candidate Representation
            mapped_data = self.fhir_mapper.map_inbound_resource(
                resource_type=request_data.resource_type,
                payload=request_data.payload,
                source_system=request_data.source_system,
                healthsetu_patient_id=resolved_patient_id,
            )

            # 6. Stage Import Record (MARKED REVIEW_REQUIRED — NEVER SILENTLY OVERWRITE)
            import_id = f"imp-{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc)

            import_record = InteroperabilityImportRecord(
                id=import_id,
                source_system=request_data.source_system,
                source_organization_id=request_data.source_organization_id,
                format=request_data.format,
                format_version=request_data.format_version or "R4",
                resource_type=request_data.resource_type,
                external_resource_id=request_data.external_resource_id,
                external_patient_id=request_data.external_patient_id,
                healthsetu_patient_id=resolved_patient_id,
                status=ImportStatus.REVIEW_REQUIRED,
                verification_status=VerificationStatus.REVIEW_REQUIRED,
                raw_payload=request_data.payload,
                mapped_data=mapped_data,
                mapped_entity_type=request_data.resource_type,
                mapped_entity_id=None,  # Not verified or inserted as active yet
                validation_errors=[],
                imported_by=user_context.user_id,
                created_at=now,
                updated_at=now,
            )

            persisted = await self.interop_repo.create_import(import_record)

            await self.audit_service.record(
                event_type=AuditEventType.INTEROPERABILITY_IMPORT_COMPLETED,
                outcome="ALLOW",
                actor_id=user_context.user_id,
                action="interoperability:import",
                resource_type=request_data.resource_type,
                resource_id=import_id,
                metadata={
                    "external_resource_id": request_data.external_resource_id,
                    "patient_id": resolved_patient_id,
                    "status": ImportStatus.REVIEW_REQUIRED.value,
                },
            )

            await self.audit_service.record(
                event_type=AuditEventType.INTEROPERABILITY_VERIFICATION_REQUIRED,
                outcome="ALLOW",
                actor_id=user_context.user_id,
                action="interoperability:verification_gate",
                resource_type="interoperability_import",
                resource_id=import_id,
            )

            return InteroperabilityImportResponse.model_validate(persisted)

        except Exception as exc:
            await self.audit_service.record(
                event_type=AuditEventType.INTEROPERABILITY_IMPORT_FAILED,
                outcome="DENY",
                actor_id=user_context.user_id,
                action="interoperability:import",
                resource_type=request_data.resource_type,
                resource_id=request_data.external_resource_id,
                reason_code=type(exc).__name__,
            )
            raise

    async def get_import(
        self,
        import_id: str,
        user_context: AuthenticatedUserContext,
    ) -> InteroperabilityImportResponse:
        """Fetch status and metadata for an import record."""
        record = await self.interop_repo.get_import(import_id)
        if not record:
            raise ImportNotFoundException(f"Import record '{import_id}' not found.")

        await self.audit_service.record(
            event_type=AuditEventType.INTEROPERABILITY_RESOURCE_VIEWED,
            outcome="ALLOW",
            actor_id=user_context.user_id,
            action="interoperability:read",
            resource_type="interoperability_import",
            resource_id=import_id,
        )

        return InteroperabilityImportResponse.model_validate(record)

    # ========================================================================
    # EXPORT PIPELINE
    # ========================================================================

    async def export_patient_data(
        self,
        request_data: InteroperabilityExportRequest,
        user_context: AuthenticatedUserContext,
    ) -> InteroperabilityExportResponse:
        """Extract, transform, and export authorized patient clinical data into FHIR R4 Bundle."""
        if not self.settings.INTEROPERABILITY_ENABLED:
            raise InteroperabilityDisabledException()

        patient_id = request_data.patient_id

        # 1. Verify Patient Exists
        patient = await self.patient_repo.get_by_id(patient_id)
        if not patient:
            raise NotFoundException(f"Patient '{patient_id}' not found.")

        # 2. Enforce Phase 3 Consent for Interoperability Data Sharing
        active_consents = await self.consent_repo.list_by_patient(patient_id, status_filter=ConsentStatus.ACTIVE)
        if not active_consents and patient.user_id:
            active_consents = await self.consent_repo.list_by_patient(patient.user_id, status_filter=ConsentStatus.ACTIVE)

        has_consent = False
        valid_consent_id = request_data.consent_id

        for c in active_consents:
            c_scopes = getattr(c, "scopes", None) or [getattr(c, "scope", "")]
            if isinstance(c_scopes, str):
                c_scopes = [c_scopes]
            scopes = [s.lower() for s in c_scopes if s]
            if any(s in scopes for s in ("interoperability", "clinical_records", "all_records")):
                has_consent = True
                valid_consent_id = valid_consent_id or c.id
                break

        if not has_consent and not request_data.consent_id:
            logger.warning(f"Export rejected: Missing interoperability consent for patient '{patient_id}'")
            raise InteroperabilityConsentRequiredException(
                "Patient consent is required for interoperability data exchange."
            )

        await self.audit_service.record(
            event_type=AuditEventType.INTEROPERABILITY_EXPORT_STARTED,
            outcome="ALLOW",
            actor_id=user_context.user_id,
            action="interoperability:export",
            resource_type="patient",
            resource_id=patient_id,
            metadata={
                "target_system": request_data.target_system,
                "scope": request_data.scope.value,
                "format": request_data.format.value,
            },
        )

        try:
            # 3. Assemble Resources Based on Requested ExportScope
            resources: list[dict[str, Any]] = []
            requested_types = (
                [t.lower() for t in request_data.resource_types]
                if request_data.resource_types
                else None
            )

            # Check for unsupported resource types if explicit filter supplied
            supported_types = {t.value.lower() for t in SupportedFHIRResourceType}
            if requested_types:
                for rt in requested_types:
                    if rt not in supported_types:
                        raise UnsupportedResourceTypeException(f"Resource type '{rt}' is not supported for export.")

            # Patient demographics (unless explicitly filtered out)
            if not requested_types or "patient" in requested_types:
                patient_fhir = self.fhir_mapper.map_patient_outbound(patient)
                resources.append(patient_fhir)

            if request_data.scope in (ExportScope.FULL_AUTHORIZED_RECORD, ExportScope.VITALS):
                if not requested_types or "observation" in requested_types:
                    vitals = await self.vitals_repo.list_by_patient(patient_id=patient_id, limit=20)
                    for v in vitals:
                        resources.append(self.fhir_mapper.map_vital_outbound(v, patient_id))

            if request_data.scope in (ExportScope.FULL_AUTHORIZED_RECORD, ExportScope.ALLERGIES):
                if not requested_types or "allergyintolerance" in requested_types:
                    allergies = await self.allergy_repo.list_by_patient(patient_id=patient_id)
                    for a in allergies:
                        resources.append(self.fhir_mapper.map_allergy_outbound(a, patient_id))

            if request_data.scope in (ExportScope.FULL_AUTHORIZED_RECORD, ExportScope.MEDICATIONS):
                if not requested_types or "medicationrequest" in requested_types:
                    meds = await self.medication_repo.list_by_patient(patient_id=patient_id, limit=20)
                    for m in meds:
                        resources.append(self.fhir_mapper.map_medication_outbound(m, patient_id))

            if request_data.scope in (ExportScope.FULL_AUTHORIZED_RECORD, ExportScope.ENCOUNTER):
                if not requested_types or "encounter" in requested_types:
                    encs, _ = await self.encounter_repo.list_by_patient(patient_id=patient_id, limit=10)
                    for enc in encs:
                        resources.append(self.fhir_mapper.map_encounter_outbound(enc, patient_id))

            if request_data.scope in (ExportScope.FULL_AUTHORIZED_RECORD, ExportScope.DOCUMENTS):
                if not requested_types or "documentreference" in requested_types:
                    docs, _ = await self.document_repo.list_by_patient(patient_id=patient_id, limit=10)
                    for doc in docs:
                        resources.append(self.fhir_mapper.map_document_outbound(doc, patient_id))

            # 4. Construct and Validate FHIR Bundle
            fhir_bundle = self.fhir_mapper.create_fhir_bundle(resources)
            self.fhir_validator.validate_or_raise(fhir_bundle)

            # 5. Dispatch via Adapter Provider
            delivery_result = await self.provider.export_resource(
                target_system=request_data.target_system,
                resource_payload=fhir_bundle,
                format=request_data.format.value,
            )

            export_id = f"exp-{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc)

            export_record = InteroperabilityExportRecord(
                id=export_id,
                patient_id=patient_id,
                target_system=request_data.target_system,
                target_organization_id=request_data.target_organization_id,
                format=request_data.format,
                format_version=request_data.format_version or "R4",
                scope=request_data.scope,
                resource_types=[r.get("resourceType", "") for r in resources],
                status=ExportStatus.DELIVERED,
                exported_bundle=fhir_bundle,
                exported_count=len(resources),
                exported_by=user_context.user_id,
                consent_id=valid_consent_id,
                created_at=now,
                updated_at=now,
            )

            persisted = await self.interop_repo.create_export(export_record)

            # Audit completion and data sharing
            await self.audit_service.record(
                event_type=AuditEventType.INTEROPERABILITY_EXPORT_COMPLETED,
                outcome="ALLOW",
                actor_id=user_context.user_id,
                action="interoperability:export",
                resource_type="patient",
                resource_id=patient_id,
                metadata={
                    "export_id": export_id,
                    "target_system": request_data.target_system,
                    "resources_count": len(resources),
                },
            )

            await self.audit_service.record(
                event_type=AuditEventType.INTEROPERABILITY_DATA_SHARED,
                outcome="ALLOW",
                actor_id=user_context.user_id,
                action="interoperability:share",
                resource_type="export_bundle",
                resource_id=export_id,
                metadata={
                    "scope": request_data.scope.value,
                    "target_system": request_data.target_system,
                },
            )

            return InteroperabilityExportResponse(
                export_id=export_id,
                patient_id=patient_id,
                target_system=request_data.target_system,
                format=request_data.format,
                format_version=request_data.format_version or "R4",
                scope=request_data.scope,
                status=ExportStatus.DELIVERED,
                resource_count=len(resources),
                data=fhir_bundle,
                created_at=now,
            )

        except Exception as exc:
            await self.audit_service.record(
                event_type=AuditEventType.INTEROPERABILITY_EXPORT_FAILED,
                outcome="DENY",
                actor_id=user_context.user_id,
                action="interoperability:export",
                resource_type="patient",
                resource_id=patient_id,
                reason_code=type(exc).__name__,
            )
            raise

    async def get_export(
        self,
        export_id: str,
        user_context: AuthenticatedUserContext,
    ) -> InteroperabilityExportResponse:
        """Fetch status and metadata for an export record."""
        record = await self.interop_repo.get_export(export_id)
        if not record:
            raise ExportNotFoundException(f"Export record '{export_id}' not found.")

        await self.audit_service.record(
            event_type=AuditEventType.INTEROPERABILITY_RESOURCE_VIEWED,
            outcome="ALLOW",
            actor_id=user_context.user_id,
            action="interoperability:read",
            resource_type="interoperability_export",
            resource_id=export_id,
        )

        return InteroperabilityExportResponse(
            export_id=record.id,
            patient_id=record.patient_id,
            target_system=record.target_system,
            format=record.format,
            format_version=record.format_version,
            scope=record.scope,
            status=record.status,
            resource_count=record.exported_count,
            data=record.exported_bundle,
            created_at=record.created_at,
        )

    # ========================================================================
    # IDENTITY RESOLUTION HELPER
    # ========================================================================

    async def _resolve_patient_identity(
        self,
        source_system: str,
        external_patient_id: str | None,
        healthsetu_patient_id: str | None,
        payload: dict[str, Any],
        resource_type: str,
    ) -> str:
        """Resolve external patient identity to HealthSetu patient ID without guessing.

        Deterministic rules:
        1. If explicit healthsetu_patient_id is supplied, verify it exists.
        2. If external_patient_id is supplied, look up established deterministic mapping.
        3. If resource is Patient, inspect identifiers for HealthSetu system URI or external ID.
        4. If resource is a clinical resource, check subject reference (e.g. 'Patient/{id}').
        5. NEVER guess or merge based on demographic heuristics.
        """
        # 1. Direct HealthSetu patient ID
        if healthsetu_patient_id:
            p = await self.patient_repo.get_by_id(healthsetu_patient_id)
            if not p:
                await self.audit_service.record(
                    event_type=AuditEventType.EXTERNAL_IDENTITY_UNRESOLVED,
                    outcome="DENY",
                    actor_id="system",
                    action="identity:resolve",
                    resource_type="patient",
                    resource_id=healthsetu_patient_id,
                )
                raise ExternalIdentityUnresolvedException(
                    f"Specified HealthSetu patient ID '{healthsetu_patient_id}' does not exist."
                )
            # Record resolved mapping if external ID provided
            if external_patient_id:
                await self.interop_repo.map_identity(source_system, external_patient_id, healthsetu_patient_id)
            await self.audit_service.record(
                event_type=AuditEventType.EXTERNAL_IDENTITY_RESOLVED,
                outcome="ALLOW",
                actor_id="system",
                action="identity:resolve",
                resource_type="patient",
                resource_id=healthsetu_patient_id,
                metadata={"source_system": source_system, "method": "direct_id"},
            )
            return healthsetu_patient_id

        # 2. Known external ID mapping
        if external_patient_id:
            mapped_id = await self.interop_repo.resolve_identity(source_system, external_patient_id)
            if mapped_id:
                p = await self.patient_repo.get_by_id(mapped_id)
                if p:
                    await self.audit_service.record(
                        event_type=AuditEventType.EXTERNAL_IDENTITY_RESOLVED,
                        outcome="ALLOW",
                        actor_id="system",
                        action="identity:resolve",
                        resource_type="patient",
                        resource_id=mapped_id,
                        metadata={"source_system": source_system, "method": "saved_mapping"},
                    )
                    return mapped_id

        # 3. Patient resource internal identifiers
        if resource_type.lower() == "patient":
            # Check for direct HealthSetu system identifier tag
            for ident in payload.get("identifier", []):
                if isinstance(ident, dict):
                    sys = ident.get("system", "")
                    val = ident.get("value", "")
                    if "healthsetu" in sys and val:
                        p = await self.patient_repo.get_by_id(val)
                        if p:
                            if external_patient_id:
                                await self.interop_repo.map_identity(source_system, external_patient_id, p.id)
                            return p.id
            # Also check if payload.id is an existing HealthSetu patient ID
            pid_raw = str(payload.get("id") or "")
            if pid_raw:
                p = await self.patient_repo.get_by_id(pid_raw)
                if p:
                    return p.id

        # 4. Clinical resource subject reference
        subject_ref = (
            payload.get("subject", {}).get("reference")
            or payload.get("patient", {}).get("reference")
        )
        if subject_ref and isinstance(subject_ref, str) and subject_ref.startswith("Patient/"):
            cand_id = subject_ref.split("Patient/")[1].strip()
            # Check if this matches a direct HealthSetu patient
            p = await self.patient_repo.get_by_id(cand_id)
            if p:
                return p.id
            # Or if it's a known external patient ID
            mapped_id = await self.interop_repo.resolve_identity(source_system, cand_id)
            if mapped_id:
                p = await self.patient_repo.get_by_id(mapped_id)
                if p:
                    return p.id

        # 5. Failed resolution: Reject to avoid guessing or corrupting records
        await self.audit_service.record(
            event_type=AuditEventType.EXTERNAL_IDENTITY_UNRESOLVED,
            outcome="DENY",
            actor_id="system",
            action="identity:resolve",
            resource_type="external_resource",
            resource_id=str(payload.get("id") or "unknown"),
            metadata={"source_system": source_system, "external_patient_id": external_patient_id},
        )
        raise ExternalIdentityUnresolvedException(
            f"External patient identity could not be deterministically resolved from source '{source_system}'."
        )
