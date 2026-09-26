"""Prompt template for Discharge Instruction Organization (Phase 14).

Task: DISCHARGE_EXTRACTION
Version: 1.0.0
"""

VERSION = "1.0.0"

SYSTEM_INSTRUCTION = """You are HealthSetu's Discharge Instruction Organization Assistant.
Your task is to organize free-text discharge summaries into structured categories: medication changes, appointments, red flags, and restrictions.

CRITICAL CLINICAL SAFETY RULES:
1. NEVER invent discharge instructions, medication dosages, or warning symptoms not present in the text.
2. Emphasize red flag symptoms requiring immediate emergency care as written by the treating hospital.
3. Keep all medication guidance strictly identical to what the physician authorized.
"""

TASK_TEMPLATE = """TASK: Organize the discharge text into standardized clinical discharge instruction categories.

OUTPUT SPECIFICATION:
Provide a JSON object adhering to this schema:
{{
  "organized_instructions": [string],
  "medication_changes": [string],
  "follow_up_appointments": [string],
  "warning_signs_red_flags": [string],
  "activity_and_diet_restrictions": [string],
  "source_citations": [
    {{"source_type": "discharge_summary", "source_id": "input", "text_span": string, "field_name": string}}
  ],
  "uncertainties": [string],
  "missing_information": [string],
  "confidence_level": "HIGH" | "MEDIUM" | "LOW"
}}

<<<SOURCE_START>>>
ADMISSION DIAGNOSIS: {admission_diagnosis}
DISCHARGE TEXT:
{discharge_text}
DISCHARGE MEDICATIONS: {discharge_medications}
<<<SOURCE_END>>>
"""


def build_discharge_prompt(
    discharge_text: str,
    admission_diagnosis: str = "Unspecified",
    discharge_medications: str = "See discharge text",
) -> tuple[str, str, str]:
    """Generate system and user prompts for discharge instruction organization."""
    user_prompt = TASK_TEMPLATE.format(
        admission_diagnosis=admission_diagnosis,
        discharge_text=discharge_text,
        discharge_medications=discharge_medications,
    )
    return SYSTEM_INSTRUCTION.strip(), user_prompt.strip(), VERSION

