"""Pydantic schemas for Phase 10 — Doctor Clinical Workflow.

Covers:
- ClinicalNote: clinician-authored structured notes (SOAP, Progress, etc.)
- ClinicalAssessment: clinician-authored diagnostic assessments
- ClinicalPlan: clinician-authored treatment/management plans
- ClinicalWorkspace: consolidated read-only view for a clinician session

SECURITY:
- clinician_id is ALWAYS sourced from the server-side JWT (never from client payload).
- Schemas intentionally omit clinician_id from all Create/Update models.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
import uuid


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ClinicalNoteType(str, Enum):
    """Supported clinical note types."""

    SOAP = "SOAP"
    PROGRESS = "PROGRESS"
    CONSULTATION = "CONSULTATION"
    DISCHARGE = "DISCHARGE"
    REFERRAL = "REFERRAL"
    PROCEDURE = "PROCEDURE"
    OTHER = "OTHER"


class ClinicalAssessmentType(str, Enum):
    """Supported clinical assessment types."""

    DIAGNOSIS = "DIAGNOSIS"
    DIFFERENTIAL = "DIFFERENTIAL"
    FUNCTIONAL = "FUNCTIONAL"
    RISK = "RISK"
    PROGNOSIS = "PROGNOSIS"
    OTHER = "OTHER"


class AssessmentConfidence(str, Enum):
    """Clinician confidence level for an assessment."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ClinicalPlanType(str, Enum):
    """Supported clinical plan types."""

    TREATMENT = "TREATMENT"
    MANAGEMENT = "MANAGEMENT"
    DIAGNOSTIC = "DIAGNOSTIC"
    PREVENTIVE = "PREVENTIVE"
    PALLIATIVE = "PALLIATIVE"
    OTHER = "OTHER"


class ClinicalPlanStatus(str, Enum):
    """Lifecycle status of a clinical plan."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# ---------------------------------------------------------------------------
# Clinical Note schemas
# ---------------------------------------------------------------------------

class ClinicalNoteCreate(BaseModel):
    """Input payload for creating a new clinical note.

    NOTE: clinician_id is intentionally absent — it is sourced from the
    authenticated JWT on the server side, never from the client payload.
    """

    model_config = ConfigDict(extra="forbid")

    note_type: ClinicalNoteType = Field(description="Category of clinical note")
    title: str = Field(..., min_length=1, max_length=200, description="Short descriptive title")
    content: str = Field(..., min_length=1, description="Full clinical note content")
    encounter_id: str | None = Field(default=None, description="Optional encounter reference")
    is_addendum: bool = Field(default=False, description="Whether this note is an addendum")
    parent_note_id: str | None = Field(
        default=None,
        description="If addendum, the ID of the parent note being amended",
    )


class ClinicalNoteUpdate(BaseModel):
    """Update payload for a clinical note (only unsigned notes may be updated)."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1)
    expected_version: int = Field(
        ...,
        description="Current version for optimistic concurrency control",
    )


class ClinicalNoteSign(BaseModel):
    """Request to sign/lock a clinical note."""

    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(
        ...,
        description="Current version for optimistic concurrency control",
    )


class ClinicalNoteRecord(BaseModel):
    """Complete persisted clinical note record (internal domain model)."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    encounter_id: str | None = None
    clinician_id: str = Field(description="Sourced from server-side JWT; never from client")
    note_type: ClinicalNoteType
    title: str
    content: str
    is_signed: bool = False
    signed_at: datetime | None = None
    is_addendum: bool = False
    parent_note_id: str | None = None
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ClinicalNoteResponse(BaseModel):
    """API response for a clinical note."""

    note_id: str
    patient_id: str
    encounter_id: str | None = None
    clinician_id: str
    note_type: ClinicalNoteType
    title: str
    content: str
    is_signed: bool
    signed_at: datetime | None = None
    is_addendum: bool
    parent_note_id: str | None = None
    version: int
    created_at: datetime
    updated_at: datetime


class ClinicalNoteListResponse(BaseModel):
    """Paginated list of clinical notes."""

    items: list[ClinicalNoteResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Clinical Assessment schemas
# ---------------------------------------------------------------------------

class ClinicalFinding(BaseModel):
    """A single structured clinical finding entry."""

    system: str = Field(description="Body system or domain (e.g., 'Cardiovascular', 'Neurological')")
    finding: str = Field(description="Clinical finding description")
    is_normal: bool = Field(default=True, description="Whether the finding is within normal limits")


class ClinicalAssessmentCreate(BaseModel):
    """Input payload for creating a new clinical assessment.

    NOTE: clinician_id is intentionally absent — sourced from JWT.
    """

    model_config = ConfigDict(extra="forbid")

    assessment_type: ClinicalAssessmentType
    title: str = Field(..., min_length=1, max_length=200)
    summary: str = Field(..., min_length=1, description="Clinician's overall assessment narrative")
    findings: list[ClinicalFinding] = Field(default_factory=list)
    icd_codes: list[str] = Field(default_factory=list, description="ICD-10/11 codes")
    severity: str | None = Field(default=None, max_length=50)
    confidence: AssessmentConfidence | None = None
    encounter_id: str | None = None


class ClinicalAssessmentUpdate(BaseModel):
    """Update payload for a clinical assessment (only non-finalized)."""

    model_config = ConfigDict(extra="forbid")

    summary: str | None = Field(default=None, min_length=1)
    findings: list[ClinicalFinding] | None = None
    icd_codes: list[str] | None = None
    severity: str | None = None
    confidence: AssessmentConfidence | None = None
    expected_version: int = Field(..., description="Optimistic concurrency version")


class ClinicalAssessmentFinalize(BaseModel):
    """Request to finalize/lock a clinical assessment."""

    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(..., description="Optimistic concurrency version")


class ClinicalAssessmentRecord(BaseModel):
    """Complete persisted clinical assessment record (internal domain model)."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    encounter_id: str | None = None
    clinician_id: str
    assessment_type: ClinicalAssessmentType
    title: str
    summary: str
    findings: list[ClinicalFinding] = Field(default_factory=list)
    icd_codes: list[str] = Field(default_factory=list)
    severity: str | None = None
    confidence: AssessmentConfidence | None = None
    is_finalized: bool = False
    finalized_at: datetime | None = None
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ClinicalAssessmentResponse(BaseModel):
    """API response for a clinical assessment."""

    assessment_id: str
    patient_id: str
    encounter_id: str | None = None
    clinician_id: str
    assessment_type: ClinicalAssessmentType
    title: str
    summary: str
    findings: list[ClinicalFinding]
    icd_codes: list[str]
    severity: str | None = None
    confidence: AssessmentConfidence | None = None
    is_finalized: bool
    finalized_at: datetime | None = None
    version: int
    created_at: datetime
    updated_at: datetime


class ClinicalAssessmentListResponse(BaseModel):
    """Paginated list of clinical assessments."""

    items: list[ClinicalAssessmentResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Clinical Plan schemas
# ---------------------------------------------------------------------------

class ClinicalIntervention(BaseModel):
    """A single planned clinical intervention."""

    category: str = Field(description="Category e.g. 'Pharmacological', 'Procedural', 'Lifestyle'")
    description: str = Field(description="Detailed intervention description")
    priority: str = Field(default="ROUTINE", description="URGENT, HIGH, ROUTINE, LOW")


class ClinicalPlanCreate(BaseModel):
    """Input payload for creating a new clinical plan.

    NOTE: clinician_id is intentionally absent — sourced from JWT.
    """

    model_config = ConfigDict(extra="forbid")

    plan_type: ClinicalPlanType
    title: str = Field(..., min_length=1, max_length=200)
    objectives: list[str] = Field(default_factory=list, description="Ordered clinical objectives")
    interventions: list[ClinicalIntervention] = Field(default_factory=list)
    investigations: list[str] = Field(default_factory=list, description="Ordered diagnostics/labs")
    follow_up_instructions: str | None = None
    status: ClinicalPlanStatus = ClinicalPlanStatus.ACTIVE
    encounter_id: str | None = None


class ClinicalPlanUpdate(BaseModel):
    """Update payload for a clinical plan (non-finalized only)."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    objectives: list[str] | None = None
    interventions: list[ClinicalIntervention] | None = None
    investigations: list[str] | None = None
    follow_up_instructions: str | None = None
    status: ClinicalPlanStatus | None = None
    expected_version: int = Field(..., description="Optimistic concurrency version")


class ClinicalPlanFinalize(BaseModel):
    """Request to finalize/lock a clinical plan."""

    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(..., description="Optimistic concurrency version")


class ClinicalPlanRecord(BaseModel):
    """Complete persisted clinical plan record (internal domain model)."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    encounter_id: str | None = None
    clinician_id: str
    plan_type: ClinicalPlanType
    title: str
    objectives: list[str] = Field(default_factory=list)
    interventions: list[ClinicalIntervention] = Field(default_factory=list)
    investigations: list[str] = Field(default_factory=list)
    follow_up_instructions: str | None = None
    status: ClinicalPlanStatus = ClinicalPlanStatus.ACTIVE
    is_finalized: bool = False
    finalized_at: datetime | None = None
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ClinicalPlanResponse(BaseModel):
    """API response for a clinical plan."""

    plan_id: str
    patient_id: str
    encounter_id: str | None = None
    clinician_id: str
    plan_type: ClinicalPlanType
    title: str
    objectives: list[str]
    interventions: list[ClinicalIntervention]
    investigations: list[str]
    follow_up_instructions: str | None = None
    status: ClinicalPlanStatus
    is_finalized: bool
    finalized_at: datetime | None = None
    version: int
    created_at: datetime
    updated_at: datetime


class ClinicalPlanListResponse(BaseModel):
    """Paginated list of clinical plans."""

    items: list[ClinicalPlanResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Clinical Workspace (consolidated view)
# ---------------------------------------------------------------------------

class WorkspacePatientSummary(BaseModel):
    """Minimal patient identity in the workspace."""

    patient_id: str
    first_name: str
    last_name: str
    date_of_birth: Any | None = None
    sex: str | None = None
    preferred_language: str | None = None


class WorkspaceSummary(BaseModel):
    """Domain section count summary for clinician workspace."""

    total_history_entries: int = 0
    total_allergies: int = 0
    total_vitals_entries: int = 0
    total_encounters: int = 0
    total_documents: int = 0
    total_prescriptions: int = 0
    total_active_medications: int = 0
    total_safety_results: int = 0
    total_symptom_intakes: int = 0
    total_triage_assessments: int = 0
    total_sbar_records: int = 0
    total_discharge_summaries: int = 0
    total_care_plans: int = 0
    total_clinical_notes: int = 0
    total_clinical_assessments: int = 0
    total_clinical_plans: int = 0


class ClinicalWorkspaceResponse(BaseModel):
    """Consolidated read-only clinical workspace view for an authorized clinician.

    Aggregates all domain data for an authorized patient/encounter.
    This is the primary clinician entry point for a patient's full clinical picture.
    """

    patient: WorkspacePatientSummary
    encounter_id: str | None = None
    summary: WorkspaceSummary
    recent_notes: list[ClinicalNoteResponse] = Field(default_factory=list)
    recent_assessments: list[ClinicalAssessmentResponse] = Field(default_factory=list)
    active_plans: list[ClinicalPlanResponse] = Field(default_factory=list)
    workspace_generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    clinician_id: str = Field(description="Clinician who opened this workspace (from JWT)")
