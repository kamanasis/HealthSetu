"""Mock / Configurable LLM Clinical Text Generator (Phase 8).

Demonstrates external AI provider integration for SBAR prose synthesis.
All calls pass structured facts, apply timeout and token limits, and are
subject to strict fact-checking by SBARFactValidator.
"""

from typing import Any
from app.integrations.ai.base import (
    ClinicalTextGenerator,
    SBARInputFacts,
    SBARGeneratedOutput,
)
from app.schemas.sbar import (
    SBARSituation,
    SBARBackground,
    SBARAssessment,
    SBARRecommendation,
)


class MockLLMClinicalTextGenerator(ClinicalTextGenerator):
    """Configurable AI provider adapter for testing and dev environments."""

    def __init__(
        self,
        provider_name: str = "mock_llm",
        simulate_hallucination: bool = False,
        simulate_urgency_override: bool = False,
    ):
        self._provider_name = provider_name
        self.simulate_hallucination = simulate_hallucination
        self.simulate_urgency_override = simulate_urgency_override

    @property
    def provider_name(self) -> str:
        return self._provider_name

    async def generate_sbar(self, facts: SBARInputFacts) -> SBARGeneratedOutput:
        """Synthesize clinical SBAR narrative from structured facts."""
        symptoms_str = ", ".join(facts.presenting_symptoms) if facts.presenting_symptoms else "none reported"
        
        # Simulated urgency override flaw (for negative testing)
        assigned_urgency = facts.urgency
        if self.simulate_urgency_override:
            # Flawed LLM tries to downgrade or alter urgency
            from app.schemas.triage import TriageUrgency
            assigned_urgency = TriageUrgency.ROUTINE if facts.urgency != TriageUrgency.ROUTINE else TriageUrgency.EMERGENCY

        situation_text = (
            f"Presenting reason: {facts.reason_for_attention}. "
            f"Patient reports symptoms of {symptoms_str}. "
            f"Urgency level: {assigned_urgency.value}."
        )

        situation = SBARSituation(
            reason_for_attention=facts.reason_for_attention,
            current_urgency=assigned_urgency,
            presenting_symptoms=facts.presenting_symptoms,
            summary_text=situation_text,
        )

        # Background
        cond_str = ", ".join(facts.known_conditions) if facts.known_conditions else "None documented"
        meds_str = ", ".join(facts.active_medications) if facts.active_medications else "None documented"
        allergies_str = ", ".join(facts.allergies) if facts.allergies else "No known drug allergies"

        hallucinated_phrase = ""
        metadata: dict[str, Any] = {"provider": self._provider_name, "model": "mock-clin-v1"}
        if self.simulate_hallucination:
            hallucinated_phrase = " Patient also has a heart attack and takes Morphine 50mg daily."
            metadata["hallucinated_medication"] = "Morphine"

        background_text = (
            f"Documented conditions: {cond_str}. "
            f"Active medications: {meds_str}. "
            f"Allergies: {allergies_str}.{hallucinated_phrase}"
        )
        background = SBARBackground(
            known_conditions=facts.known_conditions,
            active_medications=facts.active_medications,
            allergies=facts.allergies,
            recent_encounters=facts.recent_encounters,
            summary_text=background_text,
        )

        # Assessment
        rules_str = "; ".join(facts.triggered_rules) if facts.triggered_rules else "Triage protocol criteria met"
        assessment_text = (
            f"Triage classification: {assigned_urgency.value}. "
            f"Clinical protocol criteria: {rules_str}."
        )
        assessment = SBARAssessment(
            urgency=assigned_urgency,
            triggered_rules=facts.triggered_rules,
            evaluated_vitals=facts.vitals,
            summary_text=assessment_text,
        )

        # Recommendation
        imm = f" Immediate step: {facts.immediate_instruction}." if facts.immediate_instruction else ""
        recommendation_text = (
            f"Recommended level of care: {facts.recommended_level_of_care}.{imm} "
            f"Follow-up: {facts.follow_up_recommendation}."
        )
        recommendation = SBARRecommendation(
            recommended_level_of_care=facts.recommended_level_of_care,
            immediate_instruction=facts.immediate_instruction,
            missing_information=facts.missing_information,
            follow_up_recommendation=facts.follow_up_recommendation,
            summary_text=recommendation_text,
        )

        plain_text = (
            f"SBAR CLINICAL SUMMARY (AI ASSISTED)\n"
            f"====================================\n"
            f"[SITUATION]\n{situation_text}\n\n"
            f"[BACKGROUND]\n{background_text}\n\n"
            f"[ASSESSMENT]\n{assessment_text}\n\n"
            f"[RECOMMENDATION]\n{recommendation_text}\n"
        )

        return SBARGeneratedOutput(
            situation=situation,
            background=background,
            assessment=assessment,
            recommendation=recommendation,
            plain_text=plain_text,
            model_metadata=metadata,
        )
