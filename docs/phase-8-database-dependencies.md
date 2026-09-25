# Phase 8 — Database Team Dependencies: Triage & SBAR System

**Document Version:** 1.0.0  
**Phase:** 8 — Triage & SBAR System  
**Status:** Backend Implemented (In-Memory Contracts Active, Pending Database Team PostgreSQL Schema)

---

## 1. Overview & System Boundary

Phase 8 introduces structured clinical symptom intake, deterministic triage rule evaluation, and SBAR (Situation, Background, Assessment, Recommendation) clinical communication summaries.

### Strict Boundaries & Invariants:
1. **Triage is NOT Diagnosis:**
   - Triage records determine clinical **urgency classification** based on authoritative clinical protocols.
   - Database tables must **never** record triage outputs as diagnostic codes or clinical conditions (`conditions` / `clinical_history`).
2. **Deterministic Primary Engine:**
   - Authoritative urgency classification derives from versioned rule sets, never unverified LLM generation.
3. **No Treatment / Prescriptions:**
   - Triage evaluations do not create medication orders or discharge care plans (Care Plans belong to Phase 9).
4. **Append-Only & Traceable:**
   - Historical assessments and SBAR summaries are immutable artifacts with complete provenance.

---

## 2. Required PostgreSQL Entities & Schemas

### 2.1 Entity: `patient_symptom_intakes`
Represents an atomic intake session where one or more symptoms were recorded.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY` | Intake session identifier |
| `patient_id` | `UUID` | `NOT NULL, REFERENCES patients(id) ON DELETE CASCADE` | Associated patient ID |
| `encounter_id` | `UUID` | `NULLABLE, REFERENCES clinical_encounters(id) ON DELETE SET NULL` | Optional associated encounter |
| `source` | `VARCHAR(50)` | `NOT NULL` | Intake provenance enum (see Section 3.1) |
| `notes` | `TEXT` | `NULLABLE` | Intake session operational notes |
| `recorded_by` | `UUID` | `NULLABLE, REFERENCES users(id)` | Authorizing actor who recorded intake |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT NOW()` | Session creation timestamp |

#### Indexes:
- `CREATE INDEX idx_symptom_intakes_patient ON patient_symptom_intakes(patient_id, created_at DESC);`
- `CREATE INDEX idx_symptom_intakes_encounter ON patient_symptom_intakes(encounter_id);`

---

### 2.2 Entity: `patient_symptoms`
Structured symptom records with preserved raw narrative alongside normalized clinical terms.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY` | Symptom record identifier |
| `patient_id` | `UUID` | `NOT NULL, REFERENCES patients(id) ON DELETE CASCADE` | Associated patient |
| `intake_id` | `UUID` | `NULLABLE, REFERENCES patient_symptom_intakes(id) ON DELETE CASCADE` | Parent intake session |
| `encounter_id` | `UUID` | `NULLABLE, REFERENCES clinical_encounters(id) ON DELETE SET NULL` | Optional encounter |
| `symptom_raw` | `VARCHAR(255)` | `NOT NULL` | Exact raw symptom narrative as reported |
| `symptom_normalized` | `VARCHAR(255)` | `NULLABLE` | Standardized clinical symptom term (NOT a diagnosis) |
| `severity` | `VARCHAR(50)` | `NULLABLE` | Severity enum: `MILD`, `MODERATE`, `SEVERE`, `CRITICAL` |
| `onset` | `VARCHAR(100)` | `NULLABLE` | Reported onset |
| `duration` | `VARCHAR(100)` | `NULLABLE` | Reported duration |
| `location` | `VARCHAR(150)` | `NULLABLE` | Anatomical location |
| `character` | `VARCHAR(150)` | `NULLABLE` | Symptom quality/character |
| `frequency` | `VARCHAR(100)` | `NULLABLE` | Frequency pattern |
| `progression` | `VARCHAR(100)` | `NULLABLE` | Progression pattern |
| `associated_symptoms`| `JSONB` | `NOT NULL DEFAULT '[]'` | Array of associated symptom strings |
| `aggravating_factors`| `JSONB` | `NOT NULL DEFAULT '[]'` | Array of aggravating factors |
| `relieving_factors` | `JSONB` | `NOT NULL DEFAULT '[]'` | Array of relieving factors |
| `patient_reported_context` | `TEXT` | `NULLABLE` | Direct contextual remarks |
| `source` | `VARCHAR(50)` | `NOT NULL` | Provenance enum |
| `recorded_by` | `UUID` | `NULLABLE, REFERENCES users(id)` | User who recorded entry |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT NOW()` | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT NOW()` | Last update timestamp |

#### Indexes:
- `CREATE INDEX idx_patient_symptoms_patient_date ON patient_symptoms(patient_id, created_at DESC);`
- `CREATE INDEX idx_patient_symptoms_intake ON patient_symptoms(intake_id);`
- `CREATE INDEX idx_patient_symptoms_normalized ON patient_symptoms(symptom_normalized);`

---

### 2.3 Entity: `clinical_triage_assessments`
Immutable clinical triage evaluation records.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY` | Triage assessment identifier |
| `patient_id` | `UUID` | `NOT NULL, REFERENCES patients(id) ON DELETE CASCADE` | Associated patient |
| `encounter_id` | `UUID` | `NULLABLE, REFERENCES clinical_encounters(id) ON DELETE SET NULL` | Optional encounter |
| `intake_id` | `UUID` | `NULLABLE, REFERENCES patient_symptom_intakes(id) ON DELETE SET NULL` | Source intake session |
| `urgency` | `VARCHAR(50)` | `NOT NULL` | Urgency classification enum (Section 3.2) |
| `status` | `VARCHAR(50)` | `NOT NULL` | Evaluation status enum (Section 3.3) |
| `rule_set` | `VARCHAR(100)` | `NOT NULL` | Name of clinical protocol evaluated |
| `rule_set_version` | `VARCHAR(50)` | `NOT NULL` | Version string of protocol |
| `explanation` | `JSONB` | `NOT NULL` | Structured explanation object |
| `immediate_instruction` | `TEXT` | `NULLABLE` | Immediate clinical action guidance |
| `previous_assessment_id` | `UUID` | `NULLABLE, REFERENCES clinical_triage_assessments(id)` | Previous assessment if reassessment |
| `sbar_id` | `UUID` | `NULLABLE` | Associated SBAR record ID |
| `idempotency_key` | `VARCHAR(100)` | `NULLABLE` | Client idempotency deduplication key |
| `assessed_by` | `UUID` | `NULLABLE, REFERENCES users(id)` | Assessing user/clinician ID |
| `assessed_at` | `TIMESTAMPTZ` | `NOT NULL` | Exact timestamp of assessment |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT NOW()` | Record persistence timestamp |

#### Indexes:
- `CREATE INDEX idx_triage_assessments_patient ON clinical_triage_assessments(patient_id, assessed_at DESC);`
- `CREATE INDEX idx_triage_assessments_urgency ON clinical_triage_assessments(urgency);`
- `CREATE UNIQUE INDEX idx_triage_idempotency ON clinical_triage_assessments(patient_id, idempotency_key) WHERE idempotency_key IS NOT NULL;`

---

### 2.4 Entity: `clinical_triage_reasons`
Traceable criteria and rule triggers for each triage evaluation.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY` | Reason entry ID |
| `assessment_id` | `UUID` | `NOT NULL, REFERENCES clinical_triage_assessments(id) ON DELETE CASCADE` | Parent triage assessment |
| `rule_id` | `VARCHAR(100)` | `NOT NULL` | Unique rule identifier |
| `reason_code` | `VARCHAR(100)` | `NOT NULL` | Clinical reason code |
| `description` | `TEXT` | `NOT NULL` | Criteria description |
| `source` | `VARCHAR(100)` | `NOT NULL` | Protocol source |
| `urgency_assigned` | `VARCHAR(50)` | `NOT NULL` | Urgency tier dictated by this rule |

---

### 2.5 Entity: `clinical_sbar_summaries`
Standardized SBAR clinical communication summaries.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY` | SBAR summary identifier |
| `patient_id` | `UUID` | `NOT NULL, REFERENCES patients(id) ON DELETE CASCADE` | Associated patient |
| `assessment_id` | `UUID` | `NOT NULL, REFERENCES clinical_triage_assessments(id) ON DELETE CASCADE` | Source triage assessment |
| `encounter_id` | `UUID` | `NULLABLE, REFERENCES clinical_encounters(id) ON DELETE SET NULL` | Optional encounter |
| `intake_id` | `UUID` | `NULLABLE, REFERENCES patient_symptom_intakes(id) ON DELETE SET NULL` | Optional intake session |
| `generation_mode` | `VARCHAR(50)` | `NOT NULL` | `template` or `ai` |
| `situation` | `JSONB` | `NOT NULL` | Structured Situation section |
| `background` | `JSONB` | `NOT NULL` | Structured Background section |
| `assessment` | `JSONB` | `NOT NULL` | Structured Assessment section |
| `recommendation` | `JSONB` | `NOT NULL` | Structured Recommendation section |
| `plain_text` | `TEXT` | `NOT NULL` | Full formatted clinical plain text |
| `validation_result` | `JSONB` | `NULLABLE` | Fact validation verification report |
| `generator_version` | `VARCHAR(50)` | `NOT NULL` | Generator algorithm version |
| `model_metadata` | `JSONB` | `NULLABLE` | AI model provider / token parameters (zero PHI) |
| `created_by` | `UUID` | `NULLABLE, REFERENCES users(id)` | Generating user |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT NOW()` | Generation timestamp |

#### Indexes:
- `CREATE INDEX idx_sbar_patient ON clinical_sbar_summaries(patient_id, created_at DESC);`
- `CREATE INDEX idx_sbar_assessment ON clinical_sbar_summaries(assessment_id);`

---

## 3. Required Enums & Reference Data

### 3.1 `symptom_source_enum`
- `PATIENT_REPORTED`
- `CAREGIVER_REPORTED`
- `DOCTOR_ENTERED`
- `CLINIC_ENTERED`
- `DOCUMENT_EXTRACTED`
- `IMPORTED`

### 3.2 `triage_urgency_enum`
- `EMERGENCY`: Immediate emergency medical care required (e.g. shock, severe hypoxia, acute coronary syndromes).
- `URGENT`: Timely clinician evaluation required within several hours.
- `SAME_DAY`: Clinician assessment recommended within 24 hours.
- `ROUTINE`: Non-urgent standard outpatient consultation.
- `SELF_CARE`: Self-care with clinical safety-net guidance.

### 3.3 `triage_status_enum`
- `COMPLETED`: Rule evaluation fully executed.
- `INSUFFICIENT_INFORMATION`: Missing required clinical observations (e.g., missing SpO2 for dyspneic patient) preventing safe risk exclusion.
- `REVIEW_REQUIRED`: Clinician manual review needed.
- `FAILED`: System or rule-engine operational failure.

---

## 4. Audit Log Integration (Phase 1/3 Alignment)

Phase 8 triggers the following standardized audit events in `audit_events`:
- `SYMPTOM_INTAKE_CREATED`
- `SYMPTOM_INTAKE_VIEWED`
- `TRIAGE_ASSESSMENT_STARTED`
- `TRIAGE_ASSESSMENT_COMPLETED`
- `TRIAGE_ASSESSMENT_FAILED`
- `TRIAGE_REASSESSMENT_CREATED`
- `SBAR_CREATED`
- `SBAR_VIEWED`
- `SBAR_REGENERATED`

**Privacy Invariant:** Under NO circumstances may symptom narratives, clinical notes, or medical history text be logged in `audit_events.metadata`. Only UUIDs, counts, urgency tiers, and protocol versions are permitted.
