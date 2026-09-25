# Phase 13 — Interoperability & Healthcare Data Exchange: Database Dependencies

## Document Information

| Field | Value |
|---|---|
| Phase | 13 |
| Module | Interoperability & Healthcare Data Exchange |
| Backend Owner | Backend Team |
| Database Owner | Database Team |
| Status | Awaiting Database Team Delivery |

---

## 1. Overview

Phase 13 introduces standardized healthcare data exchange for HealthSetu, supporting:
- HL7 FHIR R4 resource import and export.
- Extensible provider adapter abstraction.
- External patient and clinician identifier mappings.
- Provenance tracking and idempotent receipt of external clinical resources.
- Strict clinical verification boundaries (imported resources are never automatically verified or committed directly to active clinical records without clinician review).

The backend application layer provides in-memory repository implementations (`InteroperabilityRepository`) conforming to the contracts defined below. The Database Team owns PostgreSQL tables, foreign keys, constraints, and Alembic migrations.

---

## 2. Database Entities & Contracts

### 2.1 Interoperability Imports Table (`interoperability_imports`)

Stores records of inbound external healthcare resources received from external systems/providers.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(64) / UUID | PK | Unique import identifier (e.g. `imp-xxx`) |
| `source_system` | VARCHAR(120) | NOT NULL, INDEX | External system name or OID (e.g. `Hospital-A`, `urn:oid:2.16.840.1...`) |
| `source_organization_id` | VARCHAR(64) / UUID | FK `organizations.id`, NULLABLE | Associated internal or external organization |
| `resource_type` | VARCHAR(50) | NOT NULL, INDEX | Healthcare resource type (`Patient`, `Observation`, `AllergyIntolerance`, `MedicationRequest`, `Encounter`, `DocumentReference`) |
| `external_resource_id` | VARCHAR(128) | NOT NULL, INDEX | External system's resource identifier |
| `external_resource_version` | VARCHAR(32) | NULLABLE | Version tag/number in external system |
| `healthsetu_patient_id` | VARCHAR(64) / UUID | FK `patients.id`, NULLABLE, INDEX | Resolved internal patient ID (if resolved) |
| `status` | VARCHAR(30) | NOT NULL, INDEX | Status: `RECEIVED`, `VALIDATING`, `VALIDATED`, `MAPPING`, `MAPPED`, `REVIEW_REQUIRED`, `IMPORTED`, `REJECTED`, `FAILED` |
| `verification_status` | VARCHAR(30) | NOT NULL, DEFAULT 'EXTERNAL' | `EXTERNAL`, `IMPORTED`, `REVIEW_REQUIRED`, `VERIFIED` |
| `raw_payload_hash` | VARCHAR(64) | NOT NULL | SHA-256 hash of raw external payload (for idempotency check) |
| `mapped_data` | JSONB | NULLABLE | Transformed HealthSetu candidate representation |
| `mapped_entity_id` | VARCHAR(64) / UUID | NULLABLE | Target clinical entity ID once verified and merged |
| `error_details` | JSONB | NULLABLE | Error message and diagnostic codes if validation/mapping failed |
| `provenance` | JSONB | NOT NULL, DEFAULT '{}' | Complete provenance metadata (source, provider, mapper version, timestamps) |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Receipt timestamp |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Modification timestamp |

**Indexes & Constraints:**
- `uq_interop_import_source_res` UNIQUE (`source_system`, `external_resource_id`, `raw_payload_hash`) — Ensures idempotent processing of repeated external transmissions.
- `idx_interop_imports_patient` on `(healthsetu_patient_id)`
- `idx_interop_imports_status` on `(status)`
- `idx_interop_imports_source` on `(source_system, resource_type)`

---

### 2.2 Interoperability Exports Table (`interoperability_exports`)

Stores records of outbound authorized healthcare data exports sent to external systems.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(64) / UUID | PK | Unique export identifier (e.g. `exp-xxx`) |
| `patient_id` | VARCHAR(64) / UUID | FK `patients.id`, NOT NULL, INDEX | Target patient whose data was exported |
| `format` | VARCHAR(20) | NOT NULL | Interoperability format (`FHIR`, `HL7_V2`) |
| `scope` | VARCHAR(40) | NOT NULL | Export scope: `PATIENT_BASIC`, `ENCOUNTER`, `MEDICATIONS`, `ALLERGIES`, `VITALS`, `DOCUMENTS`, `CLINICAL_SUMMARY`, `FULL_AUTHORIZED_RECORD` |
| `target_system` | VARCHAR(120) | NOT NULL | Destination system, provider, or organization |
| `consent_id` | VARCHAR(64) / UUID | FK `consents.id`, NULLABLE | Phase 3 consent record authorizing interoperability exchange |
| `status` | VARCHAR(30) | NOT NULL, INDEX | Status: `REQUESTED`, `AUTHORIZED`, `PREPARING`, `VALIDATED`, `SENT`, `DELIVERED`, `FAILED`, `CANCELLED` |
| `resource_types` | TEXT[] / JSONB | NOT NULL, DEFAULT '[]' | List of FHIR resource types generated in the bundle |
| `delivered_bundle_id` | VARCHAR(128) | NULLABLE | Unique bundle identifier or external transmission reference ID |
| `error_details` | JSONB | NULLABLE | Error details if export or delivery failed |
| `provenance` | JSONB | NOT NULL, DEFAULT '{}' | Export provenance tracking |
| `created_by` | VARCHAR(64) / UUID | FK `users.id`, NOT NULL | User/actor requesting the export |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Request timestamp |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Modification timestamp |

**Indexes:**
- `idx_interop_exports_patient` on `(patient_id)`
- `idx_interop_exports_status` on `(status)`
- `idx_interop_exports_target` on `(target_system)`

---

### 2.3 External Patient Identifier Mappings Table (`interoperability_patient_identifier_mappings`)

Maintains deterministic identity mappings between external identifiers and internal HealthSetu patient records. Guessing or heuristic fuzzy matching is strictly forbidden.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(64) / UUID | PK | Unique mapping ID |
| `source_system` | VARCHAR(120) | NOT NULL | External system / authority (e.g. `Hospital-A`, `urn:oid:...`) |
| `external_patient_id`| VARCHAR(128) | NOT NULL | External system's patient MRN / identifier |
| `healthsetu_patient_id`| VARCHAR(64) / UUID | FK `patients.id`, NOT NULL, INDEX | Confirmed HealthSetu patient ID |
| `mapping_type` | VARCHAR(30) | NOT NULL, DEFAULT 'DIRECT' | `DIRECT`, `FEDERATED_ID`, `MANUAL_VERIFIED` |
| `verified_by` | VARCHAR(64) / UUID | FK `users.id`, NULLABLE | Clinician or administrator who verified identity match |
| `verified_at` | TIMESTAMPTZ | NULLABLE | Verification timestamp |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Creation timestamp |

**Constraints & Indexes:**
- `uq_interop_pat_mapping` UNIQUE (`source_system`, `external_patient_id`) — Each external identifier in a system maps to exactly one HealthSetu patient.
- `idx_interop_pat_mapping_internal` on `(healthsetu_patient_id)`

---

## 3. Relationships to Existing Clinical Entities

1. **`patients` (Phase 4):**
   - References `patients.id` via `healthsetu_patient_id` in imports, exports, and identity mappings.
2. **`consents` (Phase 3):**
   - References `consents.id` in `interoperability_exports` to enforce patient authorization under `ConsentScope.INTEROPERABILITY`.
3. **`allergies`, `patient_medications`, `vitals`, `encounters`, `documents` (Phases 4, 5, 6):**
   - Outbound export queries these records directly without schema changes.
   - Inbound import creates candidate payloads with `status = REVIEW_REQUIRED` and does not mutate active tables until Phase 10 clinician verification.
4. **`audit_events` (Phase 1/3):**
   - Records all interoperability lifecycles without storing PHI or raw FHIR payloads.
