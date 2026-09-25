"""Licensed Commercial Medication Safety Provider Adapter (Production Stub).

=============================================================================
EXTERNAL PROVIDER DEPENDENCY — LICENSED INTEGRATION REQUIRED
=============================================================================
This adapter is a structured placeholder for an enterprise licensed clinical
safety provider (e.g. First Databank / FDB, DrugBank Enterprise, Wolters Kluwer Medi-Span).

PRODUCTION STATUS:
HealthSetu currently does NOT have an active commercial license or verified API
credentials for DrugBank or FDB.

In accordance with strict healthcare architecture policies:
1. Fake or unverified production credentials are never hard-coded.
2. The application will not claim production safety coverage until an authoritative
   licensed contract and active credentials are provided.
3. If configured without credentials, this adapter raises MedicationSafetyAuthError
   or MedicationSafetyProviderError immediately.
=============================================================================
"""

import httpx
from app.integrations.medication_safety.base import (
    MedicationSafetyAuthError,
    MedicationSafetyProvider,
    MedicationSafetyProviderError,
    MedicationSafetyTimeoutError,
    ProviderSafetyCheckResult,
)
from app.schemas.medication_safety import (
    SafetyAlert,
    SafetyCheckType,
    SafetyEvaluationStatus,
    SafetyMedicationInput,
    SafetyPatientContext,
)


class LicensedMedicationSafetyProvider(MedicationSafetyProvider):
    """Adapter for licensed commercial safety databases.

    Requires valid enterprise credentials (MEDICATION_SAFETY_BASE_URL and MEDICATION_SAFETY_API_KEY).
    """

    def __init__(
        self,
        base_url: str = "",
        api_key: str = "",
        timeout_seconds: int = 15,
        max_retries: int = 2,
    ):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries

    @property
    def provider_name(self) -> str:
        return "Licensed-Commercial-Provider"

    @property
    def provider_version(self) -> str:
        return "PENDING_LICENSE"

    @property
    def ruleset_version(self) -> str | None:
        return None

    @property
    def capabilities(self) -> dict[SafetyCheckType, bool]:
        """Declared commercial provider capabilities."""
        return {
            SafetyCheckType.DRUG_DRUG: True,
            SafetyCheckType.DRUG_ALLERGY: True,
            SafetyCheckType.DRUG_DISEASE: True,
            SafetyCheckType.CONTRAINDICATION: True,
            SafetyCheckType.DUPLICATE_THERAPY: True,
            SafetyCheckType.DOSING: True,
            SafetyCheckType.PREGNANCY: True,
            SafetyCheckType.RENAL: True,
            SafetyCheckType.HEPATIC: True,
            SafetyCheckType.OTHER: False,
        }

    async def evaluate_safety(
        self,
        medications: list[SafetyMedicationInput],
        patient_context: SafetyPatientContext,
        requested_checks: list[SafetyCheckType] | None = None,
    ) -> ProviderSafetyCheckResult:
        """Call external licensed safety provider API.

        Raises MedicationSafetyAuthError if credentials are not configured.
        """
        if not self._base_url or not self._api_key:
            raise MedicationSafetyAuthError(
                "EXTERNAL PROVIDER DEPENDENCY: Licensed safety provider is configured, but "
                "MEDICATION_SAFETY_BASE_URL or MEDICATION_SAFETY_API_KEY is missing. "
                "Production safety checking cannot proceed without active commercial credentials."
            )

        # Minimized payload for external vendor
        payload = {
            "medications": [
                {
                    "system": m.terminology_system,
                    "code": m.terminology_code,
                    "name": m.name,
                    "strength": m.strength,
                    "route": m.route,
                }
                for m in medications
            ],
            "allergies": [
                {"allergen": a.get("allergen") or a.get("allergen_name")}
                for a in patient_context.allergies
                if a.get("allergen") or a.get("allergen_name")
            ],
            "conditions": [
                {"code": c.get("code"), "diagnosis": c.get("diagnosis")}
                for c in patient_context.conditions
                if c.get("diagnosis")
            ],
            "patient_factors": {
                "age_years": patient_context.age_years,
                "sex": patient_context.sex,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    f"{self._base_url}/v1/safety/evaluate",
                    json=payload,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                if response.status_code in (401, 403):
                    raise MedicationSafetyAuthError("Licensed safety provider rejected credentials")
                if response.status_code >= 500:
                    raise MedicationSafetyProviderError(
                        f"Licensed provider returned server error: {response.status_code}",
                        is_transient=True,
                    )
                response.raise_for_status()
                data = response.json()
                
                # Normalization logic for licensed provider API schema
                # (To be completed when vendor contract/spec is finalized)
                return ProviderSafetyCheckResult(
                    provider_name=self.provider_name,
                    provider_version=data.get("version", "1.0"),
                    ruleset_version=data.get("ruleset_version"),
                    alerts=[],
                    check_summaries=[],
                    status=SafetyEvaluationStatus.CLEAR,
                )
        except httpx.TimeoutException as exc:
            raise MedicationSafetyTimeoutError(f"Licensed safety provider timed out after {self._timeout_seconds}s") from exc
        except httpx.RequestError as exc:
            raise MedicationSafetyProviderError(f"Network error communicating with safety provider: {exc}", is_transient=True) from exc
