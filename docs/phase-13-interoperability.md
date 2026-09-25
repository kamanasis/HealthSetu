# Phase 13 — Healthcare Interoperability & Data Exchange Specification

## 1. Executive Summary & Architectural Scope

Phase 13 delivers the standards-based healthcare data exchange layer for the HealthSetu platform.

### Architectural Boundaries:
- **Data Exchange Layer Only:** The interoperability module is strictly a translation, validation, and transport pipeline between external healthcare standard representations and HealthSetu's internal domain models.
- **No Duplicate Systems:** Reuses Phase 4 (Clinical records, vitals, allergies, encounters), Phase 5 (Documents), Phase 6 (Medication normalization), Phase 7 (Medication safety), Phase 10 (Clinical verification), and Phase 11 (Organizations/Facilities).
- **Safety Boundary:** External healthcare data is **never** automatically verified or committed directly to active clinical records without clinician verification.

---

## 2. Standards Support & Configuration

HealthSetu configures its healthcare interoperability capabilities through application configuration:

| Setting | Default Value | Description |
|---|---|---|
| `INTEROPERABILITY_ENABLED` | `True` | Master feature flag for interoperability endpoints |
| `INTEROPERABILITY_PROVIDER` | `"none"` | Active integration provider (`none`, `mock`, `fhir_rest`) |
| `FHIR_ENABLED` | `True` | Enables HL7 FHIR exchange |
| `FHIR_VERSION` | `"R4"` | Standards version (explicitly HL7 FHIR Release 4) |
| `HL7_ENABLED` | `False` | HL7 v2/v3 message parsing (disabled unless required) |
| `HL7_VERSION` | `""` | Configured HL7 v2.x version if enabled |
| `INTEROPERABILITY_TIMEOUT_SECONDS` | `30` | Network request timeout for external provider connections |
| `INTEROPERABILITY_MAX_RETRIES` | `2` | Maximum retry attempts for transient transport failures |

### Supported Standards:
1. **Primary Standard:** HL7 FHIR R4 (`http://hl7.org/fhir/R4`).
2. **Secondary/Boundary:** HL7 v2 pipe-delimited messaging parser interface (`app/integrations/interoperability/hl7/`), configured off by default until a concrete integration endpoint requires it.

---

## 3. Supported FHIR R4 Resource Types

HealthSetu supports only the resource types that safely map to verified domain models:

| Resource Type | Inbound Import | Outbound Export | Internal Domain Mapping |
|---|---|---|---|
| `Patient` | Supported | Supported | `PatientRecord` (Phase 4) |
| `Observation` | Supported (Vitals) | Supported (Vitals) | `VitalRecord` (Phase 4) |
| `AllergyIntolerance` | Supported | Supported | `AllergyRecord` (Phase 4) |
| `MedicationRequest` | Supported | Supported | `PatientMedicationRecord` / `MedicationRecord` (Phase 6) |
| `Encounter` | Supported | Supported | `EncounterRecord` (Phase 4) |
| `DocumentReference` | Supported | Supported | `DocumentRecord` (Phase 5) |
| `Bundle` | Supported (`collection`, `batch`, `transaction`) | Supported (`collection`) | Multi-resource container |

---

## 4. Provider Adapter Architecture

HealthSetu utilizes an adapter-based architecture defining an abstract provider interface:

```
                  ┌───────────────────────────────┐
                  │    InteroperabilityService    │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │   InteroperabilityProvider    │ (app/integrations/interoperability/base.py)
                  └───────────────┬───────────────┘
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
┌──────────────────────────────┐              ┌──────────────────────────────┐
│  MockInteroperabilityProvider │              │   FHIRClient / HTTP Adapter  │
│      (Synthetic / Test)      │              │      (OAuth2 / Mutual TLS)   │
└──────────────────────────────┘              └──────────────────────────────┘
```

The service does not contain vendor-specific transport, protocol, or authentication details.

---

## 5. Inbound Import Pipeline & Safety Boundary

```
External Healthcare System
        │ (Payload)
        ▼
1. Receive Data (POST /api/v1/interoperability/import)
        │
2. Verify Feature Flags (INTEROPERABILITY_ENABLED, FHIR_ENABLED)
        │
3. Idempotency Check (SHA-256 hash + source_system + external_resource_id)
        │
4. Validate Format & Structural Constraints (FHIRValidator)
        │
5. Deterministic Identity Resolution (Never fuzzy match!)
        │  ├── Check healthsetu_patient_id exists
        │  ├── Query external_patient_id in repository
        │  └── Inspect FHIR Patient identifier / subject reference
        │  └── If unresolved: raise EXTERNAL_IDENTITY_UNRESOLVED
        │  └── If multiple conflicting matches: raise AMBIGUOUS_PATIENT_MATCH
        ▼
6. Resource Mapping (FHIRMapper)
        │  Transforms to candidate dictionary
        ▼
7. Clinical Safety Boundary
        │  Status: REVIEW_REQUIRED
        │  VerificationStatus: REVIEW_REQUIRED
        │  mapped_entity_id: None (never directly mutates active clinical records)
        ▼
8. Persistence & Audit
        │  Persist in InteroperabilityRepository
        └── Emit INTEROPERABILITY_IMPORT_COMPLETED & INTEROPERABILITY_VERIFICATION_REQUIRED
```

---

## 6. Outbound Export Pipeline & Data Minimization

```
Export Request (POST /api/v1/interoperability/export)
        │
1. Authentication & Permission Verification (INTEROPERABILITY_EXPORT)
        │
2. Patient Access & Phase 3 Consent Verification
        │  Verify active consent with scope: interoperability, clinical_records, or all_records
        ▼
3. Scoped Domain Query (Least Privilege Minimization)
        │  PATIENT_BASIC        -> Patient resource only
        │  ENCOUNTER            -> Patient + Encounter resources
        │  MEDICATIONS          -> Patient + MedicationRequest resources
        │  ALLERGIES            -> Patient + AllergyIntolerance resources
        │  VITALS               -> Patient + Observation (vitals) resources
        │  DOCUMENTS            -> Patient + DocumentReference resources
        │  CLINICAL_SUMMARY     -> Patient + Vitals + Allergies + Medications
        │  FULL_AUTHORIZED_RECORD -> All authorized clinical domains
        ▼
4. Bi-directional Mapping (FHIRMapper)
        │  Converts domain entities to FHIR R4 resources
        │  Embeds source identifiers, codings (LOINC, RxNorm, SNOMED), and timestamps
        ▼
5. Bundle Assembly & Validation (FHIRValidator)
        │  Generates FHIR Bundle of type "collection"
        │  Validates complete bundle before transmission
        ▼
6. Provider Dispatch & Audit
        │  Dispatches to configured InteroperabilityProvider
        └── Emits INTEROPERABILITY_EXPORT_COMPLETED & INTEROPERABILITY_DATA_SHARED
```

---

## 7. Deterministic Identity Matching Rules

1. **No Heuristic / Probabilistic Matching:** HealthSetu forbids merging or associating patients based solely on name, telephone number, address, or date of birth.
2. **Authoritative Resolution Priority:**
   - **Direct Internal ID:** Request explicitly specifies a verified HealthSetu `patient_id`.
   - **Pre-existing Mappings:** Queried from `interoperability_patient_identifier_mappings` matching `(source_system, external_patient_id)`.
   - **FHIR System Identifiers:** FHIR `identifier` containing `system = "urn:healthsetu:patient:id"`.
   - **Clinical Subject Reference:** Inbound observation/allergy referencing an internal `Patient/{id}` or mapped external patient.
3. **Ambiguity Handling:** If an external identifier resolves to more than one distinct internal patient record, the system immediately rejects the import with `AMBIGUOUS_PATIENT_MATCH`.
4. **Unresolved Identity:** If no authoritative link can be verified, the import returns `EXTERNAL_IDENTITY_UNRESOLVED` and halts without creating clinical records.

---

## 8. Provenance & PHI-Safe Auditing

Every inbound and outbound record tracks:
- `source_system` / `target_system`
- `source_organization_id`
- `external_resource_id`
- `external_resource_version`
- `provider`
- `mapper_version` (`1.0.0`)
- `fhir_version` (`R4`)
- `verification_status` (`REVIEW_REQUIRED`)
- Timestamps (`created_at`, `updated_at`)

**PHI Safety Rule:** Audit logs and responses never expose raw FHIR clinical payloads, patient medical histories, access tokens, or unredacted confidential observations.
