"""AI & Intelligence Layer Core Schemas (Phase 14).

Defines fundamental enums, provider metadata, source citations,
and provenance tracking structures for the HealthSetu AI orchestration layer.

Architectural boundaries:
- AI layer is an orchestration and assistance layer.
- AI is NOT a clinical decision engine.
- AI output is NEVER authoritative clinical truth solely because an AI generated it.
- AI confidence is NOT clinical certainty.
- Explicit human clinician verification is required for clinical records.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AITaskType(str, Enum):
    """Approved, allowlisted AI tasks. Arbitrary prompt execution is strictly forbidden."""

    DOCUMENT_EXTRACTION = "DOCUMENT_EXTRACTION"
    DOCUMENT_SUMMARIZATION = "DOCUMENT_SUMMARIZATION"
    PATIENT_EXPLANATION = "PATIENT_EXPLANATION"
    SBAR_ASSISTANCE = "SBAR_ASSISTANCE"
    DISCHARGE_EXTRACTION = "DISCHARGE_EXTRACTION"
    CARE_PLAN_ORGANIZATION = "CARE_PLAN_ORGANIZATION"
    CLINICAL_NOTE_DRAFT = "CLINICAL_NOTE_DRAFT"
    CLINICAL_SUMMARY = "CLINICAL_SUMMARY"
    STRUCTURED_CLASSIFICATION = "STRUCTURED_CLASSIFICATION"


class AITaskStatus(str, Enum):
    """Lifecycle state machine for AI task execution."""

    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AIVerificationStatus(str, Enum):
    """Clinical verification status boundary for AI outputs."""

    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    VERIFIED = "VERIFIED"
    CORRECTED = "CORRECTED"
    REJECTED = "REJECTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AIGroundingStatus(str, Enum):
    """Evaluation of factual adherence to supplied source data."""

    GROUNDED = "GROUNDED"
    PARTIALLY_GROUNDED = "PARTIALLY_GROUNDED"
    UNSUPPORTED_CONTENT = "UNSUPPORTED_CONTENT"
    UNGROUNDED = "UNGROUNDED"
    SKIPPED = "SKIPPED"


class AIConfidenceLevel(str, Enum):
    """AI model/system confidence indicator. Never treated as clinical certainty."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class AIProviderName(str, Enum):
    """Supported AI provider adapter identifiers."""

    MOCK = "mock"
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"


# ---------------------------------------------------------------------------
# Source Citation & Evidence Grounding
# ---------------------------------------------------------------------------

class AISourceReference(BaseModel):
    """Traceable evidence pointer grounding an AI assertion to source facts."""

    model_config = ConfigDict(extra="ignore")

    field: str | None = Field(default=None, description="Field in output supported by this citation")
    text_span: str | None = Field(default=None, description="Exact substring or snippet from source")
    document_id: str | None = Field(default=None, description="Document ID if extracted from a document")
    page: int | None = Field(default=None, description="1-indexed page number if applicable")
    source_id: str | None = Field(default=None)


class AIGroundingEvaluation(BaseModel):
    """Grounding assessment comparing AI claims against source data."""

    status: AIGroundingStatus = Field(default=AIGroundingStatus.GROUNDED)
    grounded_fields: list[str] = Field(default_factory=list)
    ungrounded_claims: list[str] = Field(default_factory=list)
    grounding_score: float = Field(default=1.0, ge=0.0, le=1.0)
    evaluation_notes: str | None = None


# ---------------------------------------------------------------------------
# Provider & Model Metadata
# ---------------------------------------------------------------------------

class AIModelMetadata(BaseModel):
    """Metadata regarding the invoked model deployment."""

    provider_name: str
    model_name: str
    model_version: str | None = None
    temperature: float = 0.0
    max_tokens: int = 2000
    is_mock: bool = False


class AIUsageMetadata(BaseModel):
    """Operational token consumption and latency metrics. Excludes PHI."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    estimated_cost_usd: float | None = None
    request_id: str | None = None


# ---------------------------------------------------------------------------
# Provenance Record
# ---------------------------------------------------------------------------

class AIProvenanceRecord(BaseModel):
    """Immutable provenance chain linking source data, prompt, model, and result."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: f"aiprov-{uuid.uuid4().hex[:12]}")
    task_type: AITaskType
    task_version: str
    prompt_version: str
    provider: str
    model: str
    model_version: str
    source_content_hash: str = Field(description="SHA-256 hash of sanitized input")
    output_content_hash: str = Field(description="SHA-256 hash of structured output")
    citation_count: int = 0
    citations: list[AISourceReference] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
