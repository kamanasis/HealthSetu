"""Pydantic schemas for Medication Safety System (Phase 7).

CRITICAL CLINICAL BOUNDARIES:
- Safety results represent provider-backed clinical evidence, NOT autonomous clinical decisions.
- Never assert that openFDA or RxNorm alone provide a complete interaction engine.
- LLMs are NOT authoritative safety engines.
- Provider failures NEVER become a false CLEAR status.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SafetyCheckType(str, Enum):
    """Types of medication safety checks."""
    DRUG_DRUG = "DRUG_DRUG"
    DRUG_ALLERGY = "DRUG_ALLERGY"
    DRUG_DISEASE = "DRUG_DISEASE"
    CONTRAINDICATION = "CONTRAINDICATION"
    DUPLICATE_THERAPY = "DUPLICATE_THERAPY"
    DOSING = "DOSING"
    PREGNANCY = "PREGNANCY"
    RENAL = "RENAL"
    HEPATIC = "HEPATIC"
    OTHER = "OTHER"


class SafetyAlertSeverity(str, Enum):
    """Clinical severity levels reported by authoritative safety providers."""
    CRITICAL = "CRITICAL"      # Life-threatening, absolute contraindication
    MAJOR = "MAJOR"            # Severe potential outcome, requires clinical intervention
    MODERATE = "MODERATE"      # Significant potential interaction or precaution
    MINOR = "MINOR"            # Mild, monitor or informational
    INFO = "INFO"              # Contextual clinical note


class SafetyEvaluationStatus(str, Enum):
    """Overall evaluation status for a safety check run."""
    CLEAR = "CLEAR"                            # Checks executed, no alerts detected
    ALERT = "ALERT"                            # At least one critical/major alert identified
    WARNING = "WARNING"                        # Moderate or minor warnings identified
    NOT_SUPPORTED = "NOT_SUPPORTED"            # One or more requested checks unsupported by provider
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"  # Required clinical context missing
    UNKNOWN = "UNKNOWN"                        # Provider error / unable to determine safety
    ERROR = "ERROR"                            # Execution failed


class MedicationContextSource(str, Enum):
    """Medication collection context for evaluation."""
    CURRENT_MEDICATIONS = "CURRENT_MEDICATIONS"          # Only currently active patient medications
    NEW_PRESCRIPTION = "NEW_PRESCRIPTION"                # Prospective new prescription check
    FULL_MEDICATION_REVIEW = "FULL_MEDICATION_REVIEW"    # Complete historical review


# ---------------------------------------------------------------------------
# Input Models
# ---------------------------------------------------------------------------

class SafetyMedicationInput(BaseModel):
    """Normalized medication input for safety evaluation."""
    model_config = ConfigDict(extra="ignore")

    medication_id: str | None = Field(default=None, description="Internal HealthSetu medication ID if recorded")
    name: str = Field(..., description="Medication name or generic active ingredient")
    terminology_system: str | None = Field(default=None, description="Coding system (e.g., 'RXNORM', 'SNOMED-CT')")
    terminology_code: str | None = Field(default=None, description="Normalized code (e.g. RxCUI)")
    strength: str | None = Field(default=None, description="Dosage strength (e.g., '500 mg')")
    dosage_form: str | None = Field(default=None, description="Form (e.g., 'tablet', 'solution')")
    route: str | None = Field(default=None, description="Administration route (e.g., 'oral', 'intravenous')")
    frequency: str | None = Field(default=None, description="Frequency (e.g., 'once daily')")
    duration: str | None = Field(default=None, description="Duration string")
    status: str | None = Field(default="ACTIVE", description="Medication status")


class SafetyPatientContext(BaseModel):
    """Minimized patient clinical context strictly necessary for safety checks."""
    model_config = ConfigDict(extra="ignore")

    allergies: list[dict[str, Any]] = Field(default_factory=list, description="Explicitly recorded active allergies")
    conditions: list[dict[str, Any]] = Field(default_factory=list, description="Explicitly recorded active conditions")
    vitals: list[dict[str, Any]] = Field(default_factory=list, description="Relevant vitals if required")
    age_years: int | None = Field(default=None, description="Age in years if required for dosing/pediatric rules")
    sex: str | None = Field(default=None, description="Biological sex if required for sex-specific contraindications")


class PatientSafetyCheckRequest(BaseModel):
    """Request to evaluate safety for a patient's active or selected medications."""
    model_config = ConfigDict(extra="ignore")

    medication_ids: list[str] | None = Field(
        default=None,
        description="Optional list of specific medication IDs to evaluate. If omitted, evaluates all active medications.",
    )
    medication_context: MedicationContextSource = Field(
        default=MedicationContextSource.CURRENT_MEDICATIONS,
        description="Medication evaluation context scope",
    )
    requested_check_types: list[SafetyCheckType] | None = Field(
        default=None,
        description="Specific safety check types requested. If omitted, all provider-supported checks run.",
    )


class ProspectiveMedicationsCheckRequest(BaseModel):
    """Request to evaluate prospective/new medications, optionally against existing active medications."""
    model_config = ConfigDict(extra="ignore")

    medications: list[SafetyMedicationInput] = Field(
        ...,
        min_length=1,
        description="Prospective medications to evaluate",
    )
    include_current_medications: bool = Field(
        default=True,
        description="Whether to check prospective medications against currently active patient medications",
    )
    requested_check_types: list[SafetyCheckType] | None = Field(
        default=None,
        description="Specific safety check types requested",
    )


# ---------------------------------------------------------------------------
# Output / Result Models
# ---------------------------------------------------------------------------

CLINICAL_SAFETY_DISCLAIMER = (
    "DISCLAIMER: Medication safety findings represent clinical evidence from configured "
    "terminology and safety providers. They do not constitute autonomous clinical decisions, "
    "prescriptions, or medical directives, and do not replace professional physician judgment."
)


class SafetyAlert(BaseModel):
    """A single normalized safety alert or finding from an authoritative provider."""
    model_config = ConfigDict(extra="ignore")

    alert_id: str = Field(..., description="Unique alert identifier")
    check_type: SafetyCheckType = Field(..., description="Type of check generating this alert")
    severity: SafetyAlertSeverity = Field(..., description="Alert severity level")
    title: str = Field(..., description="Short summary of the alert")
    description: str = Field(..., description="Factual clinical explanation from provider")
    medications_involved: list[dict[str, str]] = Field(
        default_factory=list,
        description="Medications involved in this alert (name, code, id)",
    )
    clinical_context_involved: list[dict[str, str]] = Field(
        default_factory=list,
        description="Allergy, condition, or other clinical context involved in the alert",
    )
    evidence: str | None = Field(default=None, description="Authoritative clinical evidence or literature citation")
    source: str = Field(..., description="Originating provider or database name")
    provider_rule_id: str | None = Field(default=None, description="Internal rule/monograph ID from provider")


class CheckTypeSummary(BaseModel):
    """Summary of a specific check type evaluation."""
    check_type: SafetyCheckType
    supported: bool
    status: SafetyEvaluationStatus
    alert_count: int = 0
    note: str | None = None


class SafetyEvaluationResponse(BaseModel):
    """Complete medication safety evaluation report."""
    model_config = ConfigDict(extra="ignore")

    evaluation_id: str = Field(..., description="Unique ID for this safety evaluation run")
    patient_id: str = Field(..., description="Patient ID")
    status: SafetyEvaluationStatus = Field(..., description="Overall evaluation status")
    medication_context: MedicationContextSource = Field(..., description="Context scope evaluated")
    checked_at: datetime = Field(..., description="UTC timestamp of evaluation")
    provider: str = Field(..., description="Safety provider name (e.g., 'mock', 'fdb', 'drugbank')")
    provider_version: str = Field(..., description="Provider API / database version")
    ruleset_version: str | None = Field(default=None, description="Provider clinical ruleset version")
    
    # Findings
    alerts: list[SafetyAlert] = Field(default_factory=list, description="All alerts identified")
    check_summaries: list[CheckTypeSummary] = Field(default_factory=list, description="Execution status per check type")
    
    # Provenance & Minimization Metadata
    medications_evaluated_count: int = Field(default=0, description="Number of medications analyzed")
    patient_context_used: dict[str, int] = Field(
        default_factory=dict,
        description="Counts of clinical context elements used (allergies, conditions) without exposing raw PHI",
    )
    
    # Clinical disclaimer
    disclaimer: str = Field(
        default=CLINICAL_SAFETY_DISCLAIMER,
        description="Mandatory clinical decision-support disclaimer",
    )


class SafetyEvaluationSummaryItem(BaseModel):
    """Summary item for listing historical evaluations."""
    model_config = ConfigDict(extra="ignore")

    evaluation_id: str
    patient_id: str
    status: SafetyEvaluationStatus
    medication_context: MedicationContextSource
    checked_at: datetime
    provider: str
    alert_count: int
    highest_severity: SafetyAlertSeverity | None = None


class SafetyEvaluationListResponse(BaseModel):
    """Paginated list of safety evaluations."""
    model_config = ConfigDict(extra="ignore")

    items: list[SafetyEvaluationSummaryItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class SafetyProviderCapabilities(BaseModel):
    """Metadata describing capabilities supported by the configured provider."""
    provider_name: str
    provider_version: str
    capabilities: dict[str, bool] = Field(
        description="Mapping of check type string to boolean capability status"
    )
