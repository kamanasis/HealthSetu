"""Mapper from Phase 5 document extractions into structured prescription items."""

import re
from typing import Any
from app.schemas.prescription import PrescriptionItemCreate

FREQUENCY_PATTERNS = {
    r"\b1-0-1\b": "twice daily (morning, night)",
    r"\b1-1-1\b": "three times daily (morning, noon, night)",
    r"\b1-0-0\b": "once daily (morning)",
    r"\b0-0-1\b": "once daily (night)",
    r"\bonce\s+daily\b": "once daily",
    r"\btwice\s+daily\b": "twice daily",
    r"\bthree\s+times\s+daily\b": "three times daily",
    r"\bevery\s+8\s+hours\b": "every 8 hours",
    r"\bevery\s+12\s+hours\b": "every 12 hours",
    r"\bsos\b": "SOS (as needed)",
    r"\bprn\b": "PRN (as needed)",
}

DURATION_PATTERN = re.compile(r"(\d+)\s*(days?|weeks?|months?|d|w|m)\b", re.IGNORECASE)


def extract_duration_structured(raw_text: str | None) -> str | None:
    """Safely extract structured duration string if clearly identifiable."""
    if not raw_text:
        return None
    match = DURATION_PATTERN.search(raw_text)
    if match:
        val, unit = match.groups()
        unit_lower = unit.lower()
        if unit_lower in ("d", "day", "days"):
            canonical_unit = "days"
        elif unit_lower in ("w", "week", "weeks"):
            canonical_unit = "weeks"
        elif unit_lower in ("m", "month", "months"):
            canonical_unit = "months"
        else:
            canonical_unit = unit_lower
        return f"{val} {canonical_unit}"
    return raw_text.strip()


def extract_frequency_structured(raw_text: str | None) -> str | None:
    """Safely identify structured frequency representation."""
    if not raw_text:
        return None
    cleaned = raw_text.strip().lower()
    for pattern, normalized in FREQUENCY_PATTERNS.items():
        if re.search(pattern, cleaned, re.IGNORECASE):
            return normalized
    return raw_text.strip()


class PrescriptionExtractionMapper:
    """Maps unstructured or semi-structured extraction outputs to PrescriptionItemCreate domain objects.

    CRITICAL ARCHITECTURAL BOUNDARY:
    Preserves raw values faithfully without clinical manipulation or diagnostic inference.
    """

    @classmethod
    def map_extraction_fields(
        cls, fields: list[dict[str, Any]], extraction_id: str | None = None
    ) -> list[PrescriptionItemCreate]:
        """Convert a list of extraction field dicts into PrescriptionItemCreate objects."""
        items: list[PrescriptionItemCreate] = []

        # Find all field names relevant to medications
        field_map = {f.get("field_name", ""): f.get("value", "") for f in fields}

        # Check if structured 'medications' list is present
        med_list = field_map.get("medications")
        if isinstance(med_list, list):
            for idx, med in enumerate(med_list):
                if isinstance(med, dict) and med.get("drug_name"):
                    items.append(
                        PrescriptionItemCreate(
                            drug_name_raw=str(med.get("drug_name", "")).strip(),
                            strength_raw=str(med.get("strength")) if med.get("strength") else None,
                            dosage_form_raw=str(med.get("dosage_form")) if med.get("dosage_form") else None,
                            dose_raw=str(med.get("dose")) if med.get("dose") else None,
                            route_raw=str(med.get("route")) if med.get("route") else None,
                            frequency_raw=extract_frequency_structured(med.get("frequency")),
                            duration_raw=extract_duration_structured(med.get("duration")),
                            quantity_raw=str(med.get("quantity")) if med.get("quantity") else None,
                            instructions_raw=str(med.get("instructions")) if med.get("instructions") else None,
                            extraction_reference=f"{extraction_id}:item_{idx}" if extraction_id else None,
                        )
                    )
            if items:
                return items

        # Fallback to discrete fields if single medication extracted
        drug_name = field_map.get("drug_name") or field_map.get("medication_name")
        if drug_name:
            items.append(
                PrescriptionItemCreate(
                    drug_name_raw=str(drug_name).strip(),
                    strength_raw=str(field_map.get("strength")) if field_map.get("strength") else None,
                    dosage_form_raw=str(field_map.get("dosage_form")) if field_map.get("dosage_form") else None,
                    dose_raw=str(field_map.get("dose")) if field_map.get("dose") else None,
                    route_raw=str(field_map.get("route")) if field_map.get("route") else None,
                    frequency_raw=extract_frequency_structured(field_map.get("frequency")),
                    duration_raw=extract_duration_structured(field_map.get("duration")),
                    quantity_raw=str(field_map.get("quantity")) if field_map.get("quantity") else None,
                    instructions_raw=str(field_map.get("instructions")) if field_map.get("instructions") else None,
                    extraction_reference=extraction_id,
                )
            )

        return items
