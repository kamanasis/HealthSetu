"""Prompt template for Care Plan Organization (Phase 14).

Task: CARE_PLAN_ORGANIZATION
Version: 1.0.0
"""

VERSION = "1.0.0"

SYSTEM_INSTRUCTION = """You are HealthSetu's Care Plan Structuring Assistant.
Your task is to take clinician notes and patient goals and organize them into standardized SMART goals, interventions, and monitoring milestones.

CRITICAL CLINICAL SAFETY RULES:
1. Care plans are clinical tools that guide patient recovery. Never add unapproved medical interventions.
2. Structure existing clinician instructions without modifying clinical intent.
"""

TASK_TEMPLATE = """TASK: Structure the following clinician inputs into a standardized care plan structure.

OUTPUT SPECIFICATION:
Provide a JSON object adhering to this schema:
{{
  "patient_goals": [
    {{"title": string, "target_date": string or null, "metric": string, "status": "IN_PROGRESS"}}
  ],
  "planned_interventions": [
    {{"title": string, "description": string, "frequency": string, "assigned_role": string}}
  ],
  "monitoring_schedule": [
    {{"item": string, "frequency": string, "target_range": string or null}}
  ],
  "barriers_to_adherence": [string],
  "source_citations": [
    {{"source_type": "care_plan_draft", "source_id": "{patient_id}", "text_span": string, "field_name": string}}
  ],
  "uncertainties": [string],
  "missing_information": [string],
  "confidence_level": "HIGH" | "MEDIUM" | "LOW"
}}

PATIENT ID: {patient_id}

<<<SOURCE_START>>>
DIAGNOSES: {diagnoses}
RAW GOALS: {raw_goals}
RAW INTERVENTIONS: {raw_interventions}
<<<SOURCE_END>>>
"""


def build_care_plan_prompt(
    source_text: str,
    patient_id: str = "patient_unknown",
    diagnoses: str = "See source text",
    raw_goals: str = "",
    raw_interventions: str = "",
) -> tuple[str, str, str]:
    """Generate system and user prompts for care plan organization."""
    user_prompt = TASK_TEMPLATE.format(
        patient_id=patient_id,
        diagnoses=diagnoses,
        raw_goals=raw_goals or source_text,
        raw_interventions=raw_interventions or source_text,
    )
    return SYSTEM_INSTRUCTION.strip(), user_prompt.strip(), VERSION

