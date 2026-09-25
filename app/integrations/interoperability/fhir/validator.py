"""FHIR R4 Resource Validator (Phase 13).

Enforces structural and schema invariants for incoming and outgoing HL7 FHIR R4
resources without guessing clinical intent or mutating input payloads.
"""

from datetime import date
from typing import Any

from app.core.exceptions import (
    InvalidFHIRResourceException,
    UnsupportedFHIRVersionException,
    UnsupportedResourceTypeException,
)
from app.schemas.interoperability import FHIRVersion, SupportedFHIRResourceType


VALID_GENDERS = {"male", "female", "other", "unknown"}
VALID_OBSERVATION_STATUSES = {
    "registered", "preliminary", "final", "amended", "corrected", "cancelled", "entered-in-error", "unknown"
}
VALID_ALLERGY_CLINICAL_STATUSES = {"active", "recurrence", "relapse", "inactive", "resolved"}
VALID_MEDICATION_REQUEST_STATUSES = {
    "active", "on-hold", "cancelled", "completed", "entered-in-error", "stopped", "draft", "unknown"
}


class FHIRValidator:
    """Validates structural correctness of FHIR R4 resources."""

    def validate_resource(self, payload: dict[str, Any], expected_type: str | None = None) -> list[str]:
        """Validate resource against FHIR R4 invariants. Returns list of error messages (empty if valid)."""
        errors: list[str] = []

        if not isinstance(payload, dict):
            return ["FHIR payload must be a JSON object."]

        resource_type = payload.get("resourceType")
        if not resource_type:
            return ["Missing mandatory field 'resourceType'."]

        if expected_type and resource_type.lower() != expected_type.lower():
            return [f"Payload resourceType '{resource_type}' does not match expected '{expected_type}'."]

        # Check support
        supported_types = {t.value.lower() for t in SupportedFHIRResourceType}
        # Also support Bundle
        if resource_type.lower() not in supported_types and resource_type != "Bundle":
            raise UnsupportedResourceTypeException(f"Resource type '{resource_type}' is not supported by HealthSetu interoperability.")

        # Type-specific validation
        if resource_type == "Patient":
            errors.extend(self._validate_patient(payload))
        elif resource_type == "Observation":
            errors.extend(self._validate_observation(payload))
        elif resource_type == "AllergyIntolerance":
            errors.extend(self._validate_allergy_intolerance(payload))
        elif resource_type == "MedicationRequest":
            errors.extend(self._validate_medication_request(payload))
        elif resource_type == "Encounter":
            errors.extend(self._validate_encounter(payload))
        elif resource_type == "DocumentReference":
            errors.extend(self._validate_document_reference(payload))
        elif resource_type == "Bundle":
            errors.extend(self._validate_bundle(payload))

        return errors

    def validate_or_raise(self, payload: dict[str, Any], expected_type: str | None = None) -> None:
        """Validate FHIR resource and raise InvalidFHIRResourceException if invalid."""
        errors = self.validate_resource(payload, expected_type)
        if errors:
            raise InvalidFHIRResourceException(
                message=f"FHIR validation failed: {'; '.join(errors)}",
                details={"errors": errors},
            )

    def validate_version(self, version: FHIRVersion | str) -> None:
        """Validate FHIR version against supported R4 version."""
        val = version.value if hasattr(version, "value") else str(version)
        if val != "R4":
            raise UnsupportedFHIRVersionException(
                f"FHIR version '{val}' is not supported. HealthSetu supports FHIR R4."
            )

    def _validate_patient(self, p: dict[str, Any]) -> list[str]:
        errs = []
        if "name" not in p and "identifier" not in p:
            errs.append("Patient resource must include at least 'name' or 'identifier'.")

        gender = p.get("gender")
        if gender and gender.lower() not in VALID_GENDERS:
            errs.append(f"Invalid Patient.gender '{gender}'. Must be one of {sorted(VALID_GENDERS)}.")

        birth_date = p.get("birthDate")
        if birth_date:
            try:
                date.fromisoformat(str(birth_date))
            except ValueError:
                errs.append(f"Invalid Patient.birthDate format '{birth_date}'. Expected ISO format YYYY-MM-DD.")
        return errs

    def _validate_observation(self, obs: dict[str, Any]) -> list[str]:
        errs = []
        status = obs.get("status")
        if not status:
            errs.append("Observation missing required field 'status'.")
        elif status.lower() not in VALID_OBSERVATION_STATUSES:
            errs.append(f"Invalid Observation.status '{status}'.")

        code = obs.get("code")
        if not code or not isinstance(code, dict):
            errs.append("Observation missing required 'code' object.")
        elif not code.get("coding") and not code.get("text"):
            errs.append("Observation.code must contain either 'coding' or 'text'.")

        if not obs.get("subject") and not obs.get("patient"):
            errs.append("Observation missing required 'subject' reference.")
        return errs

    def _validate_allergy_intolerance(self, a: dict[str, Any]) -> list[str]:
        errs = []
        if not a.get("patient") and not a.get("subject"):
            errs.append("AllergyIntolerance missing required 'patient' or 'subject' reference.")
        if not a.get("code") and not a.get("reaction"):
            errs.append("AllergyIntolerance must contain 'code' or 'reaction'.")
        return errs

    def _validate_medication_request(self, m: dict[str, Any]) -> list[str]:
        errs = []
        status = m.get("status")
        if not status:
            errs.append("MedicationRequest missing required field 'status'.")
        elif status.lower() not in VALID_MEDICATION_REQUEST_STATUSES:
            errs.append(f"Invalid MedicationRequest.status '{status}'.")

        if not m.get("intent"):
            errs.append("MedicationRequest missing required field 'intent'.")

        if not m.get("subject"):
            errs.append("MedicationRequest missing required 'subject' reference.")

        if not m.get("medicationCodeableConcept") and not m.get("medicationReference"):
            errs.append("MedicationRequest requires 'medicationCodeableConcept' or 'medicationReference'.")
        return errs

    def _validate_encounter(self, enc: dict[str, Any]) -> list[str]:
        errs = []
        if not enc.get("status"):
            errs.append("Encounter missing required field 'status'.")
        if not enc.get("class"):
            errs.append("Encounter missing required field 'class'.")
        if not enc.get("subject"):
            errs.append("Encounter missing required 'subject' reference.")
        return errs

    def _validate_document_reference(self, doc: dict[str, Any]) -> list[str]:
        errs = []
        if not doc.get("status"):
            errs.append("DocumentReference missing required field 'status'.")
        if not doc.get("content") or not isinstance(doc["content"], list):
            errs.append("DocumentReference missing required 'content' list.")
        return errs

    def _validate_bundle(self, b: dict[str, Any]) -> list[str]:
        errs = []
        if not b.get("type"):
            errs.append("Bundle missing required field 'type'.")
        entries = b.get("entry")
        if entries is not None and not isinstance(entries, list):
            errs.append("Bundle.entry must be a list.")
        return errs
