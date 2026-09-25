"""Deterministic template-based SBAR clinical summary generator (Phase 8).

Provides guaranteed fallback and zero-LLM operation without external API calls.
Clinical facts are formatted deterministically into Situation, Background,
Assessment, and Recommendation sections.
"""

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


class TemplateClinicalTextGenerator(ClinicalTextGenerator):
    """Deterministic SBAR generator using structured template composition."""

    @property
    def provider_name(self) -> str:
        return "template"

    async def generate_sbar(self, facts: SBARInputFacts) -> SBARGeneratedOutput:
        """Compose structured SBAR narrative deterministically from facts."""
        # Situation
        symptoms_str = ", ".join(facts.presenting_symptoms) if facts.presenting_symptoms else "None reported"
        situation_text = (
            f"Patient attention requested for: {facts.reason_for_attention}. "
            f"Presenting symptoms: {symptoms_str}. "
            f"Current clinical triage urgency: {facts.urgency.value}."
        )
        situation = SBARSituation(
            reason_for_attention=facts.reason_for_attention,
            current_urgency=facts.urgency,
            presenting_symptoms=facts.presenting_symptoms,
            summary_text=situation_text,
        )

        # Background
        cond_str = ", ".join(facts.known_conditions) if facts.known_conditions else "No documented conditions"
        meds_str = ", ".join(facts.active_medications) if facts.active_medications else "No active medications documented"
        allergies_str = ", ".join(facts.allergies) if facts.allergies else "No documented drug allergies (NKDA)"
        enc_str = ", ".join(facts.recent_encounters) if facts.recent_encounters else "No recent clinical encounters"

        background_text = (
            f"Documented conditions: {cond_str}. "
            f"Active medications: {meds_str}. "
            f"Allergies: {allergies_str}. "
            f"Recent encounters: {enc_str}."
        )
        background = SBARBackground(
            known_conditions=facts.known_conditions,
            active_medications=facts.active_medications,
            allergies=facts.allergies,
            recent_encounters=facts.recent_encounters,
            summary_text=background_text,
        )

        # Assessment
        rules_str = "; ".join(facts.triggered_rules) if facts.triggered_rules else "Routine protocol evaluation"
        vitals_str = ", ".join(f"{k}: {v}" for k, v in facts.vitals.items()) if facts.vitals else "None recorded"

        assessment_text = (
            f"Triage evaluation result: {facts.urgency.value}. "
            f"Triggered protocol criteria: {rules_str}. "
            f"Evaluated vitals: {vitals_str}."
        )
        assessment = SBARAssessment(
            urgency=facts.urgency,
            triggered_rules=facts.triggered_rules,
            evaluated_vitals=facts.vitals,
            summary_text=assessment_text,
        )

        # Recommendation
        missing_str = f" Required observations pending: {', '.join(facts.missing_information)}." if facts.missing_information else ""
        imm_str = f" Immediate action: {facts.immediate_instruction}." if facts.immediate_instruction else ""

        recommendation_text = (
            f"Recommended level of care: {facts.recommended_level_of_care}.{imm_str}{missing_str} "
            f"Follow-up: {facts.follow_up_recommendation}."
        )
        recommendation = SBARRecommendation(
            recommended_level_of_care=facts.recommended_level_of_care,
            immediate_instruction=facts.immediate_instruction,
            missing_information=facts.missing_information,
            follow_up_recommendation=facts.follow_up_recommendation,
            summary_text=recommendation_text,
        )

        # Formatted plain text
        plain_text = (
            f"SBAR CLINICAL SUMMARY\n"
            f"=====================\n"
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
            model_metadata={"provider": "template", "version": "1.0.0"},
        )
