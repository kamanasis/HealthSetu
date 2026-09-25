# Phase 7 — Medication Safety System: Database Team Dependencies

**Document Status:** Architecture Contract / Requirements for Database Team  
**Phase:** 7 — Medication Safety System  
**Author:** Backend Engineering Team  
**Scope:** Backend/Application Implementation Only (Database schema & migrations owned by Database Team)

---

## 1. Executive Summary

Phase 7 introduces the medication safety evaluation pipeline. The backend consumes normalized medication data (Phase 6) and patient clinical context (Phase 4: allergies, conditions, vitals), and queries an authoritative medication safety provider (e.g. FDB, DrugBank, or mock during development).

In accordance with strict healthcare architecture policies:
1. **The Backend Team DOES NOT create or migrate database tables directly.**
2. **Safety results are time-bound evidence, not permanent diagnoses or prescribers.**
3. **No autonomous clinical actions** (no auto-discontinuation, no auto-prescription edits, no auto-allergy creation).
4. **Historical evaluations must be immutable** to maintain audit trails and clinical provenance.

---

## 2. Required Database Entities & Schemas

### 2.1 Table: `medication_safety_evaluations`
Stores top-level metadata and execution status for each safety evaluation run.

| Field Name | PostgreSQL Type | Nullable | Description / Constraints |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(64)` | No | Primary Key (e.g. `eval-<uuid>`) |
| `patient_id` | `VARCHAR(64)` | No | Foreign Key → `patients.id` |
| `medication_context` | `medication_context_enum` | No | `CURRENT_MEDICATIONS`, `NEW_PRESCRIPTION`, `FULL_MEDICATION_REVIEW` |
| `status` | `safety_evaluation_status_enum` | No | `CLEAR`, `ALERT`, `WARNING`, `NOT_SUPPORTED`, `INSUFFICIENT_CONTEXT`, `UNKNOWN`, `ERROR` |
| `provider` | `VARCHAR(128)` | No | Provider identifier (e.g. `HealthSetu-Synthetic-MockProvider`, `FirstDatabank`, `DrugBank`) |
| `provider_version` | `VARCHAR(64)` | No | Provider API / software build version |
| `ruleset_version` | `VARCHAR(64)` | Yes | Clinical ruleset / monograph edition version |
| `medications_evaluated_count` | `INTEGER` | No | Number of medications evaluated |
| `patient_context_used` | `JSONB` | No | Counts of clinical context elements evaluated (e.g. `{"allergies_evaluated": 2, "conditions_evaluated": 1}`) |
| `disclaimer` | `TEXT` | No | Mandatory clinical decision-support disclaimer |
| `checked_at` | `TIMESTAMP WITH TIME ZONE` | No | UTC timestamp when provider evaluation occurred |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | Timestamp of database insertion |

### 2.2 Table: `medication_safety_alerts`
Stores individual alerts / interactions identified by the provider.

| Field Name | PostgreSQL Type | Nullable | Description / Constraints |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(64)` | No | Primary Key (e.g. `alert-<type>-<uuid>`) |
| `evaluation_id` | `VARCHAR(64)` | No | Foreign Key → `medication_safety_evaluations.id` (ON DELETE CASCADE) |
| `check_type` | `safety_check_type_enum` | No | `DRUG_DRUG`, `DRUG_ALLERGY`, `DRUG_DISEASE`, `CONTRAINDICATION`, `DUPLICATE_THERAPY`, `DOSING`, `PREGNANCY`, `RENAL`, `HEPATIC`, `OTHER` |
| `severity` | `safety_alert_severity_enum` | No | `CRITICAL`, `MAJOR`, `MODERATE`, `MINOR`, `INFO` |
| `title` | `VARCHAR(255)` | No | Concise summary of interaction or warning |
| `description` | `TEXT` | No | Authoritative clinical explanation provided by vendor |
| `medications_involved` | `JSONB` | No | Array of objects: `[{"name": "...", "medication_id": "...", "code": "..."}]` |
| `clinical_context_involved` | `JSONB` | No | Array of context objects (e.g. allergy ID, condition ID, age) |
| `evidence` | `TEXT` | Yes | Literature citation or clinical guideline reference from vendor |
| `source` | `VARCHAR(128)` | No | Name of authoritative knowledge base |
| `provider_rule_id` | `VARCHAR(64)` | Yes | Vendor rule ID / monograph code |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | Timestamp of database insertion |

### 2.3 Table: `medication_safety_check_summaries`
Records execution outcome per requested check type (e.g. whether unsupported or clear).

| Field Name | PostgreSQL Type | Nullable | Description / Constraints |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(64)` | No | Primary Key |
| `evaluation_id` | `VARCHAR(64)` | No | Foreign Key → `medication_safety_evaluations.id` |
| `check_type` | `safety_check_type_enum` | No | Check type |
| `supported` | `BOOLEAN` | No | Whether configured provider supports this check |
| `status` | `safety_evaluation_status_enum` | No | Execution status for this check type |
| `alert_count` | `INTEGER` | No | Number of alerts generated |
| `note` | `TEXT` | Yes | Informational execution note (e.g. if unsupported or failed) |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | Timestamp of record creation |

---

## 3. Required PostgreSQL Enums

```sql
CREATE TYPE medication_context_enum AS ENUM (
    'CURRENT_MEDICATIONS',
    'NEW_PRESCRIPTION',
    'FULL_MEDICATION_REVIEW'
);

CREATE TYPE safety_check_type_enum AS ENUM (
    'DRUG_DRUG',
    'DRUG_ALLERGY',
    'DRUG_DISEASE',
    'CONTRAINDICATION',
    'DUPLICATE_THERAPY',
    'DOSING',
    'PREGNANCY',
    'RENAL',
    'HEPATIC',
    'OTHER'
);

CREATE TYPE safety_alert_severity_enum AS ENUM (
    'CRITICAL',
    'MAJOR',
    'MODERATE',
    'MINOR',
    'INFO'
);

CREATE TYPE safety_evaluation_status_enum AS ENUM (
    'CLEAR',
    'ALERT',
    'WARNING',
    'NOT_SUPPORTED',
    'INSUFFICIENT_CONTEXT',
    'UNKNOWN',
    'ERROR'
);
```

---

## 4. Recommended Indexes

To ensure fast paginated querying by patient and date:

```sql
-- Fast historical lookups by patient ordered by time
CREATE INDEX idx_safety_evaluations_patient_checked
ON medication_safety_evaluations(patient_id, checked_at DESC);

-- Filter by evaluation status (e.g. alerting evaluations only)
CREATE INDEX idx_safety_evaluations_patient_status
ON medication_safety_evaluations(patient_id, status);

-- Fast lookup of alerts for a given evaluation
CREATE INDEX idx_safety_alerts_evaluation_id
ON medication_safety_alerts(evaluation_id);

-- Filter alerts by check type and severity
CREATE INDEX idx_safety_alerts_check_severity
ON medication_safety_alerts(evaluation_id, check_type, severity);

-- Fast lookup of check summaries
CREATE INDEX idx_safety_summaries_evaluation_id
ON medication_safety_check_summaries(evaluation_id);
```

---

## 5. Foreign Key & Integrity Constraints

1. `medication_safety_evaluations.patient_id` → `patients(id)` ON DELETE RESTRICT (must not orphan clinical safety records).
2. `medication_safety_alerts.evaluation_id` → `medication_safety_evaluations(id)` ON DELETE CASCADE.
3. `medication_safety_check_summaries.evaluation_id` → `medication_safety_evaluations(id)` ON DELETE CASCADE.
4. Evaluations must be **append-only**. Historical evaluations should never be overwritten in place; new evaluations create distinct records to guarantee provenance.
