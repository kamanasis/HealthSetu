"""Prompt template for SBAR Wording Assistance (Phase 14).

Task: SBAR_ASSISTANCE
Version: 1.0.0
"""

VERSION = "1.0.0"

SYSTEM_INSTRUCTION = """You are HealthSetu's SBAR Clinical Communication Assistant.
Your task is to draft professional, concise SBAR (Situation, Background, Assessment, Recommendation) wording for healthcare handoffs and escalations.

CRITICAL CLINICAL SAFETY RULES:
1. You assist with wording and phrasing only. You DO NOT assign or alter emergency triage urgency levels.
2. The Assessment section must clearly articulate the clinician's observation or primary concern grounded in the provided vitals and symptoms.
3. The Recommendation section must suggest appropriate structured communication requests (e.g. bedside evaluation), never unprescribed drugs.
"""

TASK_TEMPLATE = """TASK: Draft SBAR handoff wording using the clinical facts provided below.

PATIENT ID: {patient_id}

OUTPUT SPECIFICATION:
Provide a JSON object adhering to this schema:
{{
  "situation": string,
  "background": string,
  "assessment": string,
  "recommendation": string,
  "clinical_facts_used": [string],
  "source_citations": [
    {{"source_type": "clinical_facts", "source_id": "{patient_id}", "text_span": string, "field_name": string}}
  ],
  "uncertainties": [string],
  "missing_information": [string],
  "confidence_level": "HIGH" | "MEDIUM" | "LOW"
}}

<<<SOURCE_START>>>
SYMPTOMS: {symptom_summary}
VITALS: {vital_signs}
DIAGNOSES: {known_diagnoses}
ADDITIONAL CONTEXT: {context_notes}
<<<SOURCE_END>>>
"""


def build_sbar_prompt(
    situation_facts: str = "",
    background_facts: str = "",
    assessment_facts: str = "",
    recommendation_facts: str = "",
    patient_id: str = "patient_unknown",
    context_notes: str = "",
) -> tuple[str, str, str]:
    """Generate system and user prompts for SBAR communication assistance."""
    user_prompt = TASK_TEMPLATE.format(
        patient_id=patient_id,
        symptom_summary=situation_facts,
        vital_signs=background_facts,
        known_diagnoses=assessment_facts,
        context_notes=recommendation_facts or context_notes,
    )
    return SYSTEM_INSTRUCTION.strip(), user_prompt.strip(), VERSION

