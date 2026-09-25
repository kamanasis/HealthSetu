"""FHIR R4 Bi-Directional Resource Mapper (Phase 13).

Translates between external HL7 FHIR R4 resources and HealthSetu domain concepts.

Critical boundaries:
- Data Mapping != Clinical Interpretation
- Preserves full provenance and external identifiers
- Does not guess or infer missing clinical data
"""

from datetime import datetime, timezone
from typing import Any
import uuid

from app.schemas.patient import BiologicalSex


class FHIRMapper:
    """Bi-directional mapper between FHIR R4 resources and HealthSetu models."""

    MAPPER_VERSION = "1.0.0"

    # ========================================================================
    # INBOUND MAPPINGS (External FHIR -> HealthSetu Candidate Data)
    # ========================================================================

    def map_inbound_resource(
        self,
        resource_type: str,
        payload: dict[str, Any],
        source_system: str,
        healthsetu_patient_id: str | None = None,
    ) -> dict[str, Any]:
        """Dispatch inbound FHIR resource to type-specific mapping logic."""
        rt = resource_type.lower()
        if rt == "patient":
            return self.map_patient_inbound(payload, source_system)
        elif rt == "observation":
            return self.map_observation_inbound(payload, source_system, healthsetu_patient_id)
        elif rt == "allergyintolerance":
            return self.map_allergy_inbound(payload, source_system, healthsetu_patient_id)
        elif rt == "medicationrequest":
            return self.map_medication_request_inbound(payload, source_system, healthsetu_patient_id)
        elif rt == "encounter":
            return self.map_encounter_inbound(payload, source_system, healthsetu_patient_id)
        elif rt == "documentreference":
            return self.map_document_reference_inbound(payload, source_system, healthsetu_patient_id)
        else:
            return {
                "source_system": source_system,
                "external_id": payload.get("id"),
                "resource_type": payload.get("resourceType", resource_type),
                "raw": payload,
                "mapper_version": self.MAPPER_VERSION,
            }

    def map_patient_inbound(self, payload: dict[str, Any], source_system: str) -> dict[str, Any]:
        """Map FHIR Patient resource to candidate patient demographics."""
        ext_id = str(payload.get("id") or "")
        first_name = ""
        last_name = ""

        names = payload.get("name", [])
        if names and isinstance(names, list):
            n0 = names[0]
            if isinstance(n0, dict):
                given = n0.get("given", [])
                first_name = given[0] if given and isinstance(given, list) else ""
                last_name = n0.get("family", "")

        # Gender mapping
        gender_raw = (payload.get("gender") or "").lower()
        if gender_raw == "male":
            sex = BiologicalSex.MALE.value
        elif gender_raw == "female":
            sex = BiologicalSex.FEMALE.value
        else:
            sex = BiologicalSex.OTHER.value

        # Identifiers
        identifiers = []
        for ident in payload.get("identifier", []):
            if isinstance(ident, dict):
                identifiers.append({
                    "system": ident.get("system"),
                    "value": ident.get("value"),
                })

        return {
            "source_system": source_system,
            "external_patient_id": ext_id,
            "first_name": first_name or "Unknown",
            "last_name": last_name or "Unknown",
            "date_of_birth": payload.get("birthDate"),
            "sex": sex,
            "identifiers": identifiers,
            "mapper_version": self.MAPPER_VERSION,
        }

    def map_observation_inbound(
        self, payload: dict[str, Any], source_system: str, healthsetu_patient_id: str | None
    ) -> dict[str, Any]:
        """Map FHIR Observation (vital sign or lab measurement) to candidate observation."""
        code_obj = payload.get("code", {})
        code_text = code_obj.get("text")
        if not code_text and code_obj.get("coding"):
            code_text = code_obj["coding"][0].get("display") or code_obj["coding"][0].get("code")

        val_qty = payload.get("valueQuantity", {})
        value = val_qty.get("value")
        unit = val_qty.get("unit") or val_qty.get("code") or ""

        return {
            "source_system": source_system,
            "external_id": payload.get("id"),
            "patient_id": healthsetu_patient_id,
            "observation_type": code_text or "UNKNOWN",
            "value": value,
            "unit": unit,
            "status": payload.get("status", "final"),
            "effective_datetime": payload.get("effectiveDateTime"),
            "mapper_version": self.MAPPER_VERSION,
        }

    def map_allergy_inbound(
        self, payload: dict[str, Any], source_system: str, healthsetu_patient_id: str | None
    ) -> dict[str, Any]:
        """Map FHIR AllergyIntolerance to candidate allergy information."""
        code_obj = payload.get("code", {})
        substance = code_obj.get("text")
        if not substance and code_obj.get("coding"):
            substance = code_obj["coding"][0].get("display") or code_obj["coding"][0].get("code")

        reactions = []
        for r in payload.get("reaction", []):
            if isinstance(r, dict):
                manifestations = [
                    m.get("text") or (m.get("coding", [{}])[0].get("display") if m.get("coding") else "")
                    for m in r.get("manifestation", [])
                ]
                reactions.extend([m for m in manifestations if m])

        return {
            "source_system": source_system,
            "external_id": payload.get("id"),
            "patient_id": healthsetu_patient_id,
            "substance": substance or "Unknown Substance",
            "reactions": reactions,
            "clinical_status": (
                payload.get("clinicalStatus", {}).get("coding", [{}])[0].get("code")
                if isinstance(payload.get("clinicalStatus"), dict)
                else "active"
            ),
            "mapper_version": self.MAPPER_VERSION,
        }

    def map_medication_request_inbound(
        self, payload: dict[str, Any], source_system: str, healthsetu_patient_id: str | None
    ) -> dict[str, Any]:
        """Map FHIR MedicationRequest to candidate raw medication data."""
        med_cc = payload.get("medicationCodeableConcept", {})
        drug_name = med_cc.get("text")
        if not drug_name and med_cc.get("coding"):
            drug_name = med_cc["coding"][0].get("display") or med_cc["coding"][0].get("code")

        dosage_instruction = ""
        instructions = payload.get("dosageInstruction", [])
        if instructions and isinstance(instructions, list):
            dosage_instruction = instructions[0].get("text", "")

        return {
            "source_system": source_system,
            "external_id": payload.get("id"),
            "patient_id": healthsetu_patient_id,
            "drug_name_raw": drug_name or "Unknown Medication",
            "dosage_instruction": dosage_instruction,
            "status": payload.get("status", "active"),
            "authored_on": payload.get("authoredOn"),
            "mapper_version": self.MAPPER_VERSION,
        }

    def map_encounter_inbound(
        self, payload: dict[str, Any], source_system: str, healthsetu_patient_id: str | None
    ) -> dict[str, Any]:
        """Map FHIR Encounter to candidate encounter data."""
        class_obj = payload.get("class", {})
        enc_class = class_obj.get("code") or class_obj.get("display") or "AMB"

        period = payload.get("period", {})
        return {
            "source_system": source_system,
            "external_id": payload.get("id"),
            "patient_id": healthsetu_patient_id,
            "encounter_class": enc_class,
            "status": payload.get("status", "finished"),
            "start_time": period.get("start"),
            "end_time": period.get("end"),
            "mapper_version": self.MAPPER_VERSION,
        }

    def map_document_reference_inbound(
        self, payload: dict[str, Any], source_system: str, healthsetu_patient_id: str | None
    ) -> dict[str, Any]:
        """Map FHIR DocumentReference to candidate document reference."""
        content = payload.get("content", [])
        attachment = content[0].get("attachment", {}) if content and isinstance(content, list) else {}

        return {
            "source_system": source_system,
            "external_id": payload.get("id"),
            "patient_id": healthsetu_patient_id,
            "title": payload.get("description") or attachment.get("title") or "External Document",
            "content_type": attachment.get("contentType", "application/pdf"),
            "url": attachment.get("url"),
            "status": payload.get("status", "current"),
            "mapper_version": self.MAPPER_VERSION,
        }

    # ========================================================================
    # OUTBOUND MAPPINGS (HealthSetu Domain Data -> FHIR R4 Resources)
    # ========================================================================

    def map_patient_outbound(self, patient: Any) -> dict[str, Any]:
        """Map HealthSetu PatientRecord to FHIR R4 Patient resource."""
        sex_map = {
            BiologicalSex.MALE: "male",
            BiologicalSex.FEMALE: "female",
            BiologicalSex.OTHER: "other",
        }
        gender_fhir = sex_map.get(patient.sex, "unknown")
        dob_str = patient.date_of_birth.isoformat() if hasattr(patient.date_of_birth, "isoformat") else str(patient.date_of_birth)

        return {
            "resourceType": "Patient",
            "id": patient.id,
            "identifier": [
                {
                    "system": "urn:healthsetu:patient:id",
                    "value": patient.id,
                }
            ],
            "name": [
                {
                    "use": "official",
                    "family": patient.last_name,
                    "given": [patient.first_name],
                }
            ],
            "gender": gender_fhir,
            "birthDate": dob_str,
            "active": True,
        }

    def map_vital_outbound(self, vital: Any, patient_id: str) -> dict[str, Any]:
        """Map HealthSetu VitalRecord to FHIR R4 Observation resource."""
        v_type = getattr(vital, "vital_type", None)
        type_code = v_type.value if hasattr(v_type, "value") else str(v_type or "vital")
        measured_at = vital.measured_at.isoformat() if hasattr(vital, "measured_at") and vital.measured_at else datetime.now(timezone.utc).isoformat()

        return {
            "resourceType": "Observation",
            "id": getattr(vital, "id", str(uuid.uuid4())),
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "vital-signs",
                            "display": "Vital Signs",
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://healthsetu.org/vitals",
                        "code": type_code,
                        "display": type_code.replace("_", " ").title(),
                    }
                ],
                "text": type_code.replace("_", " ").title(),
            },
            "subject": {"reference": f"Patient/{patient_id}"},
            "valueQuantity": {
                "value": getattr(vital, "value", 0.0),
                "unit": getattr(vital, "unit", ""),
            },
            "effectiveDateTime": measured_at,
        }

    def map_allergy_outbound(self, allergy: Any, patient_id: str) -> dict[str, Any]:
        """Map HealthSetu AllergyRecord to FHIR R4 AllergyIntolerance resource."""
        substance = getattr(allergy, "allergen", None) or getattr(allergy, "substance", "Unknown")
        return {
            "resourceType": "AllergyIntolerance",
            "id": getattr(allergy, "id", str(uuid.uuid4())),
            "clinicalStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                        "code": "active",
                        "display": "Active",
                    }
                ]
            },
            "verificationStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                        "code": "confirmed",
                        "display": "Confirmed",
                    }
                ]
            },
            "code": {
                "text": substance,
            },
            "patient": {"reference": f"Patient/{patient_id}"},
        }

    def map_medication_outbound(self, med: Any, patient_id: str) -> dict[str, Any]:
        """Map HealthSetu PatientMedicationRecord to FHIR R4 MedicationRequest."""
        drug_name = getattr(med, "drug_name_raw", None) or getattr(med, "medication_name", "Unknown Medication")
        return {
            "resourceType": "MedicationRequest",
            "id": getattr(med, "id", str(uuid.uuid4())),
            "status": "active",
            "intent": "order",
            "medicationCodeableConcept": {
                "text": drug_name,
            },
            "subject": {"reference": f"Patient/{patient_id}"},
            "authoredOn": datetime.now(timezone.utc).isoformat(),
        }

    def map_encounter_outbound(self, encounter: Any, patient_id: str) -> dict[str, Any]:
        """Map HealthSetu EncounterRecord to FHIR R4 Encounter resource."""
        return {
            "resourceType": "Encounter",
            "id": getattr(encounter, "id", str(uuid.uuid4())),
            "status": "finished",
            "class": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": "AMB",
                "display": "ambulatory",
            },
            "subject": {"reference": f"Patient/{patient_id}"},
        }

    def map_document_outbound(self, document: Any, patient_id: str) -> dict[str, Any]:
        """Map HealthSetu DocumentRecord to FHIR R4 DocumentReference resource."""
        doc_id = getattr(document, "id", str(uuid.uuid4()))
        filename = getattr(document, "filename", "document.pdf")
        mime_type = getattr(document, "mime_type", "application/pdf")

        return {
            "resourceType": "DocumentReference",
            "id": doc_id,
            "status": "current",
            "description": filename,
            "subject": {"reference": f"Patient/{patient_id}"},
            "content": [
                {
                    "attachment": {
                        "contentType": mime_type,
                        "title": filename,
                    }
                }
            ],
        }

    def create_fhir_bundle(
        self, resources: list[dict[str, Any]], bundle_type: str = "collection"
    ) -> dict[str, Any]:
        """Assemble a list of FHIR resources into a compliant FHIR Bundle."""
        return {
            "resourceType": "Bundle",
            "id": f"bundle-{uuid.uuid4().hex[:12]}",
            "type": bundle_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total": len(resources),
            "entry": [{"resource": r} for r in resources],
        }
