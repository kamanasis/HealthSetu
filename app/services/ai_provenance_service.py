"""AI Provenance Tracking Service.

Tracks end-to-end lineage, source text hashes, citations, and version metadata for AI results.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List
from app.schemas.ai import AIProvenanceRecord, AISourceReference, AITaskType


class AIProvenanceService:
    """Computes cryptographic hashes and records audit provenance for AI outputs."""

    @staticmethod
    def compute_sha256(content: str) -> str:
        """Compute SHA-256 hash of a string."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def create_provenance_record(
        self,
        task_type: AITaskType,
        source_text: str,
        output_payload: Dict[str, Any],
        prompt_version: str,
        task_version: str,
        provider: str,
        model: str,
        model_version: str,
        citations: List[AISourceReference],
    ) -> AIProvenanceRecord:
        """Build a verifiable provenance record linking source context to generated result."""
        source_hash = self.compute_sha256(source_text)
        serialized_output = json.dumps(output_payload, sort_keys=True)
        output_hash = self.compute_sha256(serialized_output)

        return AIProvenanceRecord(
            task_type=task_type,
            task_version=task_version,
            prompt_version=prompt_version,
            provider=provider,
            model=model,
            model_version=model_version,
            source_content_hash=source_hash,
            output_content_hash=output_hash,
            citation_count=len(citations),
            citations=citations,
        )
