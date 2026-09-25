"""FastAPI dependency injection providers for authentication, authorization, and services."""

from typing import Annotated
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.policies import Permission
from app.core.security import decode_access_token
from app.core.config import get_settings
from app.integrations.ocr.base import OCRProvider
from app.integrations.ocr.local_ocr import LocalOCRProvider
from app.integrations.scanning.base import DocumentSecurityScanner
from app.integrations.scanning.mock_scanner import MockSecurityScanner
from app.integrations.storage.base import DocumentStorage
from app.integrations.storage.local_storage import LocalDocumentStorage
from app.repositories.allergy_repository import AllergyRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.auth_session_repository import AuthSessionRepository
from app.repositories.clinical_history_repository import ClinicalHistoryRepository
from app.repositories.consent_repository import ConsentRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.encounter_repository import EncounterRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.permission_repository import PermissionRepository
from app.repositories.user_repository import UserRepository
from app.repositories.vitals_repository import VitalsRepository
from app.schemas.auth import UserRole
from app.schemas.authorization import AuthorizationContext
from app.schemas.patient import PatientResponse
from app.schemas.user import AuthenticatedUserContext
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.authorization_service import AuthorizationService
from app.services.clinical_record_service import ClinicalRecordService
from app.services.consent_service import ConsentService
from app.services.document_processing_service import DocumentProcessingService
from app.services.document_service import DocumentService
from app.services.patient_service import PatientService
from app.services.processors.generic_processor import GenericDocumentProcessor
from app.services.processors.registry import DocumentProcessorRegistry
from app.repositories.prescription_repository import PrescriptionRepository
from app.repositories.medication_repository import MedicationRepository
from app.repositories.patient_medication_repository import PatientMedicationRepository
from app.integrations.medication.base import MedicationTerminologyProvider
from app.integrations.medication.providers.local import LocalMedicationProvider
from app.integrations.medication.providers.rxnorm import RxNormProvider
from app.services.medication_normalization_service import MedicationNormalizationService
from app.services.prescription_service import PrescriptionService
from app.services.medication_service import MedicationService
from app.repositories.medication_safety_repository import MedicationSafetyRepository
from app.integrations.medication_safety.base import MedicationSafetyProvider
from app.integrations.medication_safety.registry import get_medication_safety_provider
from app.services.medication_safety_service import MedicationSafetyService

# Phase 8: Triage & SBAR imports
from app.repositories.symptom_repository import SymptomRepository
from app.repositories.triage_repository import TriageRepository
from app.repositories.sbar_repository import SBARRepository
from app.integrations.triage.base import TriageRuleEngine
from app.integrations.triage.rule_engine import HealthSetuDeterministicTriageEngine
from app.integrations.ai.base import ClinicalTextGenerator
from app.integrations.ai.providers.template_generator import TemplateClinicalTextGenerator
from app.integrations.ai.providers.mock_llm import MockLLMClinicalTextGenerator
from app.integrations.ai.validator import SBARFactValidator
from app.services.symptom_service import SymptomService
from app.services.triage_service import TriageService
from app.services.sbar_service import SBARService

# Phase 9: Care Plan & Discharge imports
from app.repositories.discharge_repository import DischargeRepository
from app.repositories.care_plan_repository import CarePlanRepository
from app.integrations.discharge.base import DischargeExtractor
from app.integrations.discharge.extractor import LocalDischargeExtractor
from app.services.discharge_service import DischargeService
from app.services.care_plan_service import CarePlanService

# ---------------------------------------------------------------------------
# HTTP Bearer scheme
# ---------------------------------------------------------------------------
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Bearer access token in Authorization header (Format: Bearer <token>)",
)

# ---------------------------------------------------------------------------
# Global default repositories (in-memory fallbacks until DB team delivers schema)
# ---------------------------------------------------------------------------
_global_user_repo = UserRepository()
_global_session_repo = AuthSessionRepository()
_global_consent_repo = ConsentRepository()
_global_audit_repo = AuditRepository()
_global_permission_repo = PermissionRepository()
_global_patient_repo = PatientRepository()
_global_history_repo = ClinicalHistoryRepository()
_global_allergy_repo = AllergyRepository()
_global_vitals_repo = VitalsRepository()
_global_encounter_repo = EncounterRepository()
_global_document_repo = DocumentRepository()
_global_document_storage = LocalDocumentStorage()
_global_security_scanner = MockSecurityScanner()
_global_ocr_provider = LocalOCRProvider()
_global_processor = GenericDocumentProcessor(_global_ocr_provider)
_global_processor_registry = DocumentProcessorRegistry(_global_processor)

# ---------------------------------------------------------------------------
# Phase 6: Global default repositories & providers
# ---------------------------------------------------------------------------
_global_prescription_repo = PrescriptionRepository()
_global_medication_repo = MedicationRepository()
_global_patient_medication_repo = PatientMedicationRepository()
_global_medication_terminology_provider = LocalMedicationProvider()
_global_medication_safety_repo = MedicationSafetyRepository()

# ---------------------------------------------------------------------------
# Phase 8: Global default repositories & providers
# ---------------------------------------------------------------------------
_global_symptom_repo = SymptomRepository()
_global_triage_repo = TriageRepository()
_global_sbar_repo = SBARRepository()
_global_triage_engine = HealthSetuDeterministicTriageEngine()
_global_template_generator = TemplateClinicalTextGenerator()
_global_ai_generator = MockLLMClinicalTextGenerator()
_global_sbar_validator = SBARFactValidator()

# ---------------------------------------------------------------------------
# Phase 9: Global default repositories & providers
# ---------------------------------------------------------------------------
_global_discharge_repo = DischargeRepository()
_global_care_plan_repo = CarePlanRepository()
_global_discharge_extractor = LocalDischargeExtractor()

_global_authz_service = AuthorizationService(
    permission_repository=_global_permission_repo,
    consent_service=ConsentService(consent_repository=_global_consent_repo),
    audit_service=AuditService(audit_repository=_global_audit_repo),
)



# ---------------------------------------------------------------------------
# Phase 1/2: Repository providers
# ---------------------------------------------------------------------------

def get_user_repository() -> UserRepository:
    """Dependency provider for UserRepository."""
    return _global_user_repo


def get_auth_session_repository() -> AuthSessionRepository:
    """Dependency provider for AuthSessionRepository."""
    return _global_session_repo


# ---------------------------------------------------------------------------
# Phase 3: Repository providers
# ---------------------------------------------------------------------------

def get_consent_repository() -> ConsentRepository:
    """Dependency provider for ConsentRepository."""
    return _global_consent_repo


def get_audit_repository() -> AuditRepository:
    """Dependency provider for AuditRepository."""
    return _global_audit_repo


def get_permission_repository() -> PermissionRepository:
    """Dependency provider for PermissionRepository."""
    return _global_permission_repo


# ---------------------------------------------------------------------------
# Phase 4: Repository providers
# ---------------------------------------------------------------------------

def get_patient_repository() -> PatientRepository:
    """Dependency provider for PatientRepository."""
    return _global_patient_repo


def get_clinical_history_repository() -> ClinicalHistoryRepository:
    """Dependency provider for ClinicalHistoryRepository."""
    return _global_history_repo


def get_allergy_repository() -> AllergyRepository:
    """Dependency provider for AllergyRepository."""
    return _global_allergy_repo


def get_vitals_repository() -> VitalsRepository:
    """Dependency provider for VitalsRepository."""
    return _global_vitals_repo


def get_encounter_repository() -> EncounterRepository:
    """Dependency provider for EncounterRepository."""
    return _global_encounter_repo


# ---------------------------------------------------------------------------
# Phase 5: Repository & Integration providers
# ---------------------------------------------------------------------------

def get_document_repository() -> DocumentRepository:
    """Dependency provider for DocumentRepository."""
    return _global_document_repo


def get_document_storage() -> DocumentStorage:
    """Dependency provider for DocumentStorage."""
    return _global_document_storage


def get_security_scanner() -> DocumentSecurityScanner:
    """Dependency provider for DocumentSecurityScanner."""
    return _global_security_scanner


def get_processor_registry() -> DocumentProcessorRegistry:
    """Dependency provider for DocumentProcessorRegistry."""
    return _global_processor_registry


# ---------------------------------------------------------------------------
# Phase 6: Repository & Integration providers
# ---------------------------------------------------------------------------

def get_prescription_repository() -> PrescriptionRepository:
    """Dependency provider for PrescriptionRepository."""
    return _global_prescription_repo


def get_medication_repository() -> MedicationRepository:
    """Dependency provider for MedicationRepository."""
    return _global_medication_repo


def get_patient_medication_repository() -> PatientMedicationRepository:
    """Dependency provider for PatientMedicationRepository."""
    return _global_patient_medication_repo


def get_medication_terminology_provider() -> MedicationTerminologyProvider:
    """Dependency provider for MedicationTerminologyProvider."""
    settings = get_settings()
    if settings.MEDICATION_TERMINOLOGY_PROVIDER.lower() == "rxnorm":
        return RxNormProvider(
            base_url=settings.MEDICATION_TERMINOLOGY_BASE_URL or None,
            api_key=settings.MEDICATION_TERMINOLOGY_API_KEY or None,
            timeout_seconds=settings.MEDICATION_TERMINOLOGY_TIMEOUT_SECONDS,
            max_retries=settings.MEDICATION_NORMALIZATION_MAX_RETRIES,
        )
    return _global_medication_terminology_provider


def get_medication_safety_repository() -> MedicationSafetyRepository:
    """Dependency provider for MedicationSafetyRepository."""
    return _global_medication_safety_repo


def get_medication_safety_provider_dep() -> MedicationSafetyProvider:
    """Dependency provider for MedicationSafetyProvider."""
    return get_medication_safety_provider()


# ---------------------------------------------------------------------------
# Phase 8: Repository & Provider dependencies
# ---------------------------------------------------------------------------

def get_symptom_repository() -> SymptomRepository:
    """Dependency provider for SymptomRepository."""
    return _global_symptom_repo


def get_triage_repository() -> TriageRepository:
    """Dependency provider for TriageRepository."""
    return _global_triage_repo


def get_sbar_repository() -> SBARRepository:
    """Dependency provider for SBARRepository."""
    return _global_sbar_repo


def get_triage_engine() -> TriageRuleEngine:
    """Dependency provider for TriageRuleEngine."""
    return _global_triage_engine


def get_template_generator() -> ClinicalTextGenerator:
    """Dependency provider for TemplateClinicalTextGenerator."""
    return _global_template_generator


def get_ai_generator() -> ClinicalTextGenerator:
    """Dependency provider for AI ClinicalTextGenerator."""
    return _global_ai_generator


def get_sbar_validator() -> SBARFactValidator:
    """Dependency provider for SBARFactValidator."""
    return _global_sbar_validator


# ---------------------------------------------------------------------------
# Phase 9: Repository & Provider dependencies
# ---------------------------------------------------------------------------

def get_discharge_repository() -> DischargeRepository:
    """Dependency provider for DischargeRepository."""
    return _global_discharge_repo


def get_care_plan_repository() -> CarePlanRepository:
    """Dependency provider for CarePlanRepository."""
    return _global_care_plan_repo


def get_discharge_extractor() -> DischargeExtractor:
    """Dependency provider for DischargeExtractor."""
    return _global_discharge_extractor



# ---------------------------------------------------------------------------
# Phase 1/2: Service providers
# ---------------------------------------------------------------------------

def get_auth_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    session_repo: Annotated[AuthSessionRepository, Depends(get_auth_session_repository)],
) -> AuthService:
    """Dependency provider for AuthService."""
    return AuthService(user_repository=user_repo, session_repository=session_repo)


# ---------------------------------------------------------------------------
# Phase 3: Service providers
# ---------------------------------------------------------------------------

def get_audit_service(
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
) -> AuditService:
    """Dependency provider for AuditService."""
    return AuditService(audit_repository=audit_repo)


def get_consent_service(
    consent_repo: Annotated[ConsentRepository, Depends(get_consent_repository)],
) -> ConsentService:
    """Dependency provider for ConsentService."""
    return ConsentService(consent_repository=consent_repo)


def get_authorization_service(
    permission_repo: Annotated[PermissionRepository, Depends(get_permission_repository)] = None,
    consent_service: Annotated[ConsentService, Depends(get_consent_service)] = None,
    audit_service: Annotated[AuditService, Depends(get_audit_service)] = None,
) -> AuthorizationService:
    """Dependency provider for AuthorizationService."""
    return _global_authz_service


# ---------------------------------------------------------------------------
# Phase 4: Service providers
# ---------------------------------------------------------------------------

def get_patient_service(
    patient_repo: Annotated[PatientRepository, Depends(get_patient_repository)],
) -> PatientService:
    """Dependency provider for PatientService."""
    return PatientService(patient_repository=patient_repo)


def get_clinical_record_service(
    history_repo: Annotated[ClinicalHistoryRepository, Depends(get_clinical_history_repository)],
    allergy_repo: Annotated[AllergyRepository, Depends(get_allergy_repository)],
    vitals_repo: Annotated[VitalsRepository, Depends(get_vitals_repository)],
    encounter_repo: Annotated[EncounterRepository, Depends(get_encounter_repository)],
) -> ClinicalRecordService:
    """Dependency provider for ClinicalRecordService."""
    return ClinicalRecordService(
        history_repo=history_repo,
        allergy_repo=allergy_repo,
        vitals_repo=vitals_repo,
        encounter_repo=encounter_repo,
    )


# ---------------------------------------------------------------------------
# Phase 5: Service providers
# ---------------------------------------------------------------------------

def get_document_service(
    doc_repo: Annotated[DocumentRepository, Depends(get_document_repository)],
    storage: Annotated[DocumentStorage, Depends(get_document_storage)],
    scanner: Annotated[DocumentSecurityScanner, Depends(get_security_scanner)],
) -> DocumentService:
    """Dependency provider for DocumentService."""
    settings = get_settings()
    return DocumentService(
        repository=doc_repo,
        storage=storage,
        scanner=scanner,
        max_size_bytes=settings.max_document_size_bytes,
    )


def get_document_processing_service(
    doc_repo: Annotated[DocumentRepository, Depends(get_document_repository)],
    storage: Annotated[DocumentStorage, Depends(get_document_storage)],
    registry: Annotated[DocumentProcessorRegistry, Depends(get_processor_registry)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> DocumentProcessingService:
    """Dependency provider for DocumentProcessingService."""
    settings = get_settings()
    return DocumentProcessingService(
        repository=doc_repo,
        storage=storage,
        registry=registry,
        audit_service=audit_service,
        max_retries=settings.MAX_PROCESSING_RETRIES,
    )


# ---------------------------------------------------------------------------
# Phase 6: Service providers
# ---------------------------------------------------------------------------

def get_medication_normalization_service(
    provider: Annotated[MedicationTerminologyProvider, Depends(get_medication_terminology_provider)],
    medication_repo: Annotated[MedicationRepository, Depends(get_medication_repository)],
    patient_medication_repo: Annotated[PatientMedicationRepository, Depends(get_patient_medication_repository)],
    prescription_repo: Annotated[PrescriptionRepository, Depends(get_prescription_repository)],
) -> MedicationNormalizationService:
    """Dependency provider for MedicationNormalizationService."""
    return MedicationNormalizationService(
        provider=provider,
        medication_repo=medication_repo,
        patient_medication_repo=patient_medication_repo,
        prescription_repo=prescription_repo,
    )


def get_prescription_service(
    prescription_repo: Annotated[PrescriptionRepository, Depends(get_prescription_repository)],
    medication_repo: Annotated[MedicationRepository, Depends(get_medication_repository)],
    document_repo: Annotated[DocumentRepository, Depends(get_document_repository)],
    normalization_service: Annotated[MedicationNormalizationService, Depends(get_medication_normalization_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> PrescriptionService:
    """Dependency provider for PrescriptionService."""
    return PrescriptionService(
        prescription_repo=prescription_repo,
        medication_repo=medication_repo,
        document_repo=document_repo,
        normalization_service=normalization_service,
        audit_service=audit_service,
    )


def get_medication_service(
    patient_medication_repo: Annotated[PatientMedicationRepository, Depends(get_patient_medication_repository)],
    medication_repo: Annotated[MedicationRepository, Depends(get_medication_repository)],
    provider: Annotated[MedicationTerminologyProvider, Depends(get_medication_terminology_provider)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> MedicationService:
    """Dependency provider for MedicationService."""
    return MedicationService(
        patient_medication_repo=patient_medication_repo,
        medication_repo=medication_repo,
        provider=provider,
        audit_service=audit_service,
    )


# ---------------------------------------------------------------------------
# Phase 7: Medication Safety service provider
# ---------------------------------------------------------------------------

def get_medication_safety_service(
    safety_repo: Annotated[MedicationSafetyRepository, Depends(get_medication_safety_repository)],
    patient_medication_repo: Annotated[PatientMedicationRepository, Depends(get_patient_medication_repository)],
    medication_repo: Annotated[MedicationRepository, Depends(get_medication_repository)],
    allergy_repo: Annotated[AllergyRepository, Depends(get_allergy_repository)],
    clinical_history_repo: Annotated[ClinicalHistoryRepository, Depends(get_clinical_history_repository)],
    patient_repo: Annotated[PatientRepository, Depends(get_patient_repository)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    provider: Annotated[MedicationSafetyProvider, Depends(get_medication_safety_provider_dep)],
) -> MedicationSafetyService:
    """Dependency provider for MedicationSafetyService."""
    return MedicationSafetyService(
        safety_repo=safety_repo,
        patient_medication_repo=patient_medication_repo,
        medication_repo=medication_repo,
        allergy_repo=allergy_repo,
        clinical_history_repo=clinical_history_repo,
        patient_repo=patient_repo,
        audit_service=audit_service,
        provider=provider,
    )


# ---------------------------------------------------------------------------
# Phase 8: Triage & SBAR service providers
# ---------------------------------------------------------------------------

def get_symptom_service(
    symptom_repo: Annotated[SymptomRepository, Depends(get_symptom_repository)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> SymptomService:
    """Dependency provider for SymptomService."""
    return SymptomService(
        symptom_repo=symptom_repo,
        audit_service=audit_service,
    )


def get_triage_service(
    triage_repo: Annotated[TriageRepository, Depends(get_triage_repository)],
    symptom_repo: Annotated[SymptomRepository, Depends(get_symptom_repository)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    rule_engine: Annotated[TriageRuleEngine, Depends(get_triage_engine)],
    vitals_repo: Annotated[VitalsRepository, Depends(get_vitals_repository)],
    patient_repo: Annotated[PatientRepository, Depends(get_patient_repository)],
    clinical_history_repo: Annotated[ClinicalHistoryRepository, Depends(get_clinical_history_repository)],
    allergy_repo: Annotated[AllergyRepository, Depends(get_allergy_repository)],
    patient_medication_repo: Annotated[PatientMedicationRepository, Depends(get_patient_medication_repository)],
) -> TriageService:
    """Dependency provider for TriageService."""
    return TriageService(
        triage_repo=triage_repo,
        symptom_repo=symptom_repo,
        audit_service=audit_service,
        rule_engine=rule_engine,
        vitals_repo=vitals_repo,
        patient_repo=patient_repo,
        clinical_history_repo=clinical_history_repo,
        allergy_repo=allergy_repo,
        patient_medication_repo=patient_medication_repo,
    )


def get_sbar_service(
    sbar_repo: Annotated[SBARRepository, Depends(get_sbar_repository)],
    triage_repo: Annotated[TriageRepository, Depends(get_triage_repository)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    template_generator: Annotated[ClinicalTextGenerator, Depends(get_template_generator)],
    ai_generator: Annotated[ClinicalTextGenerator, Depends(get_ai_generator)],
    validator: Annotated[SBARFactValidator, Depends(get_sbar_validator)],
    symptom_repo: Annotated[SymptomRepository, Depends(get_symptom_repository)],
    vitals_repo: Annotated[VitalsRepository, Depends(get_vitals_repository)],
    clinical_history_repo: Annotated[ClinicalHistoryRepository, Depends(get_clinical_history_repository)],
    allergy_repo: Annotated[AllergyRepository, Depends(get_allergy_repository)],
    patient_medication_repo: Annotated[PatientMedicationRepository, Depends(get_patient_medication_repository)],
    encounter_repo: Annotated[EncounterRepository, Depends(get_encounter_repository)],
) -> SBARService:
    """Dependency provider for SBARService."""
    return SBARService(
        sbar_repo=sbar_repo,
        triage_repo=triage_repo,
        audit_service=audit_service,
        template_generator=template_generator,
        ai_generator=ai_generator,
        validator=validator,
        symptom_repo=symptom_repo,
        vitals_repo=vitals_repo,
        clinical_history_repo=clinical_history_repo,
        allergy_repo=allergy_repo,
        patient_medication_repo=patient_medication_repo,
        encounter_repo=encounter_repo,
    )


# ---------------------------------------------------------------------------
# Phase 9: Service providers
# ---------------------------------------------------------------------------

def get_discharge_service(
    discharge_repo: Annotated[DischargeRepository, Depends(get_discharge_repository)],
    document_repo: Annotated[DocumentRepository, Depends(get_document_repository)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    extractor: Annotated[DischargeExtractor, Depends(get_discharge_extractor)],
) -> DischargeService:
    """Dependency provider for DischargeService."""
    return DischargeService(
        discharge_repo=discharge_repo,
        document_repo=document_repo,
        audit_service=audit_service,
        extractor=extractor,
    )


def get_care_plan_service(
    care_plan_repo: Annotated[CarePlanRepository, Depends(get_care_plan_repository)],
    discharge_repo: Annotated[DischargeRepository, Depends(get_discharge_repository)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> CarePlanService:
    """Dependency provider for CarePlanService."""
    return CarePlanService(
        care_plan_repo=care_plan_repo,
        discharge_repo=discharge_repo,
        audit_service=audit_service,
    )



# ---------------------------------------------------------------------------
# Phase 2: Authentication dependency
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthenticatedUserContext:
    """Reusable authentication dependency verifying JWT bearer tokens and caller context.

    Protected endpoints consume this dependency:
        current_user: AuthenticatedUserContext = Depends(get_current_user)
    """
    if credentials is None:
        raise UnauthorizedException("Authentication credentials were not provided.")

    if credentials.scheme.lower() != "bearer":
        raise UnauthorizedException("Invalid authentication scheme. 'Bearer' required.")

    token = credentials.credentials
    if not token or not token.strip():
        raise UnauthorizedException("Invalid token format.")

    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Token payload missing subject identifier.")

    user_context = await auth_service.get_user_context(str(user_id))
    return user_context


# ---------------------------------------------------------------------------
# Phase 3: Authorization dependencies
# ---------------------------------------------------------------------------

def require_permission(permission: Permission):
    """FastAPI dependency factory: require authenticated user to have a specific permission.

    Usage:
        @router.get("/resource")
        async def endpoint(
            _: None = Depends(require_permission(Permission.CLINICAL_RECORD_READ)),
            current_user: AuthenticatedUserContext = Depends(get_current_user),
        ):
            ...

    Note: This checks role → permission only. Ownership and consent are
    evaluated via require_resource_access() or AuthorizationService.authorize().
    """
    async def _dependency(
        current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
        authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    ) -> AuthenticatedUserContext:
        decision = await authz_service.check_permission(current_user, permission)
        if not decision.allowed:
            raise ForbiddenException("You do not have permission to perform this action.")
        return current_user

    return _dependency


def require_role(*roles: str):
    """FastAPI dependency factory: require authenticated user to have one of the given roles.

    Use sparingly. Prefer require_permission() for most authorization decisions.
    Use require_role() only when role-level gating is explicitly required by policy
    (e.g., only an ADMIN may invoke a specific management endpoint).

    Usage:
        @router.get("/admin/users")
        async def list_users(
            current_user: AuthenticatedUserContext = Depends(require_role("ADMIN")),
        ):
            ...
    """
    async def _dependency(
        current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    ) -> AuthenticatedUserContext:
        if current_user.role.value not in {r.upper() for r in roles}:
            raise ForbiddenException("Your role does not permit this action.")
        return current_user

    return _dependency


def require_resource_access(
    action: str,
    resource_type: str | None = None,
    require_ownership: bool = False,
    require_relationship: bool = False,
    consent_purpose: str | None = None,
    consent_scope: str | None = None,
):
    """FastAPI dependency factory: full authorization evaluation for resource access.

    Evaluates the complete authorization pipeline:
      1. Authentication (get_current_user)
      2. Permission check (role → permission for action)
      3. Ownership check (if require_ownership=True)
      4. Relationship check (if require_relationship=True)
      5. Consent check (if consent_purpose + consent_scope provided)

    Resource-specific IDs (resource_id, resource_owner_id) must be passed
    at the route level because they are path parameters, not injectable at
    dependency creation time.

    Example — patient accesses their own profile (no consent required):
        Depends(require_resource_access("patient:read_self", require_ownership=True))

    Example — doctor reads a patient clinical record (needs relationship + consent):
        Depends(require_resource_access(
            "clinical_record:read",
            resource_type="clinical_record",
            require_relationship=True,
            consent_purpose="care_delivery",
            consent_scope="clinical_records",
        ))

    The returned dependency provides the AuthorizationContext so routes can
    pass resource-specific IDs to the service directly for more control.
    """
    async def _dependency(
        current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
        authz_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    ) -> AuthenticatedUserContext:
        # Build a base context — routes that need owner/resource IDs should
        # call authz_service.authorize_or_raise() directly for full control.
        context = AuthorizationContext(
            user_id=current_user.user_id,
            role=current_user.role.value,
            resource_type=resource_type,
        )
        await authz_service.authorize_or_raise(
            user=current_user,
            action=action,
            context=context,
            require_ownership=require_ownership,
            require_relationship=require_relationship,
            consent_purpose=consent_purpose,
            consent_scope=consent_scope,
        )
        return current_user

    return _dependency


# ---------------------------------------------------------------------------
# Phase 4: Patient access verification helper
# ---------------------------------------------------------------------------

async def verify_patient_access(
    patient_id: str,
    current_user: AuthenticatedUserContext,
    patient_service: PatientService,
    authz_service: AuthorizationService,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    consent_scope: str = "clinical_records",
) -> PatientResponse:
    """Evaluate patient access for current user.

    - PATIENT: verifies ownership (user_id matches patient record); raises NotFoundException if mismatch.
               evaluates authorize_or_raise with require_ownership=True.
    - DOCTOR: evaluates authorize_or_raise with require_relationship=True and consent.
    - ADMIN/OTHER: evaluates authorize_or_raise (will deny because admin has no clinical permissions).
    """
    if current_user.role == UserRole.PATIENT:
        patient = await patient_service.get_patient_record_for_user(current_user.user_id, patient_id)
        await authz_service.authorize_or_raise(
            user=current_user,
            action=action,
            context=AuthorizationContext(
                user_id=current_user.user_id,
                role=current_user.role.value,
                resource_type=resource_type,
                resource_id=resource_id or patient_id,
                resource_owner_id=current_user.user_id,
            ),
            require_ownership=True,
        )
        return patient

    elif current_user.role == UserRole.DOCTOR:
        patient = await patient_service.get_patient(patient_id)
        owner_id = patient.user_id or patient.id
        await authz_service.authorize_or_raise(
            user=current_user,
            action=action,
            context=AuthorizationContext(
                user_id=current_user.user_id,
                role=current_user.role.value,
                resource_type=resource_type,
                resource_id=resource_id or patient_id,
                resource_owner_id=owner_id,
            ),
            require_relationship=True,
            consent_purpose="care_delivery",
            consent_scope=consent_scope,
        )
        return patient

    else:
        await authz_service.authorize_or_raise(
            user=current_user,
            action=action,
            context=AuthorizationContext(
                user_id=current_user.user_id,
                role=current_user.role.value,
                resource_type=resource_type,
                resource_id=resource_id or patient_id,
            ),
        )
        return await patient_service.get_patient(patient_id)

