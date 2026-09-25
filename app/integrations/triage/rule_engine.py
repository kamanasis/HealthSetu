"""Deterministic clinical triage rule engine (Phase 8).

Implements the HealthSetu Clinical Triage Protocol (v1.0.0).
Provides transparent, auditable, and rule-based urgency classification
without medical diagnosis.
"""

from typing import Any
from app.integrations.triage.base import (
    TriageRuleEngine,
    TriageEvaluationContext,
    TriageEngineResult,
)
from app.schemas.symptom import SymptomItemCreate, SymptomSeverity
from app.schemas.triage import (
    TriageUrgency,
    TriageStatus,
    TriageReason,
    MissingInformationItem,
)


class HealthSetuDeterministicTriageEngine(TriageRuleEngine):
    """Deterministic, protocol-driven clinical triage engine.

    Protocol Source: 'HealthSetu Clinical Triage Protocol'
    Protocol Version: '1.0.0'

    Evaluates physiological red flags, structured symptom combinations,
    vitals thresholds, and high-risk patient context deterministically.
    """

    def __init__(self, rule_set_name: str = "healthsetu_emergency_triage_v1", rule_set_version: str = "1.0.0"):
        self._rule_set_name = rule_set_name
        self._rule_set_version = rule_set_version

    @property
    def rule_set_name(self) -> str:
        return self._rule_set_name

    @property
    def rule_set_version(self) -> str:
        return self._rule_set_version

    async def evaluate(self, context: TriageEvaluationContext) -> TriageEngineResult:
        """Evaluate patient symptoms, vitals, and context against clinical protocol rules."""
        reasons: list[TriageReason] = []
        missing_info: list[MissingInformationItem] = []
        factors: list[str] = []

        symptoms_text = [s.symptom.lower().strip() for s in context.symptoms]
        severities = [s.severity for s in context.symptoms if s.severity]
        has_critical_severity = any(sev == SymptomSeverity.CRITICAL for sev in severities)
        has_severe_severity = any(sev in (SymptomSeverity.SEVERE, SymptomSeverity.CRITICAL) for sev in severities)

        # Extract vitals safely
        vitals = context.vitals or {}
        spo2 = vitals.get("oxygen_saturation") or vitals.get("spo2")
        heart_rate = vitals.get("heart_rate") or vitals.get("pulse")
        systolic_bp = vitals.get("systolic_bp") or vitals.get("systolic")
        diastolic_bp = vitals.get("diastolic_bp") or vitals.get("diastolic")
        resp_rate = vitals.get("respiratory_rate") or vitals.get("rr")
        temp_c = vitals.get("temperature_c") or vitals.get("temperature")

        # Document factors considered
        for s in context.symptoms:
            factor_desc = f"Symptom: {s.symptom}"
            if s.severity:
                factor_desc += f" (Severity: {s.severity.value})"
            if s.onset:
                factor_desc += f" (Onset: {s.onset})"
            factors.append(factor_desc)

        if vitals:
            v_desc = ", ".join(f"{k}: {v}" for k, v in vitals.items() if v is not None)
            factors.append(f"Recorded Vitals: {v_desc}")

        if context.known_conditions:
            factors.append(f"Documented Conditions: {', '.join(context.known_conditions)}")
        if context.allergies:
            factors.append(f"Documented Allergies: {', '.join(context.allergies)}")
        if context.age is not None:
            factors.append(f"Patient Age: {context.age}")

        # -------------------------------------------------------------------
        # 1. EMERGENCY (RED) PROTOCOL RULES
        # -------------------------------------------------------------------

        # Rule RED-01: Severe Hypoxia / Respiratory Failure
        is_dyspneic = any(
            any(w in st for w in ["shortness of breath", "breathing difficulty", "dyspnea", "gasping", "breathless"])
            for st in symptoms_text
        )
        if spo2 is not None and spo2 < 90:
            reasons.append(
                TriageReason(
                    rule_id="RULE_RED_HYPOXIA",
                    reason_code="RULE_RED_CRITICAL_SPO2",
                    description=f"Critically low oxygen saturation ({spo2}% < 90%) indicates severe hypoxia.",
                    source=self.rule_set_name,
                    urgency_assigned=TriageUrgency.EMERGENCY,
                )
            )

        if resp_rate is not None and (resp_rate >= 32 or resp_rate < 8):
            reasons.append(
                TriageReason(
                    rule_id="RULE_RED_RESP_RATE",
                    reason_code="RULE_RED_CRITICAL_RR",
                    description=f"Critical respiratory rate ({resp_rate} breaths/min) indicates respiratory compromise.",
                    source=self.rule_set_name,
                    urgency_assigned=TriageUrgency.EMERGENCY,
                )
            )

        # Rule RED-02: Acute Coronary / Cardiac Red Flags
        is_chest_pain = any("chest pain" in st or "chest pressure" in st or "substernal" in st for st in symptoms_text)
        has_cardiac_radiation = any(
            any(
                rad in (s.location or "").lower() or any(rad in a.lower() for a in s.associated_symptoms)
                for rad in ["jaw", "arm", "shoulder", "back"]
            )
            for s in context.symptoms
        )
        has_diaphoresis = any(
            "sweating" in st or "diaphoresis" in st or any("sweat" in a.lower() for a in s.associated_symptoms)
            for s in context.symptoms
            for st in [s.symptom.lower()]
        )
        has_cardiac_history = any(
            any(ch in c.lower() for ch in ["cad", "coronary", "heart disease", "infarction", "angina", "stent"])
            for c in context.known_conditions
        )

        if is_chest_pain:
            if has_cardiac_radiation or has_diaphoresis or has_critical_severity or (
                (context.age is not None and context.age >= 45) and has_cardiac_history
            ):
                reasons.append(
                    TriageReason(
                        rule_id="RULE_RED_ACUTE_CORONARY_RISK",
                        reason_code="RULE_RED_CARDIAC_RED_FLAGS",
                        description="Chest discomfort accompanied by high-risk associated features (radiation, diaphoresis, or cardiac history).",
                        source=self.rule_set_name,
                        urgency_assigned=TriageUrgency.EMERGENCY,
                    )
                )

        # Rule RED-03: Hemodynamic Instability / Shock
        if systolic_bp is not None and systolic_bp < 90:
            if (heart_rate is not None and heart_rate > 115) or any("syncope" in st or "fainted" in st or "collapse" in st for st in symptoms_text):
                reasons.append(
                    TriageReason(
                        rule_id="RULE_RED_HEMODYNAMIC_SHOCK",
                        reason_code="RULE_RED_HYPOTENSION_SHOCK",
                        description=f"Severe hypotension (systolic BP {systolic_bp} mmHg) with tachycardia or syncope indicates shock risk.",
                        source=self.rule_set_name,
                        urgency_assigned=TriageUrgency.EMERGENCY,
                    )
                )

        # Rule RED-04: Acute Neurological Deficit (Stroke Alert)
        has_neuro_deficit = any(
            any(kw in st for kw in ["facial droop", "slurred speech", "one-sided weakness", "hemiparesis", "sudden numbness", "loss of vision"])
            for st in symptoms_text
        )
        if has_neuro_deficit:
            reasons.append(
                TriageReason(
                    rule_id="RULE_RED_ACUTE_NEURO_DEFICIT",
                    reason_code="RULE_RED_STROKE_SYMPTOM",
                    description="Sudden acute focal neurological signs reported requiring immediate emergency stroke evaluation.",
                    source=self.rule_set_name,
                    urgency_assigned=TriageUrgency.EMERGENCY,
                )
            )

        # Rule RED-05: Anaphylaxis Red Flag
        has_throat_swelling = any(
            any(kw in st for kw in ["throat swelling", "lip swelling", "tongue swelling", "stridor", "unable to swallow"])
            for st in symptoms_text
        )
        if has_throat_swelling and (is_dyspneic or len(context.allergies) > 0):
            reasons.append(
                TriageReason(
                    rule_id="RULE_RED_ANAPHYLAXIS",
                    reason_code="RULE_RED_AIRWAY_SWELLING",
                    description="Upper airway swelling with respiratory involvement or allergy history indicates suspected anaphylaxis.",
                    source=self.rule_set_name,
                    urgency_assigned=TriageUrgency.EMERGENCY,
                )
            )

        # If any emergency rule triggered, return EMERGENCY immediately
        emergency_reasons = [r for r in reasons if r.urgency_assigned == TriageUrgency.EMERGENCY]
        if emergency_reasons:
            return TriageEngineResult(
                urgency=TriageUrgency.EMERGENCY,
                status=TriageStatus.COMPLETED,
                reasons=emergency_reasons,
                missing_information=[],
                factors_considered=factors,
                urgency_rationale=(
                    f"Configured clinical protocol triggered {len(emergency_reasons)} emergency red-flag criteria: "
                    + "; ".join(r.description for r in emergency_reasons)
                ),
                recommended_level_of_care="Emergency Department / Immediate Ambulance (108 / 911)",
                immediate_instruction="Seek emergency medical care immediately. Call local emergency services now.",
                rule_set=self.rule_set_name,
                rule_set_version=self.rule_set_version,
            )

        # -------------------------------------------------------------------
        # 2. INSUFFICIENT INFORMATION CHECKS (Section 15, 23)
        # Check if missing physiological measurements block a safe assessment
        # -------------------------------------------------------------------
        if is_dyspneic and spo2 is None:
            missing_info.append(
                MissingInformationItem(
                    field="oxygen_saturation",
                    importance="REQUIRED",
                    description="Patient reports shortness of breath, but oxygen saturation (SpO2) is not provided.",
                )
            )

        if (is_chest_pain or any("palpitation" in st for st in symptoms_text)) and (heart_rate is None or systolic_bp is None):
            missing_info.append(
                MissingInformationItem(
                    field="blood_pressure_and_heart_rate",
                    importance="REQUIRED",
                    description="Cardiovascular symptoms reported without vital hemodynamic signs (blood pressure and heart rate).",
                )
            )

        if any(m.importance == "REQUIRED" for m in missing_info):
            return TriageEngineResult(
                urgency=TriageUrgency.URGENT,  # Default caution urgency when required data missing
                status=TriageStatus.INSUFFICIENT_INFORMATION,
                reasons=[
                    TriageReason(
                        rule_id="RULE_INSUFFICIENT_CRITICAL_VITALS",
                        reason_code="RULE_INCOMPLETE_CLINICAL_DATA",
                        description="Key physiological measurements required by clinical protocol are unavailable.",
                        source=self.rule_set_name,
                        urgency_assigned=TriageUrgency.URGENT,
                    )
                ],
                missing_information=missing_info,
                factors_considered=factors,
                urgency_rationale=(
                    "The triage protocol identified reported symptoms requiring physiological confirmation. "
                    "Incomplete clinical data prevents a definitive risk exclusion without guessing."
                ),
                recommended_level_of_care="Urgent Care or Primary Care for in-person vital assessment",
                immediate_instruction="Prompt medical evaluation is recommended to measure vital signs and assess condition.",
                rule_set=self.rule_set_name,
                rule_set_version=self.rule_set_version,
            )

        # -------------------------------------------------------------------
        # 3. URGENT (YELLOW) PROTOCOL RULES
        # -------------------------------------------------------------------

        # Rule URGENT-01: High Fever in Vulnerable Patients or Severe Hyperpyrexia
        if temp_c is not None:
            if temp_c >= 39.5:
                reasons.append(
                    TriageReason(
                        rule_id="RULE_URGENT_SEVERE_HYPERPYREXIA",
                        reason_code="RULE_URGENT_TEMP_CRITICAL",
                        description=f"High fever ({temp_c}°C >= 39.5°C) warrants urgent physician evaluation.",
                        source=self.rule_set_name,
                        urgency_assigned=TriageUrgency.URGENT,
                    )
                )
            elif temp_c >= 38.5 and (
                (context.age is not None and (context.age <= 2 or context.age >= 65))
                or any("immuno" in c.lower() or "chemo" in c.lower() for c in context.known_conditions)
            ):
                reasons.append(
                    TriageReason(
                        rule_id="RULE_URGENT_FEVER_VULNERABLE",
                        reason_code="RULE_URGENT_FEVER_AGE_RISK",
                        description=f"Fever ({temp_c}°C) in vulnerable patient (age {context.age} or immunosuppressed).",
                        source=self.rule_set_name,
                        urgency_assigned=TriageUrgency.URGENT,
                    )
                )

        # Rule URGENT-02: Severe Isolated Hypertension
        if systolic_bp is not None and (systolic_bp >= 180 or (diastolic_bp is not None and diastolic_bp >= 110)):
            reasons.append(
                TriageReason(
                    rule_id="RULE_URGENT_SEVERE_HYPERTENSION",
                    reason_code="RULE_URGENT_BP_STAGE_3",
                    description=f"Markedly elevated blood pressure ({systolic_bp}/{diastolic_bp or '?'} mmHg) requires prompt assessment.",
                    source=self.rule_set_name,
                    urgency_assigned=TriageUrgency.URGENT,
                )
            )

        # Rule URGENT-03: Marked Tachycardia
        if heart_rate is not None and heart_rate >= 130:
            reasons.append(
                TriageReason(
                    rule_id="RULE_URGENT_TACHYCARDIA",
                    reason_code="RULE_URGENT_PULSE_HIGH",
                    description=f"Persistent resting tachycardia ({heart_rate} bpm >= 130) warrants prompt medical review.",
                    source=self.rule_set_name,
                    urgency_assigned=TriageUrgency.URGENT,
                )
            )

        # Rule URGENT-04: Severe Uncontrolled Pain
        if has_severe_severity:
            reasons.append(
                TriageReason(
                    rule_id="RULE_URGENT_SEVERE_SYMPTOM",
                    reason_code="RULE_URGENT_INTENSE_SYMPTOM",
                    description="Reported symptom severity is SEVERE, requiring timely clinician examination.",
                    source=self.rule_set_name,
                    urgency_assigned=TriageUrgency.URGENT,
                )
            )

        # Rule URGENT-05: Stable Shortness of Breath (SpO2 normal but dyspneic)
        if is_dyspneic and spo2 is not None and spo2 >= 90:
            reasons.append(
                TriageReason(
                    rule_id="RULE_URGENT_MODERATE_DYSPNEA",
                    reason_code="RULE_URGENT_DYSPNEA_STABLE",
                    description=f"Breathing difficulty reported despite normal oxygen saturation ({spo2}%).",
                    source=self.rule_set_name,
                    urgency_assigned=TriageUrgency.URGENT,
                )
            )

        # Check for urgent result
        urgent_reasons = [r for r in reasons if r.urgency_assigned == TriageUrgency.URGENT]
        if urgent_reasons:
            return TriageEngineResult(
                urgency=TriageUrgency.URGENT,
                status=TriageStatus.COMPLETED,
                reasons=urgent_reasons,
                missing_information=missing_info,
                factors_considered=factors,
                urgency_rationale=(
                    f"Configured clinical protocol triggered {len(urgent_reasons)} urgent criteria: "
                    + "; ".join(r.description for r in urgent_reasons)
                ),
                recommended_level_of_care="Urgent Care Clinic or Same-Day Physician Consultation",
                immediate_instruction="Seek medical attention within several hours. If symptoms rapidly worsen, proceed to emergency services.",
                rule_set=self.rule_set_name,
                rule_set_version=self.rule_set_version,
            )

        # -------------------------------------------------------------------
        # 4. SAME_DAY (GREEN) PROTOCOL RULES
        # -------------------------------------------------------------------
        has_moderate_severity = any(sev == SymptomSeverity.MODERATE for sev in severities)
        has_mild_fever = temp_c is not None and 37.8 <= temp_c < 38.5
        is_subacute = any(
            any(w in (s.duration or "").lower() for w in ["days", "week", "persistent"])
            for s in context.symptoms
        )

        if has_moderate_severity or has_mild_fever or is_subacute or len(context.symptoms) >= 3:
            reasons.append(
                TriageReason(
                    rule_id="RULE_SAME_DAY_MODERATE_SYMPTOM",
                    reason_code="RULE_SAME_DAY_ASSESSMENT",
                    description="Moderate symptom presentation or subacute duration warrants same-day medical assessment.",
                    source=self.rule_set_name,
                    urgency_assigned=TriageUrgency.SAME_DAY,
                )
            )
            return TriageEngineResult(
                urgency=TriageUrgency.SAME_DAY,
                status=TriageStatus.COMPLETED,
                reasons=reasons,
                missing_information=missing_info,
                factors_considered=factors,
                urgency_rationale="Moderate symptom severity without acute hemodynamic compromise indicates same-day clinical review.",
                recommended_level_of_care="Outpatient Primary Care Clinic (Within 24 Hours)",
                immediate_instruction="Schedule an appointment with a healthcare professional today.",
                rule_set=self.rule_set_name,
                rule_set_version=self.rule_set_version,
            )

        # -------------------------------------------------------------------
        # 5. ROUTINE (BLUE) PROTOCOL RULES
        # -------------------------------------------------------------------
        if len(context.symptoms) > 0:
            reasons.append(
                TriageReason(
                    rule_id="RULE_ROUTINE_MILD_PRESENTATION",
                    reason_code="RULE_ROUTINE_OUTPATIENT",
                    description="Mild, localized symptom presentation without red flags or vital derangements.",
                    source=self.rule_set_name,
                    urgency_assigned=TriageUrgency.ROUTINE,
                )
            )
            return TriageEngineResult(
                urgency=TriageUrgency.ROUTINE,
                status=TriageStatus.COMPLETED,
                reasons=reasons,
                missing_information=missing_info,
                factors_considered=factors,
                urgency_rationale="Reported symptoms meet routine outpatient evaluation criteria without indicators for acute intervention.",
                recommended_level_of_care="Routine Outpatient Clinic / Primary Care Physician",
                immediate_instruction="Book a standard non-urgent appointment with your doctor.",
                rule_set=self.rule_set_name,
                rule_set_version=self.rule_set_version,
            )

        # -------------------------------------------------------------------
        # 6. SELF_CARE / MONITOR
        # -------------------------------------------------------------------
        reasons.append(
            TriageReason(
                rule_id="RULE_SELF_CARE_BASELINE",
                reason_code="RULE_SELF_CARE_MONITOR",
                description="No acute active symptoms or physiological abnormalities detected.",
                source=self.rule_set_name,
                urgency_assigned=TriageUrgency.SELF_CARE,
            )
        )
        return TriageEngineResult(
            urgency=TriageUrgency.SELF_CARE,
            status=TriageStatus.COMPLETED,
            reasons=reasons,
            missing_information=missing_info,
            factors_considered=factors,
            urgency_rationale="No active acute symptoms or warning signs detected.",
            recommended_level_of_care="Self-Care and Symptom Monitoring",
            immediate_instruction="Monitor condition at home. If new or worsening symptoms develop, seek medical advice.",
            rule_set=self.rule_set_name,
            rule_set_version=self.rule_set_version,
        )
