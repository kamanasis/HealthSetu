"""Deterministic Mock Medication Safety Provider for Development and Testing.

=============================================================================
WARNING — DEVELOPMENT / TEST USE ONLY
=============================================================================
This mock provider uses synthetic clinical scenarios to validate backend
orchestration, normalization, and security boundaries.

IT IS NOT CLINICALLY VALIDATED AND MUST NEVER BE USED AS A PRESCRIPTION OR
CLINICAL DECISION SUPPORT SYSTEM IN PRODUCTION.

PRODUCTION REQUIRES LICENSED ACCESS TO AUTHORITATIVE CLINICAL DATABASES
(e.g., First Databank / FDB, DrugBank, Wolters Kluwer Medi-Span).
=============================================================================
"""

import uuid
from datetime import datetime, timezone
from app.integrations.medication_safety.base import (
    MedicationSafetyAuthError,
    MedicationSafetyProvider,
    MedicationSafetyProviderError,
    MedicationSafetyTimeoutError,
    ProviderSafetyCheckResult,
)
from app.schemas.medication_safety import (
    CheckTypeSummary,
    SafetyAlert,
    SafetyAlertSeverity,
    SafetyCheckType,
    SafetyEvaluationStatus,
    SafetyMedicationInput,
    SafetyPatientContext,
)


class MockMedicationSafetyProvider(MedicationSafetyProvider):
    """Synthetic mock provider for testing and local development.

    Exposes deterministic responses for:
    - Drug-Drug interactions (DDI)
    - Drug-Allergy cross-reactivity
    - Drug-Disease contraindications
    - Absolute contraindications (e.g. pregnancy)
    - Duplicate therapy signals
    - Simulated failures (timeout, auth, 5xx)
    """

    MOCK_PROVIDER_NAME = "HealthSetu-Synthetic-MockProvider"
    MOCK_PROVIDER_VERSION = "2026.1-DEV"
    MOCK_RULESET_VERSION = "SYNTHETIC-MOCK-v1.0"

    def __init__(self, simulate_unsupported_ddi: bool = False):
        self._simulate_unsupported_ddi = simulate_unsupported_ddi

    @property
    def provider_name(self) -> str:
        return self.MOCK_PROVIDER_NAME

    @property
    def provider_version(self) -> str:
        return self.MOCK_PROVIDER_VERSION

    @property
    def ruleset_version(self) -> str | None:
        return self.MOCK_RULESET_VERSION

    @property
    def capabilities(self) -> dict[SafetyCheckType, bool]:
        return {
            SafetyCheckType.DRUG_DRUG: not self._simulate_unsupported_ddi,
            SafetyCheckType.DRUG_ALLERGY: True,
            SafetyCheckType.DRUG_DISEASE: True,
            SafetyCheckType.CONTRAINDICATION: True,
            SafetyCheckType.DUPLICATE_THERAPY: True,
            SafetyCheckType.PREGNANCY: True,
            SafetyCheckType.RENAL: True,
            SafetyCheckType.DOSING: False,      # unsupported by mock
            SafetyCheckType.HEPATIC: False,     # unsupported by mock
            SafetyCheckType.OTHER: False,
        }

    async def evaluate_safety(
        self,
        medications: list[SafetyMedicationInput],
        patient_context: SafetyPatientContext,
        requested_checks: list[SafetyCheckType] | None = None,
    ) -> ProviderSafetyCheckResult:
        """Evaluate medications against synthetic rules and patient context."""
        
        # 1. Check for simulated failure triggers
        for med in medications:
            med_name_upper = med.name.upper()
            if "TRIGGER_TIMEOUT" in med_name_upper:
                raise MedicationSafetyTimeoutError("Simulated mock provider network timeout")
            if "TRIGGER_AUTH_ERROR" in med_name_upper:
                raise MedicationSafetyAuthError("Simulated mock provider 401 unauthorized")
            if "TRIGGER_PROVIDER_ERROR" in med_name_upper:
                raise MedicationSafetyProviderError("Simulated mock provider 500 internal server error", is_transient=True)

        checks_to_run = requested_checks or [
            SafetyCheckType.DRUG_DRUG,
            SafetyCheckType.DRUG_ALLERGY,
            SafetyCheckType.DRUG_DISEASE,
            SafetyCheckType.CONTRAINDICATION,
            SafetyCheckType.DUPLICATE_THERAPY,
        ]

        alerts: list[SafetyAlert] = []
        check_summaries: list[CheckTypeSummary] = []

        med_names_clean = [m.name.strip().lower() for m in medications]

        for check_type in checks_to_run:
            if not self.is_check_supported(check_type):
                check_summaries.append(
                    CheckTypeSummary(
                        check_type=check_type,
                        supported=False,
                        status=SafetyEvaluationStatus.NOT_SUPPORTED,
                        alert_count=0,
                        note=f"Check type {check_type.value} is not supported by {self.MOCK_PROVIDER_NAME}",
                    )
                )
                continue

            check_alerts: list[SafetyAlert] = []

            # ---------------------------------------------------------------
            # Check 1: Drug-Drug Interactions (DDI)
            # ---------------------------------------------------------------
            if check_type == SafetyCheckType.DRUG_DRUG:
                check_alerts.extend(self._evaluate_ddi(medications, med_names_clean))

            # ---------------------------------------------------------------
            # Check 2: Drug-Allergy Conflicts
            # ---------------------------------------------------------------
            elif check_type == SafetyCheckType.DRUG_ALLERGY:
                check_alerts.extend(self._evaluate_allergies(medications, patient_context.allergies))

            # ---------------------------------------------------------------
            # Check 3: Drug-Disease Interactions
            # ---------------------------------------------------------------
            elif check_type == SafetyCheckType.DRUG_DISEASE:
                check_alerts.extend(self._evaluate_drug_disease(medications, patient_context.conditions))

            # ---------------------------------------------------------------
            # Check 4: General Contraindications
            # ---------------------------------------------------------------
            elif check_type == SafetyCheckType.CONTRAINDICATION:
                check_alerts.extend(self._evaluate_contraindications(medications, patient_context))

            # ---------------------------------------------------------------
            # Check 5: Duplicate Therapy
            # ---------------------------------------------------------------
            elif check_type == SafetyCheckType.DUPLICATE_THERAPY:
                check_alerts.extend(self._evaluate_duplicate_therapy(medications, med_names_clean))

            alerts.extend(check_alerts)
            check_status = (
                SafetyEvaluationStatus.ALERT
                if any(a.severity in (SafetyAlertSeverity.CRITICAL, SafetyAlertSeverity.MAJOR) for a in check_alerts)
                else SafetyEvaluationStatus.WARNING
                if check_alerts
                else SafetyEvaluationStatus.CLEAR
            )
            check_summaries.append(
                CheckTypeSummary(
                    check_type=check_type,
                    supported=True,
                    status=check_status,
                    alert_count=len(check_alerts),
                )
            )

        # Determine overall evaluation status
        if any(s.status == SafetyEvaluationStatus.NOT_SUPPORTED for s in check_summaries) and not alerts:
            overall_status = SafetyEvaluationStatus.NOT_SUPPORTED
        elif any(a.severity == SafetyAlertSeverity.CRITICAL for a in alerts):
            overall_status = SafetyEvaluationStatus.ALERT
        elif any(a.severity == SafetyAlertSeverity.MAJOR for a in alerts):
            overall_status = SafetyEvaluationStatus.ALERT
        elif any(a.severity in (SafetyAlertSeverity.MODERATE, SafetyAlertSeverity.MINOR) for a in alerts):
            overall_status = SafetyEvaluationStatus.WARNING
        else:
            overall_status = SafetyEvaluationStatus.CLEAR

        return ProviderSafetyCheckResult(
            provider_name=self.MOCK_PROVIDER_NAME,
            provider_version=self.MOCK_PROVIDER_VERSION,
            ruleset_version=self.MOCK_RULESET_VERSION,
            alerts=alerts,
            check_summaries=check_summaries,
            status=overall_status,
        )

    # -----------------------------------------------------------------------
    # Synthetic Deterministic Evaluators
    # -----------------------------------------------------------------------

    def _evaluate_ddi(
        self, medications: list[SafetyMedicationInput], med_names: list[str]
    ) -> list[SafetyAlert]:
        alerts: list[SafetyAlert] = []
        n = len(medications)

        # Pairwise interaction rules
        ddi_rules = [
            (
                {"metformin"},
                {"contrast", "iodinated contrast", "radiopaque contrast"},
                SafetyAlertSeverity.MAJOR,
                "Metformin — Iodinated Radiopaque Contrast Interaction",
                "Intravascular administration of iodinated contrast materials in patients taking metformin "
                "may cause renal impairment, precipitating metformin accumulation and lactic acidosis.",
                "American College of Radiology (ACR) Contrast Manual / FDA Package Insert",
                "MOCK-DDI-001",
            ),
            (
                {"lisinopril", "enalapril", "ramipril"},
                {"potassium", "potassium chloride", "spironolactone"},
                SafetyAlertSeverity.MAJOR,
                "ACE Inhibitor — Potassium / Potassium-Sparing Agent Interaction",
                "Concomitant use of ACE inhibitors with potassium supplements or potassium-sparing diuretics "
                "substantially increases the risk of severe hyperkalemia, potentially leading to cardiac arrhythmias.",
                "Clinical Pharmacology Compendium / Drug Interaction Guideline",
                "MOCK-DDI-002",
            ),
            (
                {"warfarin"},
                {"aspirin", "ibuprofen", "naproxen"},
                SafetyAlertSeverity.MAJOR,
                "Warfarin — NSAID / Antiplatelet Interaction",
                "Concurrent administration of warfarin with NSAIDs significantly enhances gastrointestinal bleeding risk "
                "and inhibits platelet aggregation.",
                "Chest Antithrombotic Therapy Guidelines / FDA Black Box Warning",
                "MOCK-DDI-003",
            ),
            (
                {"sildenafil", "tadalafil"},
                {"nitroglycerin", "isosorbide dinitrate", "isosorbide mononitrate"},
                SafetyAlertSeverity.CRITICAL,
                "Phosphodiesterase-5 Inhibitor — Nitrate Absolute Contraindication",
                "Co-administration of PDE-5 inhibitors with organic nitrates produces significant and potentially fatal "
                "systemic hypotension due to amplified cyclic GMP signaling.",
                "ACC/AHA Guidelines / FDA Contraindication Warning",
                "MOCK-DDI-004",
            ),
            (
                {"methotrexate"},
                {"ibuprofen", "naproxen"},
                SafetyAlertSeverity.MAJOR,
                "Methotrexate — NSAID Renal Clearance Interaction",
                "NSAIDs may diminish renal excretion of methotrexate, causing severe bone marrow suppression and gastrointestinal toxicity.",
                "FDA Safety Communication / Prescribing Information",
                "MOCK-DDI-005",
            ),
        ]

        for i in range(n):
            for j in range(i + 1, n):
                med_a = medications[i]
                med_b = medications[j]
                name_a = med_a.name.lower()
                name_b = med_b.name.lower()

                for set1, set2, severity, title, desc, evidence, rule_id in ddi_rules:
                    match1 = any(k in name_a for k in set1) and any(k in name_b for k in set2)
                    match2 = any(k in name_b for k in set1) and any(k in name_a for k in set2)

                    if match1 or match2:
                        alerts.append(
                            SafetyAlert(
                                alert_id=f"alert-ddi-{uuid.uuid4().hex[:8]}",
                                check_type=SafetyCheckType.DRUG_DRUG,
                                severity=severity,
                                title=title,
                                description=desc,
                                medications_involved=[
                                    {"name": med_a.name, "medication_id": med_a.medication_id or "", "code": med_a.terminology_code or ""},
                                    {"name": med_b.name, "medication_id": med_b.medication_id or "", "code": med_b.terminology_code or ""},
                                ],
                                clinical_context_involved=[],
                                evidence=evidence,
                                source=self.MOCK_PROVIDER_NAME,
                                provider_rule_id=rule_id,
                            )
                        )

        return alerts

    def _evaluate_allergies(
        self, medications: list[SafetyMedicationInput], allergies: list[dict]
    ) -> list[SafetyAlert]:
        alerts: list[SafetyAlert] = []

        allergy_rules = [
            (
                {"penicillin", "beta-lactam"},
                {"amoxicillin", "ampicillin", "penicillin", "augmentin"},
                SafetyAlertSeverity.CRITICAL,
                "Beta-Lactam / Penicillin Cross-Reactivity Alert",
                "Patient has an explicitly documented penicillin/beta-lactam allergy. Administration of this penicillin "
                "derivative poses a high risk of acute type I hypersensitivity and anaphylaxis.",
                "Practice Parameters for Drug Allergy: An EAACI/AAAAI Joint Consensus",
                "MOCK-ALLERGY-001",
            ),
            (
                {"sulfa", "sulfonamide"},
                {"sulfamethoxazole", "bactrim", "septra"},
                SafetyAlertSeverity.CRITICAL,
                "Sulfonamide Antibacterial Hypersensitivity Alert",
                "Documented sulfonamide allergy. High risk of severe cutaneous adverse reactions (SCAR / Stevens-Johnson syndrome).",
                "FDA Warning / AAAAI Hypersensitivity Guidance",
                "MOCK-ALLERGY-002",
            ),
            (
                {"nsaid", "aspirin"},
                {"ibuprofen", "naproxen", "ketorolac", "aspirin"},
                SafetyAlertSeverity.MAJOR,
                "NSAID Hypersensitivity / Cross-Reactivity",
                "Documented aspirin or NSAID intolerance. Potential for severe bronchospasm, angioedema, or urticaria.",
                "EAACI NSAID Hypersensitivity Classification",
                "MOCK-ALLERGY-003",
            ),
        ]

        for allergy in allergies:
            allergen = str(allergy.get("allergen", "") or allergy.get("allergen_name", "")).lower()
            if not allergen:
                continue

            for allergy_keywords, med_keywords, severity, title, desc, evidence, rule_id in allergy_rules:
                if any(ak in allergen for ak in allergy_keywords):
                    for med in medications:
                        med_name = med.name.lower()
                        if any(mk in med_name for mk in med_keywords):
                            alerts.append(
                                SafetyAlert(
                                    alert_id=f"alert-allergy-{uuid.uuid4().hex[:8]}",
                                    check_type=SafetyCheckType.DRUG_ALLERGY,
                                    severity=severity,
                                    title=title,
                                    description=desc,
                                    medications_involved=[
                                        {"name": med.name, "medication_id": med.medication_id or "", "code": med.terminology_code or ""},
                                    ],
                                    clinical_context_involved=[
                                        {"type": "allergy", "allergen": allergen, "allergy_id": str(allergy.get("id", ""))}
                                    ],
                                    evidence=evidence,
                                    source=self.MOCK_PROVIDER_NAME,
                                    provider_rule_id=rule_id,
                                )
                            )
        return alerts

    def _evaluate_drug_disease(
        self, medications: list[SafetyMedicationInput], conditions: list[dict]
    ) -> list[SafetyAlert]:
        alerts: list[SafetyAlert] = []

        disease_rules = [
            (
                {"peptic ulcer", "gastric ulcer", "gi bleed", "ulcerative colitis"},
                {"ibuprofen", "naproxen", "ketorolac", "aspirin"},
                SafetyAlertSeverity.MAJOR,
                "NSAID — Active Peptic Ulcer Disease Contraindication",
                "NSAIDs inhibit gastroprotective prostaglandins, exacerbating active mucosal lesions and precipitating severe GI hemorrhage.",
                "ACG Guidelines for Prevention of NSAID-Related Ulcer Complications",
                "MOCK-DISEASE-001",
            ),
            (
                {"asthma", "reactive airway"},
                {"propranolol", "timolol", "nadolol"},
                SafetyAlertSeverity.MAJOR,
                "Non-Selective Beta Blocker — Asthma Bronchospasm Warning",
                "Non-cardioselective beta-adrenergic antagonism may provoke acute, refractory bronchoconstriction in asthmatic patients.",
                "GINA Global Strategy for Asthma Management",
                "MOCK-DISEASE-002",
            ),
            (
                {"chronic kidney disease", "renal failure", "renal impairment"},
                {"gentamicin", "tobramycin", "amikacin"},
                SafetyAlertSeverity.MAJOR,
                "Aminoglycoside — Renal Impairment Nephrotoxicity Alert",
                "Aminoglycosides exhibit dose-dependent proximal tubular toxicity, requiring strict therapeutic drug monitoring or dose reduction.",
                "KDIGO Clinical Practice Guideline for Acute Kidney Injury",
                "MOCK-DISEASE-003",
            ),
        ]

        for condition in conditions:
            cond_name = str(condition.get("diagnosis", "") or condition.get("condition_name", "")).lower()
            if not cond_name:
                continue

            for dis_keywords, med_keywords, severity, title, desc, evidence, rule_id in disease_rules:
                if any(dk in cond_name for dk in dis_keywords):
                    for med in medications:
                        med_name = med.name.lower()
                        if any(mk in med_name for mk in med_keywords):
                            alerts.append(
                                SafetyAlert(
                                    alert_id=f"alert-disease-{uuid.uuid4().hex[:8]}",
                                    check_type=SafetyCheckType.DRUG_DISEASE,
                                    severity=severity,
                                    title=title,
                                    description=desc,
                                    medications_involved=[
                                        {"name": med.name, "medication_id": med.medication_id or "", "code": med.terminology_code or ""},
                                    ],
                                    clinical_context_involved=[
                                        {"type": "condition", "condition": cond_name, "condition_id": str(condition.get("id", ""))}
                                    ],
                                    evidence=evidence,
                                    source=self.MOCK_PROVIDER_NAME,
                                    provider_rule_id=rule_id,
                                )
                            )
        return alerts

    def _evaluate_contraindications(
        self, medications: list[SafetyMedicationInput], context: SafetyPatientContext
    ) -> list[SafetyAlert]:
        alerts: list[SafetyAlert] = []

        # Example: Pediatric contraindication
        if context.age_years is not None and context.age_years < 18:
            for med in medications:
                if "aspirin" in med.name.lower():
                    alerts.append(
                        SafetyAlert(
                            alert_id=f"alert-contra-{uuid.uuid4().hex[:8]}",
                            check_type=SafetyCheckType.CONTRAINDICATION,
                            severity=SafetyAlertSeverity.CRITICAL,
                            title="Aspirin — Pediatric Reye Syndrome Contraindication",
                            description="Aspirin is strictly contraindicated in pediatric patients with viral symptoms due to the risk of Reye's syndrome.",
                            medications_involved=[{"name": med.name, "medication_id": med.medication_id or "", "code": med.terminology_code or ""}],
                            clinical_context_involved=[{"type": "age", "age_years": str(context.age_years)}],
                            evidence="CDC / American Academy of Pediatrics Guidance",
                            source=self.MOCK_PROVIDER_NAME,
                            provider_rule_id="MOCK-CONTRA-001",
                        )
                    )
        return alerts

    def _evaluate_duplicate_therapy(
        self, medications: list[SafetyMedicationInput], med_names: list[str]
    ) -> list[SafetyAlert]:
        alerts: list[SafetyAlert] = []

        therapeutic_classes = [
            (
                "Statin (HMG-CoA Reductase Inhibitor)",
                ["atorvastatin", "rosuvastatin", "simvastatin", "pravastatin", "lovastatin"],
                SafetyAlertSeverity.MODERATE,
                "Duplicate Statin Therapy Alert",
                "Concurrent prescription of multiple HMG-CoA reductase inhibitors offers no added clinical efficacy "
                "and significantly elevates the risk of myopathy, transaminitis, and rhabdomyolysis.",
                "ACC/AHA Cholesterol Clinical Practice Guidelines",
                "MOCK-DUP-001",
            ),
            (
                "Proton Pump Inhibitor (PPI)",
                ["omeprazole", "pantoprazole", "esomeprazole", "lansoprazole", "rabeprazole"],
                SafetyAlertSeverity.MODERATE,
                "Duplicate Proton Pump Inhibitor Therapy",
                "Simultaneous administration of two PPIs constitutes therapeutic duplication without proven additive gastric acid suppression.",
                "ACG Clinical Guidelines on Gastroesophageal Reflux Disease",
                "MOCK-DUP-002",
            ),
        ]

        for class_name, drug_list, severity, title, desc, evidence, rule_id in therapeutic_classes:
            matched_meds = [m for m in medications if any(d in m.name.lower() for d in drug_list)]
            if len(matched_meds) > 1:
                alerts.append(
                    SafetyAlert(
                        alert_id=f"alert-dup-{uuid.uuid4().hex[:8]}",
                        check_type=SafetyCheckType.DUPLICATE_THERAPY,
                        severity=severity,
                        title=title,
                        description=desc,
                        medications_involved=[
                            {"name": m.name, "medication_id": m.medication_id or "", "code": m.terminology_code or ""}
                            for m in matched_meds
                        ],
                        clinical_context_involved=[{"therapeutic_class": class_name}],
                        evidence=evidence,
                        source=self.MOCK_PROVIDER_NAME,
                        provider_rule_id=rule_id,
                    )
                )

        return alerts
