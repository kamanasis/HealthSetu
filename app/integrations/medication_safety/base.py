"""Base interface and types for Medication Safety Providers.

IMPORTANT CLINICAL & INTEGRATION BOUNDARIES:
- Safety providers supply clinical safety evidence (DDIs, allergy conflicts, etc.).
- The system must NOT treat RxNorm or openFDA alone as complete safety engines.
- Commercial providers (DrugBank, FDB) require active licensing; this interface abstracts them.
- Any provider failure must result in UNKNOWN/ERROR, NEVER a false CLEAR.
"""

from abc import ABC, abstractmethod
from typing import Any
from app.schemas.medication_safety import (
    CheckTypeSummary,
    SafetyAlert,
    SafetyCheckType,
    SafetyEvaluationStatus,
    SafetyMedicationInput,
    SafetyPatientContext,
)


class MedicationSafetyProviderError(Exception):
    """Base exception for medication safety provider errors."""
    def __init__(self, message: str, is_transient: bool = False, error_code: str = "MEDICATION_SAFETY_PROVIDER_ERROR"):
        super().__init__(message)
        self.message = message
        self.is_transient = is_transient
        self.error_code = error_code


class MedicationSafetyTimeoutError(MedicationSafetyProviderError):
    """Raised when safety provider call exceeds configured timeout."""
    def __init__(self, message: str = "Medication safety provider timed out"):
        super().__init__(message, is_transient=True, error_code="MEDICATION_SAFETY_PROVIDER_TIMEOUT")


class MedicationSafetyAuthError(MedicationSafetyProviderError):
    """Raised when authentication with safety provider fails."""
    def __init__(self, message: str = "Medication safety provider authentication failed"):
        super().__init__(message, is_transient=False, error_code="MEDICATION_SAFETY_PROVIDER_AUTH_ERROR")


class MedicationSafetyUnsupportedError(MedicationSafetyProviderError):
    """Raised when requested check is unsupported by provider."""
    def __init__(self, message: str = "Requested check type is unsupported by safety provider"):
        super().__init__(message, is_transient=False, error_code="MEDICATION_SAFETY_UNSUPPORTED")


class ProviderSafetyCheckResult:
    """Internal normalized result returned by a safety provider adapter."""

    def __init__(
        self,
        provider_name: str,
        provider_version: str,
        ruleset_version: str | None,
        alerts: list[SafetyAlert],
        check_summaries: list[CheckTypeSummary],
        status: SafetyEvaluationStatus,
    ):
        self.provider_name = provider_name
        self.provider_version = provider_version
        self.ruleset_version = ruleset_version
        self.alerts = alerts
        self.check_summaries = check_summaries
        self.status = status


class MedicationSafetyProvider(ABC):
    """Abstract Base Class for Medication Safety Providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the safety provider."""
        ...

    @property
    @abstractmethod
    def provider_version(self) -> str:
        """Version of the safety provider."""
        ...

    @property
    @abstractmethod
    def ruleset_version(self) -> str | None:
        """Clinical ruleset / monograph version, if available."""
        ...

    @property
    @abstractmethod
    def capabilities(self) -> dict[SafetyCheckType, bool]:
        """Declared capabilities of this provider."""
        ...

    def is_check_supported(self, check_type: SafetyCheckType) -> bool:
        """Check whether this provider supports a given check type."""
        return self.capabilities.get(check_type, False)

    @abstractmethod
    async def evaluate_safety(
        self,
        medications: list[SafetyMedicationInput],
        patient_context: SafetyPatientContext,
        requested_checks: list[SafetyCheckType] | None = None,
    ) -> ProviderSafetyCheckResult:
        """Execute medication safety checks against the provider.

        Args:
            medications: Minimized normalized medication inputs.
            patient_context: Minimized clinical context (allergies, conditions, vitals).
            requested_checks: Optional subset of checks to evaluate.

        Returns:
            ProviderSafetyCheckResult with alerts, summaries, and status.

        Raises:
            MedicationSafetyTimeoutError: On request timeout.
            MedicationSafetyAuthError: On credential failure.
            MedicationSafetyProviderError: On upstream failure.
        """
        ...
