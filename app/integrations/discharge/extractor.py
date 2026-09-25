"""Local rule-based discharge summary extractor (Phase 9).

Extracts structured clinical instructions (medications, activity, diet, wound care,
warning signs, follow-up) from document text.
Preserves clinical boundaries:
- Extracted diagnoses are labelled as extracted from the hospital document, NOT autonomously diagnosed.
"""

import re
from typing import Any
from app.integrations.discharge.base import (
    DischargeExtractor,
    ExtractedDischargeData,
)
from app.schemas.discharge import (
    DischargeActivityInstruction,
    DischargeDietInstruction,
    DischargeFollowUpItem,
    DischargeMedicationItem,
    DischargeWarningSign,
    DischargeWoundCareInstruction,
)


class LocalDischargeExtractor(DischargeExtractor):
    """Rule-based extractor for hospital discharge documents."""

    @property
    def provider_name(self) -> str:
        return "local_discharge_extractor"

    async def extract_discharge_instructions(self, document_text: str) -> ExtractedDischargeData:
        """Parse structured discharge instructions from document text."""
        diagnoses: list[str] = []
        medications: list[DischargeMedicationItem] = []
        activities: list[DischargeActivityInstruction] = []
        diets: list[DischargeDietInstruction] = []
        wound_care: list[DischargeWoundCareInstruction] = []
        warning_signs: list[DischargeWarningSign] = []
        follow_ups: list[DischargeFollowUpItem] = []

        lines = document_text.splitlines()
        current_section = None

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            lower_line = line.lower()

            # Section detection
            if any(lower_line.startswith(h) for h in ["discharge diagnoses:", "discharge diagnosis:", "diagnoses:", "diagnosis:"]):
                current_section = "DIAGNOSIS"
                content = re.sub(r"^(discharge diagnoses:|discharge diagnosis:|diagnoses:|diagnosis:)\s*", "", line, flags=re.I).strip()
                if content:
                    diagnoses.append(content)
                continue
            elif any(lower_line.startswith(h) for h in ["discharge medications:", "medications on discharge:", "medications:", "rx:"]):
                current_section = "MEDICATIONS"
                content = re.sub(r"^(discharge medications:|medications on discharge:|medications:|rx:)\s*", "", line, flags=re.I).strip()
                if content:
                    medications.append(self._parse_med_line(content))
                continue
            elif any(lower_line.startswith(h) for h in ["activity restrictions:", "physical activity:", "activity:", "activities:"]):
                current_section = "ACTIVITY"
                content = re.sub(r"^(activity restrictions:|physical activity:|activity:|activities:)\s*", "", line, flags=re.I).strip()
                if content:
                    activities.append(DischargeActivityInstruction(category="RESTRICTION", description=content))
                continue
            elif any(lower_line.startswith(h) for h in ["dietary orders:", "dietary instructions:", "diet:", "nutrition:"]):
                current_section = "DIET"
                content = re.sub(r"^(dietary orders:|dietary instructions:|diet:|nutrition:)\s*", "", line, flags=re.I).strip()
                if content:
                    diets.append(DischargeDietInstruction(dietary_type="RECOMMENDED", recommendations=[content]))
                continue
            elif any(lower_line.startswith(h) for h in ["wound care:", "surgical site care:", "dressing:"]):
                current_section = "WOUND_CARE"
                content = re.sub(r"^(wound care:|surgical site care:|dressing:)\s*", "", line, flags=re.I).strip()
                if content:
                    wound_care.append(DischargeWoundCareInstruction(dressing_instructions=content))
                continue
            elif any(lower_line.startswith(h) for h in ["red flags & warning signs:", "warning signs:", "when to seek care:", "emergency signs:", "red flags:"]):
                current_section = "WARNING_SIGNS"
                content = re.sub(r"^(red flags & warning signs:|warning signs:|when to seek care:|emergency signs:|red flags:)\s*", "", line, flags=re.I).strip()
                if content:
                    warning_signs.append(
                        DischargeWarningSign(
                            symptom=content,
                            action_required="Seek urgent medical assessment or emergency room immediately",
                        )
                    )
                continue
            elif any(lower_line.startswith(h) for h in ["follow-up appointments:", "follow-up:", "follow up:", "next appointment:"]):
                current_section = "FOLLOW_UP"
                content = re.sub(r"^(follow-up appointments:|follow-up:|follow up:|next appointment:)\s*", "", line, flags=re.I).strip()
                if content:
                    follow_ups.append(
                        DischargeFollowUpItem(
                            provider_or_specialty="Attending Physician / Specialist",
                            recommended_timeframe=content,
                            purpose="Post-discharge clinical review",
                        )
                    )
                continue
            elif any(lower_line.startswith(h) for h in ["hospital course:", "history of present illness:", "procedures:", "attending physician:"]):
                current_section = None
                continue

            # Process lines under active section
            cleaned_bullet = re.sub(r"^[-*•\s]*(\d+[.)]\s*|[-*•]\s*)?", "", line).strip()
            if not cleaned_bullet:
                continue

            if current_section == "DIAGNOSIS":
                diagnoses.append(cleaned_bullet)
            elif current_section == "MEDICATIONS":
                medications.append(self._parse_med_line(cleaned_bullet))
            elif current_section == "ACTIVITY":
                activities.append(DischargeActivityInstruction(category="RESTRICTION", description=cleaned_bullet))
            elif current_section == "DIET":
                diets.append(DischargeDietInstruction(dietary_type="RECOMMENDED", recommendations=[cleaned_bullet]))
            elif current_section == "WOUND_CARE":
                wound_care.append(DischargeWoundCareInstruction(dressing_instructions=cleaned_bullet))
            elif current_section == "WARNING_SIGNS":
                action = "Seek urgent medical assessment or emergency care immediately"
                symptom = cleaned_bullet
                if "->" in cleaned_bullet:
                    parts = cleaned_bullet.split("->", 1)
                    symptom = parts[0].strip()
                    action = parts[1].strip()
                warning_signs.append(
                    DischargeWarningSign(
                        symptom=symptom,
                        action_required=action,
                    )
                )
            elif current_section == "FOLLOW_UP":
                follow_ups.append(
                    DischargeFollowUpItem(
                        provider_or_specialty="Outpatient Clinic",
                        recommended_timeframe=cleaned_bullet,
                        purpose="Post-discharge recovery check",
                    )
                )

        # Baseline safety warning signs if none explicitly mentioned
        if not warning_signs:
            warning_signs.append(
                DischargeWarningSign(
                    symptom="Severe pain, high fever (>38.5C), sudden shortness of breath, or bleeding",
                    action_required="Seek emergency medical attention immediately",
                    severity="CRITICAL",
                )
            )

        return ExtractedDischargeData(
            discharge_diagnoses=diagnoses,
            medications=medications,
            activity_instructions=activities,
            diet_instructions=diets,
            wound_care_instructions=wound_care,
            warning_signs=warning_signs,
            follow_up_instructions=follow_ups,
            confidence_score=0.95 if (diagnoses or medications) else 0.70,
            extractor_version="1.0.0",
        )

    def _parse_med_line(self, line: str) -> DischargeMedicationItem:
        """Extract medication name, dosage, frequency, and instructions."""
        parts = [p.strip() for p in line.split(",") if p.strip()]
        name = parts[0]
        freq = parts[1] if len(parts) > 1 else None
        inst = parts[2] if len(parts) > 2 else None

        return DischargeMedicationItem(
            drug_name=name,
            frequency=freq,
            instructions=inst,
            is_new=True,
        )

    # Convenient alias
    extract = extract_discharge_instructions
