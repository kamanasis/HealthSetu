"""Prompt template for Patient-Friendly Explanation & Simplification (Phase 14).

Task: PATIENT_EXPLANATION
Version: 1.0.0
"""

VERSION = "1.0.0"

SYSTEM_INSTRUCTION = """You are HealthSetu's Patient Explanation Assistant.
Your goal is to translate complex clinical terminology and doctor instructions into clear, empathetic, 6th-grade reading level explanations for patients and caregivers.

CRITICAL CLINICAL SAFETY RULES:
1. Do NOT give medical advice or suggest changing prescribed dosages or stopping medicines.
2. Emphasize that the patient must consult their treating physician with any medical questions.
3. Define jargon in simple terms.
4. Keep action items strictly faithful to what the clinician originally specified.
"""

TASK_TEMPLATE = """TASK: Explain the clinical text below in clear, accessible plain language.

TARGET READING LEVEL: {reading_level}
TARGET LANGUAGE: {language}

OUTPUT SPECIFICATION:
Provide a JSON object adhering to this schema:
{{
  "simplified_explanation": string,
  "reading_level": string,
  "action_items": [string],
  "questions_to_ask_doctor": [string],
  "medical_terms_glossary": {{"term": "plain_language_definition"}},
  "source_citations": [
    {{"source_type": "clinical_text", "source_id": "input", "text_span": string, "field_name": string}}
  ],
  "uncertainties": [string],
  "missing_information": [string],
  "confidence_level": "HIGH" | "MEDIUM" | "LOW"
}}

<<<SOURCE_START>>>
{source_text}
<<<SOURCE_END>>>
"""


def build_explanation_prompt(
    source_text: str,
    reading_level: str = "Grade 6",
    language: str = "English",
) -> tuple[str, str, str]:
    """Generate system and user prompts for patient explanation."""
    user_prompt = TASK_TEMPLATE.format(
        reading_level=reading_level,
        language=language,
        source_text=source_text,
    )
    return SYSTEM_INSTRUCTION.strip(), user_prompt.strip(), VERSION

