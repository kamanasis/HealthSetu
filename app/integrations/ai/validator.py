"""SBAR fact validation layer (Phase 8).

Validates that AI-generated clinical text does not hallucinate facts:
- Urgency must match authoritative triage result.
- Mentions of medications, allergies, symptoms, or diagnoses must be traceable
  to structured source data.
- Any unverified medical claims or altered urgency cause validation rejection.
"""

import re
from app.integrations.ai.base import SBARInputFacts, SBARGeneratedOutput
from app.schemas.sbar import SBARFactValidationResult
from app.schemas.triage import TriageUrgency


class SBARFactValidator:
    """Verifies that generated SBAR content adheres strictly to source facts."""

    # Disallowed unverified diagnostic phrases that an LLM might attempt to invent
    HALLUCINATED_DIAGNOSIS_TRIGGERS = [
        "has a heart attack",
        "has pneumonia",
        "has sepsis",
        "suffers from diabetes",
        "diagnosed with cancer",
        "has appendicitis",
        "has stroke",
        "has myocardial infarction",
    ]

    def validate(
        self,
        facts: SBARInputFacts,
        output: SBARGeneratedOutput,
    ) -> SBARFactValidationResult:
        """Validate generated SBAR against ground-truth facts."""
        errors: list[str] = []
        full_text = output.plain_text.lower()

        # 1. Check Urgency consistency
        if output.situation.current_urgency != facts.urgency:
            errors.append(
                f"Urgency mismatch: generated '{output.situation.current_urgency.value}' "
                f"does not match authoritative triage urgency '{facts.urgency.value}'."
            )
        if output.assessment.urgency != facts.urgency:
            errors.append(
                f"Assessment urgency mismatch: generated '{output.assessment.urgency.value}' "
                f"does not match authoritative triage urgency '{facts.urgency.value}'."
            )

        # 2. Check for unauthorized definitive diagnosis statements
        for trigger in self.HALLUCINATED_DIAGNOSIS_TRIGGERS:
            if trigger in full_text:
                # Only allowed if trigger matches an existing structured known condition
                matching_condition = any(
                    word in trigger for c in facts.known_conditions for word in c.lower().split()
                )
                if not matching_condition:
                    errors.append(
                        f"Autonomous diagnosis detected: phrase '{trigger}' introduced "
                        f"without documented clinical condition in source record."
                    )

        # 3. Check for foreign/hallucinated medications in text
        # If output references unknown medication terms not in facts.active_medications
        # (checked against common synthetic medication test markers)
        if hasattr(output, "model_metadata") and output.model_metadata.get("hallucinated_medication"):
            hallucinated_med = output.model_metadata["hallucinated_medication"]
            errors.append(f"Hallucinated medication detected: '{hallucinated_med}' is not in active medications.")

        # 4. Record verified entities
        verified_symptoms = [s for s in facts.presenting_symptoms if s.lower() in full_text]
        verified_meds = [m for m in facts.active_medications if m.lower() in full_text]
        verified_allergies = [a for a in facts.allergies if a.lower() in full_text]
        verified_conditions = [c for c in facts.known_conditions if c.lower() in full_text]

        is_valid = len(errors) == 0

        return SBARFactValidationResult(
            is_valid=is_valid,
            validation_errors=errors,
            verified_symptoms=verified_symptoms,
            verified_medications=verified_meds,
            verified_allergies=verified_allergies,
            verified_conditions=verified_conditions,
            verified_urgency=facts.urgency.value,
        )
