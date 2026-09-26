"""Prompt template for Clinician Documentation Assistance (Phase 14).

Task: CLINICAL_NOTE_DRAFT
Version: 1.0.0
"""

VERSION = "1.0.0"

SYSTEM_INSTRUCTION = """You are HealthSetu's Clinician Documentation Drafting Assistant.
Your task is to draft a professional, standard SOAP note draft based exclusively on the clinician's notes, observations, and exam findings.

CRITICAL CLINICAL SAFETY RULES:
1. You provide a DRAFT only. The clinician must explicitly sign and authenticate the final note.
2. Do not invent lab results, physical exam findings, or differential diagnoses not provided.
3. Clearly delineate Subjective, Objective, Assessment, and Plan components.
"""

TASK_TEMPLATE = """TASK: Structure the encounter observations into a standardized SOAP note draft.

OUTPUT SPECIFICATION:
Provide a JSON object adhering to this schema:
{{
  "subjective": string,
  "objective": string,
  "assessment": string,
  "plan": string,
  "full_draft_text": string,
  "source_citations": [
    {{"source_type": "encounter_context", "source_id": "{encounter_id}", "text_span": string, "field_name": string}}
  ],
  "uncertainties": [string],
  "missing_information": [string],
  "confidence_level": "HIGH" | "MEDIUM" | "LOW"
}}

PATIENT ID: {patient_id}
ENCOUNTER ID: {encounter_id}

<<<SOURCE_START>>>
CHIEF COMPLAINT: {chief_complaint}
HISTORY OF PRESENT ILLNESS: {history_of_present_illness}
PHYSICAL EXAM: {physical_exam_findings}
CLINICIAN IMPRESSIONS: {clinician_impressions}
<<<SOURCE_END>>>
"""


def build_clinical_documentation_prompt(
    source_text: str,
    encounter_type: str = "outpatient",
    patient_id: str = "patient_unknown",
    encounter_id: str = "enc_unknown",
) -> tuple[str, str, str]:
    """Generate system and user prompts for clinical documentation drafting."""
    user_prompt = TASK_TEMPLATE.format(
        patient_id=patient_id,
        encounter_id=encounter_id,
        chief_complaint=source_text,
        history_of_present_illness=f"Encounter Type: {encounter_type}",
        physical_exam_findings="See clinical notes",
        clinician_impressions=source_text,
    )
    return SYSTEM_INSTRUCTION.strip(), user_prompt.strip(), VERSION

