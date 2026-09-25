"""Phase 6 tests: Prescription extraction mapper and structured field ingestion."""

from app.services.prescription_extraction_mapper import (
    PrescriptionExtractionMapper,
    extract_duration_structured,
    extract_frequency_structured,
)


def test_frequency_extraction():
    """Verify frequency extraction across standard and latin abbreviations."""
    assert extract_frequency_structured("1-0-1") == "twice daily (morning, night)"
    assert extract_frequency_structured("1-1-1") == "three times daily (morning, noon, night)"
    assert extract_frequency_structured("1-0-0") == "once daily (morning)"
    assert extract_frequency_structured("0-0-1") == "once daily (night)"
    assert extract_frequency_structured("once daily") == "once daily"
    assert extract_frequency_structured("twice daily") == "twice daily"
    assert extract_frequency_structured("SOS") == "SOS (as needed)"
    assert extract_frequency_structured("PRN") == "PRN (as needed)"
    assert extract_frequency_structured(None) is None


def test_duration_extraction():
    """Verify duration normalization to standard value + unit."""
    assert extract_duration_structured("5 days") == "5 days"
    assert extract_duration_structured("5d") == "5 days"
    assert extract_duration_structured("2 weeks") == "2 weeks"
    assert extract_duration_structured("1 month") == "1 months"
    assert extract_duration_structured(None) is None


def test_map_discrete_extraction_fields():
    """Map single discrete extraction dictionary to prescription item."""
    fields = [
        {"field_name": "drug_name", "value": "Metformin"},
        {"field_name": "strength", "value": "500 mg"},
        {"field_name": "dosage_form", "value": "tablet"},
        {"field_name": "frequency", "value": "1-0-1"},
        {"field_name": "duration", "value": "30 days"},
        {"field_name": "instructions", "value": "with meals"},
    ]
    items = PrescriptionExtractionMapper.map_extraction_fields(fields, extraction_id="ext-123")
    assert len(items) == 1
    item = items[0]
    assert item.drug_name_raw == "Metformin"
    assert item.strength_raw == "500 mg"
    assert item.dosage_form_raw == "tablet"
    assert item.frequency_raw == "twice daily (morning, night)"
    assert item.duration_raw == "30 days"
    assert item.instructions_raw == "with meals"
    assert item.extraction_reference == "ext-123"


def test_map_multiple_medications_list():
    """Map structured list of medications extracted from a multi-drug prescription."""
    fields = [
        {
            "field_name": "medications",
            "value": [
                {
                    "drug_name": "Amoxicillin",
                    "strength": "500 mg",
                    "frequency": "twice daily",
                    "duration": "5 days",
                },
                {
                    "drug_name": "Paracetamol",
                    "strength": "650 mg",
                    "frequency": "SOS",
                    "instructions": "for fever",
                },
            ],
        }
    ]
    items = PrescriptionExtractionMapper.map_extraction_fields(fields, extraction_id="ext-multi")
    assert len(items) == 2
    assert items[0].drug_name_raw == "Amoxicillin"
    assert items[0].duration_raw == "5 days"
    assert items[1].drug_name_raw == "Paracetamol"
    assert items[1].frequency_raw == "SOS (as needed)"
    assert items[1].instructions_raw == "for fever"
    assert items[0].extraction_reference == "ext-multi:item_0"
    assert items[1].extraction_reference == "ext-multi:item_1"


def test_map_empty_fields_returns_empty_list():
    """Empty or non-medication fields return an empty list gracefully."""
    fields = [{"field_name": "patient_name", "value": "John Doe"}]
    items = PrescriptionExtractionMapper.map_extraction_fields(fields)
    assert len(items) == 0
