"""Deterministic Mock AI Provider for robust testing and offline development."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel

from app.core.exceptions import (
    AIGroundingFailedException,
    AIOutputInvalidException,
    AIOutputSchemaInvalidException,
    AIProviderTimeoutException,
    AIProviderUnavailableException,
)
from app.integrations.ai.base import AIProvider
from app.integrations.ai.models import AIProviderRequest, AIProviderResponse
from app.schemas.ai import AITaskType, AIConfidenceLevel


class MockAIProvider(AIProvider):
    """Deterministic Mock AI Provider supporting simulation of error conditions and structured output."""

    def __init__(
        self,
        provider_name: str = "mock",
        model_name: str = "mock-med-v1",
        version: str = "1.0.0",
        simulate_timeout: bool = False,
        simulate_unavailable: bool = False,
        simulate_malformed: bool = False,
        simulate_schema_failure: bool = False,
        simulate_grounding_failure: bool = False,
    ) -> None:
        self._provider_name = provider_name
        self._model_name = model_name
        self._version = version
        self.simulate_timeout = simulate_timeout
        self.simulate_unavailable = simulate_unavailable
        self.simulate_malformed = simulate_malformed
        self.simulate_schema_failure = simulate_schema_failure
        self.simulate_grounding_failure = simulate_grounding_failure

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def version(self) -> str:
        return self._version

    def _check_simulation_flags(self) -> None:
        if self.simulate_timeout:
            raise AIProviderTimeoutException("Mock provider simulated request timeout.")
        if self.simulate_unavailable:
            raise AIProviderUnavailableException("Mock provider simulated service unavailable.")

    async def generate_text(self, request: AIProviderRequest) -> AIProviderResponse:
        self._check_simulation_flags()
        if self.simulate_malformed:
            return AIProviderResponse(
                raw_text="This is an incomplete or malformed text response that doesn't respect format",
                model=self._model_name,
                provider=self._provider_name,
                model_version=self._version,
                prompt_tokens=45,
                completion_tokens=15,
                total_tokens=60,
                latency_ms=12.5,
            )

        task_type = request.task_type
        text_output = f"Mock response for task {task_type}. Grounded in verified input context."
        return AIProviderResponse(
            raw_text=text_output,
            model=self._model_name,
            provider=self._provider_name,
            model_version=self._version,
            prompt_tokens=50,
            completion_tokens=20,
            total_tokens=70,
            latency_ms=10.0,
        )

    async def generate_structured(
        self,
        request: AIProviderRequest,
        schema: Type[BaseModel],
    ) -> AIProviderResponse:
        self._check_simulation_flags()

        if self.simulate_malformed:
            return AIProviderResponse(
                raw_text="<<MALFORMED JSON NOT PARSABLE",
                model=self._model_name,
                provider=self._provider_name,
                model_version=self._version,
                prompt_tokens=30,
                completion_tokens=5,
                total_tokens=35,
                latency_ms=15.0,
            )

        if self.simulate_schema_failure:
            return AIProviderResponse(
                raw_text=json.dumps({"unexpected_field": "data_missing_required_keys"}),
                model=self._model_name,
                provider=self._provider_name,
                model_version=self._version,
                prompt_tokens=30,
                completion_tokens=10,
                total_tokens=40,
                latency_ms=14.0,
            )

        deterministic_payload = self._build_deterministic_payload(request)
        raw_json = json.dumps(deterministic_payload)

        # Validate with the schema to ensure our mock is valid
        parsed_obj = schema.model_validate(deterministic_payload)

        return AIProviderResponse(
            raw_text=raw_json,
            parsed_json=parsed_obj.model_dump(),
            model=self._model_name,
            provider=self._provider_name,
            model_version=self._version,
            prompt_tokens=85,
            completion_tokens=65,
            total_tokens=150,
            latency_ms=25.0,
        )

    def _build_deterministic_payload(self, request: AIProviderRequest) -> Dict[str, Any]:
        task_type = request.task_type
        # If simulating grounding failure, insert an unsupported hallucinated claim
        grounding_hallucination = "Patient has severe allergies to penicillin and peanut oil." if self.simulate_grounding_failure else None

        if task_type == AITaskType.DOCUMENT_EXTRACTION:
            extracted_facts = [
                {"entity": "Blood Pressure", "value": "120/80 mmHg", "category": "vitals"},
                {"entity": "Heart Rate", "value": "72 bpm", "category": "vitals"},
            ]
            if grounding_hallucination:
                extracted_facts.append({"entity": "Allergy", "value": grounding_hallucination, "category": "allergy"})

            citations = [
                {"document_id": "doc-123", "page": 1, "text_span": "BP 120/80, HR 72", "field": "vitals"}
            ]
            return {
                "document_type": "Discharge Summary",
                "patient_name": "John Doe",
                "extracted_fields": {"patient_name": "John Doe", "date": "2026-09-25"},
                "extracted_facts": extracted_facts,
                "extracted_vitals": [{"type": "BP", "value": "120/80", "unit": "mmHg"}],
                "extracted_allergies": [{"allergen": "Penicillin", "reaction": "Hives"}] if grounding_hallucination else [],
                "extracted_medications": [{"name": "Lisinopril", "dosage": "10mg", "frequency": "daily"}],
                "extracted_diagnoses": [{"diagnosis": "Hypertension", "status": "active"}],
                "extracted_procedures": [],
                "encounter_date": "2026-09-25",
                "source_citations": citations,
                "source_references": citations,
                "uncertainties": [],
                "missing_information": [],
                "confidence": AIConfidenceLevel.HIGH.value,
                "confidence_level": AIConfidenceLevel.HIGH.value,
            }

        elif task_type in (AITaskType.DOCUMENT_SUMMARIZATION, AITaskType.CLINICAL_SUMMARY):
            key_points = [
                "Patient presented with mild seasonal allergies.",
                "Stable vitals recorded during observation.",
            ]
            if grounding_hallucination:
                key_points.append(grounding_hallucination)

            citations = [
                {"field": "summary", "text_span": "stable vitals"}
            ]
            summary_txt = "Patient presented with mild seasonal symptoms and remained hemodynamically stable."
            return {
                "summary": summary_txt,
                "summary_narrative": summary_txt,
                "key_findings": key_points,
                "active_problems": ["Seasonal rhinitis"],
                "current_medications": ["Cetirizine 10mg"],
                "allergies": ["Pollen"],
                "recent_vital_trends": ["BP 120/80 mmHg, HR 72 bpm"],
                "source_citations": citations,
                "source_references": citations,
                "uncertainties": [],
                "missing_information": [],
                "confidence": AIConfidenceLevel.HIGH.value,
                "confidence_level": AIConfidenceLevel.HIGH.value,
            }

        elif task_type == AITaskType.PATIENT_EXPLANATION:
            citations = [
                {"field": "simplified_text", "text_span": "BP normal"}
            ]
            explanation_txt = "Your blood pressure reading looks normal and healthy. Keep taking your prescribed daily vitamins."
            return {
                "simplified_text": explanation_txt,
                "simplified_explanation": explanation_txt,
                "reading_level": "Grade 6",
                "action_items": ["Take daily vitamins with breakfast", "Keep a daily log of blood pressure"],
                "questions_to_ask_doctor": ["Should I schedule my next routine checkup in six months?"],
                "glossary": {"Hypertension": "High blood pressure"},
                "medical_terms_glossary": {"Hypertension": "High blood pressure"},
                "source_citations": citations,
                "source_references": citations,
                "uncertainties": [],
                "missing_information": [],
                "confidence": AIConfidenceLevel.HIGH.value,
                "confidence_level": AIConfidenceLevel.HIGH.value,
            }

        elif task_type == AITaskType.SBAR_ASSISTANCE:
            rec = "Continue telemetry monitoring and follow up in morning rounds."
            if grounding_hallucination:
                rec = f"{rec} Hallucination: {grounding_hallucination}"

            citations = [
                {"field": "assessment", "text_span": "vitals normal"}
            ]
            return {
                "situation": "45-year-old male admitted for observation following mild dizziness.",
                "background": "No prior cardiovascular disease history.",
                "assessment": "Vital signs normal, symptoms resolved after hydration.",
                "recommendation": rec,
                "clinical_facts_used": ["BP 120/80", "HR 72", "Dizziness resolved with hydration"],
                "source_citations": citations,
                "source_references": citations,
                "uncertainties": [],
                "missing_information": [],
                "confidence": AIConfidenceLevel.HIGH.value,
                "confidence_level": AIConfidenceLevel.HIGH.value,
            }

        elif task_type == AITaskType.DISCHARGE_EXTRACTION:
            citations = [
                {"field": "discharge_instructions", "text_span": "rest for 48 hours"}
            ]
            instructions = [
                "Take prescribed medication with food",
                "Rest for 48 hours and avoid heavy lifting",
            ]
            return {
                "organized_instructions": instructions,
                "discharge_instructions": instructions,
                "medication_changes": ["Start Lisinopril 10mg daily"],
                "follow_up_appointments": ["Cardiology clinic in 2 weeks"],
                "warning_signs_red_flags": ["Sudden chest tightness or shortness of breath"],
                "warning_signs": ["Sudden chest tightness or shortness of breath"],
                "activity_and_diet_restrictions": ["No lifting over 10 lbs", "Low-sodium diet"],
                "activity_restrictions": ["No lifting over 10 lbs"],
                "source_citations": citations,
                "source_references": citations,
                "uncertainties": [],
                "missing_information": [],
                "confidence": AIConfidenceLevel.HIGH.value,
                "confidence_level": AIConfidenceLevel.HIGH.value,
            }

        elif task_type == AITaskType.CARE_PLAN_ORGANIZATION:
            citations = [
                {"field": "goals", "text_span": "target BP < 130/80"}
            ]
            return {
                "goals": ["Maintain blood pressure below 130/80 mmHg"],
                "patient_goals": [{"goal": "Maintain blood pressure below 130/80 mmHg", "target_date": "2026-10-25"}],
                "interventions": ["Low-sodium diet", "Daily 30-minute moderate walking"],
                "planned_interventions": [{"intervention": "Low-sodium diet"}, {"intervention": "Daily 30-minute moderate walking"}],
                "monitoring_schedule": [{"metric": "Blood Pressure", "frequency": "Daily AM/PM"}],
                "barriers_to_adherence": ["Busy work schedule"],
                "timelines": ["Re-evaluate in 30 days"],
                "responsible_parties": ["Patient", "Primary Care Provider"],
                "source_citations": citations,
                "source_references": citations,
                "uncertainties": [],
                "missing_information": [],
                "confidence": AIConfidenceLevel.HIGH.value,
                "confidence_level": AIConfidenceLevel.HIGH.value,
            }

        elif task_type == AITaskType.CLINICAL_NOTE_DRAFT:
            plan = "Hydration therapy and discharge home tomorrow."
            if grounding_hallucination:
                plan += f" Hallucinated: {grounding_hallucination}"

            citations = [
                {"field": "subjective", "text_span": "headache resolved"}
            ]
            subj = "Patient reports resolution of earlier headache and fatigue."
            obj = "BP 120/80, HR 72, Afebrile."
            assess = "Transient fatigue likely dehydration-related."
            return {
                "subjective": subj,
                "objective": obj,
                "assessment": assess,
                "plan": plan,
                "full_draft_text": f"S: {subj}\nO: {obj}\nA: {assess}\nP: {plan}",
                "source_citations": citations,
                "source_references": citations,
                "uncertainties": [],
                "missing_information": [],
                "confidence": AIConfidenceLevel.HIGH.value,
                "confidence_level": AIConfidenceLevel.HIGH.value,
            }

        elif task_type == AITaskType.STRUCTURED_CLASSIFICATION:
            citations = [
                {"field": "classification_category", "text_span": "follow up in 2 weeks"}
            ]
            return {
                "category": "ROUTINE_FOLLOW_UP",
                "classification_category": "ROUTINE_FOLLOW_UP",
                "subcategories": ["cardiology"],
                "tags": ["outpatient", "cardiology"],
                "suggested_tags": ["outpatient", "cardiology"],
                "rationale": "Non-authoritative preliminary categorization based on follow-up timeline.",
                "explanation": "Non-authoritative preliminary categorization based on follow-up timeline.",
                "source_citations": citations,
                "source_references": citations,
                "uncertainties": [],
                "missing_information": [],
                "confidence": AIConfidenceLevel.MEDIUM.value,
                "confidence_level": AIConfidenceLevel.MEDIUM.value,
            }

        # Fallback default generic payload
        return {
            "fields": {"result": "Default mock response"},
            "source_citations": [],
            "source_references": [],
            "uncertainties": [],
            "missing_information": [],
            "confidence": AIConfidenceLevel.UNKNOWN.value,
            "confidence_level": AIConfidenceLevel.UNKNOWN.value,
        }

    async def health_check(self) -> Dict[str, Any]:
        self._check_simulation_flags()
        return {
            "status": "healthy",
            "provider": self._provider_name,
            "model": self._model_name,
            "version": self._version,
            "mode": "mock_deterministic",
        }

    def get_model_metadata(self) -> Dict[str, Any]:
        return {
            "provider": self._provider_name,
            "model": self._model_name,
            "version": self._version,
            "max_context_tokens": 8192,
            "max_output_tokens": 2048,
            "supports_structured_output": True,
            "training_opt_in": False,
            "retention_mode": "disabled",
        }
