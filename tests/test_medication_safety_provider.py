"""Tests for Medication Safety Providers (Phase 7).

Validates:
- Capabilities discovery
- Mock provider deterministic responses
- Drug-Drug Interactions (DDI)
- Drug-Allergy cross-reactivity
- Drug-Disease interactions
- Contraindications
- Duplicate therapy detection
- Error and timeout simulation
- Licensed provider credential validation
"""

import pytest

from app.integrations.medication_safety.base import (
    MedicationSafetyAuthError,
    MedicationSafetyProviderError,
    MedicationSafetyTimeoutError,
)
from app.integrations.medication_safety.providers.licensed_provider import (
    LicensedMedicationSafetyProvider,
)
from app.integrations.medication_safety.providers.mock import MockMedicationSafetyProvider
from app.integrations.medication_safety.registry import (
    get_medication_safety_provider,
    get_safety_capabilities,
)
from app.schemas.medication_safety import (
    SafetyAlertSeverity,
    SafetyCheckType,
    SafetyEvaluationStatus,
    SafetyMedicationInput,
    SafetyPatientContext,
)


@pytest.mark.asyncio
async def test_mock_provider_capabilities():
    """Verify capabilities declared by the mock safety provider."""
    provider = MockMedicationSafetyProvider()
    caps = get_safety_capabilities(provider)

    assert caps.provider_name == MockMedicationSafetyProvider.MOCK_PROVIDER_NAME
    assert caps.capabilities[SafetyCheckType.DRUG_DRUG.value] is True
    assert caps.capabilities[SafetyCheckType.DRUG_ALLERGY.value] is True
    assert caps.capabilities[SafetyCheckType.DRUG_DISEASE.value] is True
    assert caps.capabilities[SafetyCheckType.CONTRAINDICATION.value] is True
    assert caps.capabilities[SafetyCheckType.DUPLICATE_THERAPY.value] is True
    assert caps.capabilities[SafetyCheckType.DOSING.value] is False
    assert caps.capabilities[SafetyCheckType.HEPATIC.value] is False


@pytest.mark.asyncio
async def test_mock_provider_clean_evaluation():
    """Single medication with no interactions or conflicts yields CLEAR status."""
    provider = MockMedicationSafetyProvider()
    meds = [
        SafetyMedicationInput(name="Paracetamol", strength="500 mg", dosage_form="tablet")
    ]
    context = SafetyPatientContext(allergies=[], conditions=[])

    result = await provider.evaluate_safety(medications=meds, patient_context=context)

    assert result.status == SafetyEvaluationStatus.CLEAR
    assert len(result.alerts) == 0
    assert result.provider_name == MockMedicationSafetyProvider.MOCK_PROVIDER_NAME
    assert result.provider_version == MockMedicationSafetyProvider.MOCK_PROVIDER_VERSION


@pytest.mark.asyncio
async def test_mock_provider_ddi_metformin_contrast():
    """Metformin + Iodinated Contrast triggers a MAJOR DDI alert (lactic acidosis risk)."""
    provider = MockMedicationSafetyProvider()
    meds = [
        SafetyMedicationInput(name="Metformin HCl", strength="500 mg", terminology_code="6809"),
        SafetyMedicationInput(name="Iodinated Radiopaque Contrast", terminology_code="9999"),
    ]
    context = SafetyPatientContext()

    result = await provider.evaluate_safety(medications=meds, patient_context=context)

    assert result.status == SafetyEvaluationStatus.ALERT
    assert len(result.alerts) >= 1
    ddi_alert = next(a for a in result.alerts if a.check_type == SafetyCheckType.DRUG_DRUG)
    assert ddi_alert.severity == SafetyAlertSeverity.MAJOR
    assert "Metformin" in ddi_alert.title
    assert "Contrast" in ddi_alert.title
    assert len(ddi_alert.medications_involved) == 2


@pytest.mark.asyncio
async def test_mock_provider_ddi_sildenafil_nitroglycerin():
    """Sildenafil + Nitroglycerin triggers a CRITICAL DDI alert."""
    provider = MockMedicationSafetyProvider()
    meds = [
        SafetyMedicationInput(name="Sildenafil citrate", strength="50 mg"),
        SafetyMedicationInput(name="Nitroglycerin sublingual", strength="0.4 mg"),
    ]
    context = SafetyPatientContext()

    result = await provider.evaluate_safety(medications=meds, patient_context=context)

    assert result.status == SafetyEvaluationStatus.ALERT
    alert = next(a for a in result.alerts if a.check_type == SafetyCheckType.DRUG_DRUG)
    assert alert.severity == SafetyAlertSeverity.CRITICAL
    assert "Nitrate" in alert.title


@pytest.mark.asyncio
async def test_mock_provider_drug_allergy_conflict():
    """Documented penicillin allergy + Amoxicillin triggers CRITICAL allergy alert."""
    provider = MockMedicationSafetyProvider()
    meds = [
        SafetyMedicationInput(name="Amoxicillin", strength="500 mg", terminology_code="723")
    ]
    context = SafetyPatientContext(
        allergies=[{"id": "all-01", "allergen": "Penicillin V", "severity": "CRITICAL"}]
    )

    result = await provider.evaluate_safety(medications=meds, patient_context=context)

    assert result.status == SafetyEvaluationStatus.ALERT
    assert len(result.alerts) == 1
    alert = result.alerts[0]
    assert alert.check_type == SafetyCheckType.DRUG_ALLERGY
    assert alert.severity == SafetyAlertSeverity.CRITICAL
    assert "Beta-Lactam" in alert.title or "Penicillin" in alert.title
    assert alert.clinical_context_involved[0]["allergen"] == "penicillin v"


@pytest.mark.asyncio
async def test_mock_provider_drug_disease_interaction():
    """Peptic ulcer disease + Ibuprofen triggers MAJOR drug-disease alert."""
    provider = MockMedicationSafetyProvider()
    meds = [
        SafetyMedicationInput(name="Ibuprofen", strength="400 mg")
    ]
    context = SafetyPatientContext(
        conditions=[{"id": "cond-01", "diagnosis": "Active Peptic Ulcer", "status": "ACTIVE"}]
    )

    result = await provider.evaluate_safety(medications=meds, patient_context=context)

    assert result.status == SafetyEvaluationStatus.ALERT
    alert = next(a for a in result.alerts if a.check_type == SafetyCheckType.DRUG_DISEASE)
    assert alert.severity == SafetyAlertSeverity.MAJOR
    assert "Peptic Ulcer" in alert.title


@pytest.mark.asyncio
async def test_mock_provider_duplicate_therapy():
    """Atorvastatin + Rosuvastatin triggers MODERATE duplicate statin therapy alert."""
    provider = MockMedicationSafetyProvider()
    meds = [
        SafetyMedicationInput(name="Atorvastatin", strength="20 mg"),
        SafetyMedicationInput(name="Rosuvastatin", strength="10 mg"),
    ]
    context = SafetyPatientContext()

    result = await provider.evaluate_safety(medications=meds, patient_context=context)

    assert result.status == SafetyEvaluationStatus.WARNING
    alert = next(a for a in result.alerts if a.check_type == SafetyCheckType.DUPLICATE_THERAPY)
    assert alert.severity == SafetyAlertSeverity.MODERATE
    assert "Duplicate Statin Therapy" in alert.title


@pytest.mark.asyncio
async def test_mock_provider_pediatric_contraindication():
    """Aspirin in pediatric patient (<18) triggers CRITICAL Reye syndrome contraindication."""
    provider = MockMedicationSafetyProvider()
    meds = [SafetyMedicationInput(name="Aspirin", strength="81 mg")]
    context = SafetyPatientContext(age_years=12)

    result = await provider.evaluate_safety(medications=meds, patient_context=context)

    assert result.status == SafetyEvaluationStatus.ALERT
    alert = next(a for a in result.alerts if a.check_type == SafetyCheckType.CONTRAINDICATION)
    assert alert.severity == SafetyAlertSeverity.CRITICAL
    assert "Reye" in alert.title


@pytest.mark.asyncio
async def test_mock_provider_unsupported_check_type():
    """Requesting unsupported check type (e.g. DOSING) returns NOT_SUPPORTED summary."""
    provider = MockMedicationSafetyProvider()
    meds = [SafetyMedicationInput(name="Paracetamol", strength="500 mg")]
    context = SafetyPatientContext()

    result = await provider.evaluate_safety(
        medications=meds,
        patient_context=context,
        requested_checks=[SafetyCheckType.DOSING],
    )

    assert result.status == SafetyEvaluationStatus.NOT_SUPPORTED
    assert len(result.check_summaries) == 1
    summary = result.check_summaries[0]
    assert summary.check_type == SafetyCheckType.DOSING
    assert summary.supported is False
    assert summary.status == SafetyEvaluationStatus.NOT_SUPPORTED


@pytest.mark.asyncio
async def test_mock_provider_simulated_timeout():
    """Triggering timeout simulates network failure and raises MedicationSafetyTimeoutError."""
    provider = MockMedicationSafetyProvider()
    meds = [SafetyMedicationInput(name="Medication_TRIGGER_TIMEOUT")]
    context = SafetyPatientContext()

    with pytest.raises(MedicationSafetyTimeoutError) as exc_info:
        await provider.evaluate_safety(medications=meds, patient_context=context)
    assert exc_info.value.is_transient is True


@pytest.mark.asyncio
async def test_mock_provider_simulated_auth_error():
    """Triggering auth error simulates 401 and raises MedicationSafetyAuthError."""
    provider = MockMedicationSafetyProvider()
    meds = [SafetyMedicationInput(name="Medication_TRIGGER_AUTH_ERROR")]
    context = SafetyPatientContext()

    with pytest.raises(MedicationSafetyAuthError) as exc_info:
        await provider.evaluate_safety(medications=meds, patient_context=context)
    assert exc_info.value.is_transient is False


@pytest.mark.asyncio
async def test_licensed_provider_missing_credentials():
    """Licensed provider raises MedicationSafetyAuthError if credentials are not configured."""
    provider = LicensedMedicationSafetyProvider(base_url="", api_key="")
    meds = [SafetyMedicationInput(name="Metformin")]
    context = SafetyPatientContext()

    with pytest.raises(MedicationSafetyAuthError) as exc_info:
        await provider.evaluate_safety(medications=meds, patient_context=context)
    assert "EXTERNAL PROVIDER DEPENDENCY" in str(exc_info.value)
