"""AI Output Validation and Grounding Service.

Validates that AI output complies with HealthSetu safety constraints, schema definitions,
and source document grounding boundaries.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Type
from pydantic import BaseModel

from app.core.config import settings
from app.core.exceptions import (
    AIGroundingFailedException,
    AIOutputInvalidException,
    AIOutputSchemaInvalidException,
)
from app.integrations.ai.validators import AIOutputValidator
from app.schemas.ai import AIGroundingStatus, AISourceReference, AITaskType

logger = logging.getLogger(__name__)


class AIValidationService:
    """Validates schemas, source grounding, and clinical safety boundaries on AI outputs."""

    def __init__(self, grounding_enabled: Optional[bool] = None) -> None:
        self.grounding_enabled = (
            grounding_enabled if grounding_enabled is not None else settings.AI_GROUNDING_VALIDATION_ENABLED
        )

    def validate_schema(
        self,
        raw_text: str,
        target_schema: Type[BaseModel],
    ) -> BaseModel:
        """Parse and validate that raw AI response conforms to target Pydantic schema."""
        return AIOutputValidator.validate_schema(raw_text, target_schema)

    def validate_grounding(
        self,
        parsed_output: Dict[str, Any],
        source_text: str,
        task_type: AITaskType,
    ) -> Tuple[AIGroundingStatus, List[str]]:
        """Verify that AI-generated claims and extracted fields are grounded in the source text.
        
        Returns:
            Tuple of (AIGroundingStatus, list_of_unsupported_claims)
        """
        if not self.grounding_enabled:
            return AIGroundingStatus.GROUNDED, []

        source_lower = (source_text or "").lower()
        unsupported_claims: List[str] = []

        # Check explicit source references / citations if present
        source_refs = parsed_output.get("source_citations", []) or parsed_output.get("source_references", [])
        for ref in source_refs:
            text_span = ref.get("text_span") if isinstance(ref, dict) else getattr(ref, "text_span", None)
            if text_span:
                # Normalize whitespace
                norm_span = " ".join(text_span.lower().split())
                norm_source = " ".join(source_lower.split())
                if norm_span and norm_span not in norm_source:
                    unsupported_claims.append(f"Citation text span '{text_span[:50]}...' not found in source text.")

        # Check extracted facts for document extraction
        if task_type == AITaskType.DOCUMENT_EXTRACTION:
            facts = parsed_output.get("extracted_facts", [])
            for fact in facts:
                val = fact.get("value") if isinstance(fact, dict) else getattr(fact, "value", None)
                if val and isinstance(val, str):
                    # Check for words from val in source
                    words = [w for w in val.lower().split() if len(w) > 4]
                    if words and not any(w in source_lower for w in words):
                        unsupported_claims.append(f"Extracted fact '{val[:50]}' lacks groundings in source document.")

        # Check key findings for clinical summary tasks
        GENERIC_STOPWORDS = {"patient", "doctor", "history", "hospital", "clinic", "reported", "recorded", "presents", "presented", "during"}
        if task_type in (AITaskType.CLINICAL_SUMMARY, AITaskType.DOCUMENT_SUMMARIZATION):
            for finding in parsed_output.get("key_findings", []):
                substantive_words = [
                    w for w in re.findall(r"[a-zA-Z]+", finding.lower())
                    if len(w) > 3 and w not in GENERIC_STOPWORDS
                ]
                if substantive_words:
                    unmatched = [w for w in substantive_words if w not in source_lower]
                    if len(unmatched) / len(substantive_words) > 0.5:
                        unsupported_claims.append(f"Summary finding '{finding[:50]}' lacks grounding in source records.")



        # Safety check: look for overt clinical hallucinations or diagnostic overreach
        hallucination_indicators = [
            "definitive diagnosis:",
            "prescribing medication",
            "order discontinued immediately",
            "autonomous triage decision",
        ]
        text_dump = str(parsed_output).lower()
        for indicator in hallucination_indicators:
            if indicator in text_dump and indicator not in source_lower:
                unsupported_claims.append(f"AI output contains prohibited autonomous clinical statement: '{indicator}'")

        if unsupported_claims:
            logger.warning(
                "Grounding validation detected %d unsupported claims: %s",
                len(unsupported_claims),
                unsupported_claims[:3],
            )
            return AIGroundingStatus.UNSUPPORTED_CONTENT, unsupported_claims

        return AIGroundingStatus.GROUNDED, []

    def enforce_safety_boundaries(self, parsed_output: Dict[str, Any]) -> None:
        """Ensure AI did not attempt to self-verify or create authoritative clinical prescriptions."""
        if parsed_output.get("verification_status") in ("VERIFIED", "APPROVED"):
            raise AIOutputInvalidException(
                "Safety violation: AI output attempted to self-assign VERIFIED status."
            )
        if "prescribe_now" in str(parsed_output).lower():
            raise AIOutputInvalidException(
                "Safety violation: AI output attempted autonomous prescribing."
            )
