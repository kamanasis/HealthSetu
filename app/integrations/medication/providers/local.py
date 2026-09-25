"""Deterministic local mock terminology provider for development and automated testing."""

import re
from typing import Any

from app.integrations.medication.base import (
    MedicationTerminologyProvider,
    NormalizedConcept,
    RawMedicationInput,
    TerminologyLookupResult,
)
from app.schemas.prescription import NormalizationStatus

PROVIDER_NAME = "local_mock"
PROVIDER_VERSION = "2026.1-mock"

# Curated reference concepts for testing & local development
MOCK_VOCABULARY: dict[str, dict[str, Any]] = {
    "amoxicillin": {
        "canonical_name": "Amoxicillin",
        "generic_name": "Amoxicillin",
        "brand_name": "Amoxil",
        "terminology_system": "RXNORM",
        "terminology_code": "8640",
        "default_strength": "500 mg",
        "default_dosage_form": "capsule",
        "default_route": "oral",
    },
    "amoxil": {
        "canonical_name": "Amoxicillin",
        "generic_name": "Amoxicillin",
        "brand_name": "Amoxil",
        "terminology_system": "RXNORM",
        "terminology_code": "8640",
        "default_strength": "500 mg",
        "default_dosage_form": "capsule",
        "default_route": "oral",
    },
    "paracetamol": {
        "canonical_name": "Acetaminophen",
        "generic_name": "Acetaminophen",
        "brand_name": "Tylenol",
        "terminology_system": "RXNORM",
        "terminology_code": "161",
        "default_strength": "500 mg",
        "default_dosage_form": "tablet",
        "default_route": "oral",
    },
    "acetaminophen": {
        "canonical_name": "Acetaminophen",
        "generic_name": "Acetaminophen",
        "brand_name": "Tylenol",
        "terminology_system": "RXNORM",
        "terminology_code": "161",
        "default_strength": "500 mg",
        "default_dosage_form": "tablet",
        "default_route": "oral",
    },
    "metformin": {
        "canonical_name": "Metformin hydrochloride",
        "generic_name": "Metformin",
        "brand_name": "Glucophage",
        "terminology_system": "RXNORM",
        "terminology_code": "6809",
        "default_strength": "500 mg",
        "default_dosage_form": "tablet",
        "default_route": "oral",
    },
    "atorvastatin": {
        "canonical_name": "Atorvastatin calcium",
        "generic_name": "Atorvastatin",
        "brand_name": "Lipitor",
        "terminology_system": "RXNORM",
        "terminology_code": "83367",
        "default_strength": "20 mg",
        "default_dosage_form": "tablet",
        "default_route": "oral",
    },
    "ibuprofen": {
        "canonical_name": "Ibuprofen",
        "generic_name": "Ibuprofen",
        "brand_name": "Advil",
        "terminology_system": "RXNORM",
        "terminology_code": "5640",
        "default_strength": "400 mg",
        "default_dosage_form": "tablet",
        "default_route": "oral",
    },
    "omeprazole": {
        "canonical_name": "Omeprazole",
        "generic_name": "Omeprazole",
        "brand_name": "Prilosec",
        "terminology_system": "RXNORM",
        "terminology_code": "7646",
        "default_strength": "20 mg",
        "default_dosage_form": "capsule",
        "default_route": "oral",
    },
    "azithromycin": {
        "canonical_name": "Azithromycin",
        "generic_name": "Azithromycin",
        "brand_name": "Zithromax",
        "terminology_system": "RXNORM",
        "terminology_code": "18631",
        "default_strength": "250 mg",
        "default_dosage_form": "tablet",
        "default_route": "oral",
    },
    "cetirizine": {
        "canonical_name": "Cetirizine hydrochloride",
        "generic_name": "Cetirizine",
        "brand_name": "Zyrtec",
        "terminology_system": "RXNORM",
        "terminology_code": "20610",
        "default_strength": "10 mg",
        "default_dosage_form": "tablet",
        "default_route": "oral",
    },
}

# Known ambiguous prefixes for testing disambiguation handling
MOCK_AMBIGUOUS_MAP: dict[str, list[str]] = {
    "metro": ["Metronidazole", "Metoprolol"],
    "met": ["Metformin", "Metronidazole", "Metoprolol"],
    "amox": ["Amoxicillin", "Amoxicillin / Clavulanate"],
}

# Strength normalization patterns
STRENGTH_G_PATTERN = re.compile(r"^([\d.]+)\s*g$", re.IGNORECASE)
STRENGTH_MCG_PATTERN = re.compile(r"^([\d.]+)\s*mcg$", re.IGNORECASE)
STRENGTH_MG_PATTERN = re.compile(r"^([\d.]+)\s*mg$", re.IGNORECASE)
STRENGTH_ML_PATTERN = re.compile(r"^([\d.]+)\s*ml$", re.IGNORECASE)

# Dosage form mapping
FORM_MAPPING = {
    "tab": "tablet",
    "tabs": "tablet",
    "tablet": "tablet",
    "tablets": "tablet",
    "cap": "capsule",
    "caps": "capsule",
    "capsule": "capsule",
    "capsules": "capsule",
    "syr": "syrup",
    "syrup": "syrup",
    "susp": "suspension",
    "suspension": "suspension",
    "inj": "injection",
    "injection": "injection",
    "crm": "cream",
    "cream": "cream",
    "oint": "ointment",
    "ointment": "ointment",
    "sol": "solution",
    "solution": "solution",
}

# Route mapping
ROUTE_MAPPING = {
    "po": "oral",
    "oral": "oral",
    "by mouth": "oral",
    "per os": "oral",
    "iv": "intravenous",
    "intravenous": "intravenous",
    "im": "intramuscular",
    "intramuscular": "intramuscular",
    "sc": "subcutaneous",
    "subcutaneous": "subcutaneous",
    "top": "topical",
    "topical": "topical",
    "inh": "inhaled",
    "inhalation": "inhaled",
}


def normalize_strength(raw_strength: str | None) -> str | None:
    """Normalize medication strength units safely without clinical inference."""
    if not raw_strength:
        return None
    raw_clean = raw_strength.strip()
    
    # 0.5 g -> 500 mg
    g_match = STRENGTH_G_PATTERN.match(raw_clean)
    if g_match:
        try:
            val = float(g_match.group(1))
            mg_val = int(val * 1000) if (val * 1000).is_integer() else val * 1000
            return f"{mg_val} mg"
        except ValueError:
            pass

    # 1000 mcg -> 1 mg
    mcg_match = STRENGTH_MCG_PATTERN.match(raw_clean)
    if mcg_match:
        try:
            val = float(mcg_match.group(1))
            if val >= 1000 and (val / 1000).is_integer():
                return f"{int(val / 1000)} mg"
            return f"{val} mcg"
        except ValueError:
            pass

    # 500mg -> 500 mg
    mg_match = STRENGTH_MG_PATTERN.match(raw_clean)
    if mg_match:
        return f"{mg_match.group(1)} mg"

    # 5ml -> 5 mL
    ml_match = STRENGTH_ML_PATTERN.match(raw_clean)
    if ml_match:
        return f"{ml_match.group(1)} mL"

    return raw_clean


def normalize_dosage_form(raw_form: str | None) -> str | None:
    """Normalize dosage form safely."""
    if not raw_form:
        return None
    cleaned = raw_form.strip().lower()
    return FORM_MAPPING.get(cleaned, raw_form.strip())


def normalize_route(raw_route: str | None) -> str | None:
    """Normalize administration route safely."""
    if not raw_route:
        return None
    cleaned = raw_route.strip().lower()
    return ROUTE_MAPPING.get(cleaned, raw_route.strip())


class LocalMedicationProvider:
    """Deterministic local terminology provider for testing and offline development.

    MARKER: DEVELOPMENT/TEST ONLY.
    Not for production clinical decision support.
    """

    def __init__(self, failure_trigger: str | None = None) -> None:
        self.failure_trigger = failure_trigger

    async def normalize(self, medication_input: RawMedicationInput) -> TerminologyLookupResult:
        """Evaluate raw medication input against local mock terminology dataset."""
        raw_name = medication_input.drug_name_raw.strip()
        normalized_lookup_key = raw_name.lower()

        # Simulated failure test hooks
        if normalized_lookup_key in ("simulatefailure", "error_trigger") or self.failure_trigger:
            return TerminologyLookupResult(
                status=NormalizationStatus.FAILED,
                error_code="TERMINOLOGY_PROVIDER_UNAVAILABLE",
                error_message="Simulated terminology provider failure for resilience testing.",
            )

        if normalized_lookup_key == "simulatetimeout":
            return TerminologyLookupResult(
                status=NormalizationStatus.FAILED,
                error_code="TERMINOLOGY_PROVIDER_TIMEOUT",
                error_message="Simulated terminology provider execution timeout.",
            )

        # Check for ambiguity
        if normalized_lookup_key in MOCK_AMBIGUOUS_MAP:
            candidates = MOCK_AMBIGUOUS_MAP[normalized_lookup_key]
            return TerminologyLookupResult(
                status=NormalizationStatus.AMBIGUOUS,
                potential_matches=candidates,
                error_message=f"Multiple terminology concepts match '{raw_name}'. Selection cannot be automated.",
            )

        # Check for exact or alias match in mock vocabulary
        entry = MOCK_VOCABULARY.get(normalized_lookup_key)
        if entry:
            norm_strength = normalize_strength(medication_input.strength_raw) or entry.get("default_strength")
            norm_form = normalize_dosage_form(medication_input.dosage_form_raw) or entry.get("default_dosage_form")
            norm_route = normalize_route(medication_input.route_raw) or entry.get("default_route")

            concept = NormalizedConcept(
                canonical_name=entry["canonical_name"],
                generic_name=entry["generic_name"],
                brand_name=entry["brand_name"],
                terminology_system=entry["terminology_system"],
                terminology_code=entry["terminology_code"],
                normalized_strength=norm_strength,
                normalized_dosage_form=norm_form,
                normalized_route=norm_route,
                confidence_score=0.98,
                provider=PROVIDER_NAME,
                provider_version=PROVIDER_VERSION,
            )
            return TerminologyLookupResult(
                status=NormalizationStatus.MATCHED,
                concept=concept,
            )

        # Unmatched outcome
        return TerminologyLookupResult(
            status=NormalizationStatus.UNMATCHED,
            error_message=f"No terminology match found for medication name '{raw_name}'.",
        )
