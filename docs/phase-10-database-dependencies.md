# Phase 10 — Doctor Clinical Workflow: Database Dependencies

## Document Information

| Field | Value |
|---|---|
| Phase | 10 |
| Module | Doctor Clinical Workflow |
| Backend Owner | Backend Team |
| Database Owner | Database Team |
| Status | Awaiting Database Team Delivery |

---

## Overview

Phase 10 introduces the clinician-facing workspace layer, including:

- Clinician-authored **clinical notes**
- Clinician-authored **clinical assessments**
- Clinician-authored **clinical plans**
- A **consolidated workspace** aggregating all clinical domain data for a patient/encounter

The backend is implemented with in-memory repository stubs. The Database Team must deliver the
PostgreSQL schema and replace the in-memory stubs.

---

## 1. Clinical Notes Table

**Backend contract name:** `clinical_notes`

### Columns

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Unique note identifier |
| `patient_id` | UUID | FK → patients.id, NOT NULL, INDEX | Owning patient |
| `encounter_id` | UUID | FK → encounters.id, NULLABLE, INDEX | Optional encounter reference |
| `clinician_id` | UUID | FK → users.id, NOT NULL, INDEX | Authoring clinician (server-side; never client-supplied) |
| `note_type` | VARCHAR(50) | NOT NULL | Enum: SOAP, PROGRESS, CONSULTATION, DISCHARGE, REFERRAL, PROCEDURE, OTHER |
| `title` | VARCHAR(200) | NOT NULL | Short descriptive title |
| `content` | TEXT | NOT NULL | Clinical note content |
| `is_signed` | BOOLEAN | NOT NULL, DEFAULT FALSE | Whether the note has been signed |
| `signed_at` | TIMESTAMPTZ | NULLABLE | Timestamp of signing |
| `is_addendum` | BOOLEAN | NOT NULL, DEFAULT FALSE | Whether this is an addendum to another note |
| `parent_note_id` | UUID | FK clinical_notes.id, NULLABLE | Reference to original note if addendum |
| `version` | INTEGER | NOT NULL, DEFAULT 1 | Optimistic concurrency version |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

### Indexes

- `idx_clinical_notes_patient_id` on `(patient_id)`
- `idx_clinical_notes_encounter_id` on `(encounter_id)`
- `idx_clinical_notes_clinician_id` on `(clinician_id)`
- `idx_clinical_notes_created_at` on `(created_at DESC)`

---

## 2. Clinical Assessments Table

**Backend contract name:** `clinical_assessments`

### Columns

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Unique assessment identifier |
| `patient_id` | UUID | FK patients.id, NOT NULL, INDEX | Owning patient |
| `encounter_id` | UUID | FK encounters.id, NULLABLE, INDEX | Optional encounter reference |
| `clinician_id` | UUID | FK users.id, NOT NULL, INDEX | Authoring clinician |
| `assessment_type` | VARCHAR(50) | NOT NULL | Enum: DIAGNOSIS, DIFFERENTIAL, FUNCTIONAL, RISK, PROGNOSIS, OTHER |
| `title` | VARCHAR(200) | NOT NULL | Short title for the assessment |
| `summary` | TEXT | NOT NULL | Clinician's overall assessment summary |
| `findings` | JSONB | NULLABLE | Structured clinical findings list |
| `icd_codes` | VARCHAR[] | NULLABLE | ICD-10/11 codes assigned |
| `severity` | VARCHAR(30) | NULLABLE | Severity label |
| `confidence` | VARCHAR(30) | NULLABLE | Clinician confidence: HIGH, MEDIUM, LOW |
| `is_finalized` | BOOLEAN | NOT NULL, DEFAULT FALSE | Whether finalized/locked |
| `finalized_at` | TIMESTAMPTZ | NULLABLE | Timestamp of finalization |
| `version` | INTEGER | NOT NULL, DEFAULT 1 | Optimistic concurrency version |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

---

## 3. Clinical Plans Table

**Backend contract name:** `clinical_plans`

### Columns

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Unique plan identifier |
| `patient_id` | UUID | FK patients.id, NOT NULL, INDEX | Owning patient |
| `encounter_id` | UUID | FK encounters.id, NULLABLE, INDEX | Optional encounter reference |
| `clinician_id` | UUID | FK users.id, NOT NULL, INDEX | Authoring clinician |
| `plan_type` | VARCHAR(50) | NOT NULL | Enum: TREATMENT, MANAGEMENT, DIAGNOSTIC, PREVENTIVE, PALLIATIVE, OTHER |
| `title` | VARCHAR(200) | NOT NULL | Plan title |
| `objectives` | TEXT[] | NOT NULL, DEFAULT '{}' | Ordered list of clinical objectives |
| `interventions` | JSONB | NULLABLE | Structured list of planned interventions |
| `investigations` | TEXT[] | NULLABLE | Ordered diagnostics/labs ordered |
| `follow_up_instructions` | TEXT | NULLABLE | Follow-up guidance |
| `status` | VARCHAR(30) | NOT NULL, DEFAULT 'ACTIVE' | Enum: DRAFT, ACTIVE, COMPLETED, CANCELLED |
| `is_finalized` | BOOLEAN | NOT NULL, DEFAULT FALSE | Whether finalized/locked |
| `finalized_at` | TIMESTAMPTZ | NULLABLE | |
| `version` | INTEGER | NOT NULL, DEFAULT 1 | Optimistic concurrency |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

---

## 4. Cross-Phase Read Dependencies

Phase 10 reads from all prior-phase tables to assemble the clinical workspace:

| Domain | Table(s) | Purpose |
|---|---|---|
| Phase 4 | patients, clinical_history, allergies, vitals, encounters | Patient demographics + clinical context |
| Phase 5 | documents, document_extractions | Medical documents |
| Phase 6 | prescriptions, patient_medications | Medications |
| Phase 7 | medication_safety_results | Safety checks |
| Phase 8 | symptom_intakes, triage_assessments, sbar_records | Triage and SBAR |
| Phase 9 | discharge_instructions, patient_care_plans | Care plans |

> The backend does NOT create, migrate, or alter any of these tables.
> All DDL is the exclusive responsibility of the Database Team.

---

## 5. Optimistic Concurrency

All three Phase 10 tables include a `version` column. The backend will:

1. Read the current `version` on fetch.
2. Accept `expected_version` on update requests.
3. Raise HTTP 409 Conflict if the persisted `version` does not match `expected_version`.

---

## 6. Security Notes

- `clinician_id` is always populated from the server-side JWT subject (`sub` claim).
- Client payloads must never include a `clinician_id` field.
- The `content` field of `clinical_notes` is sensitive PHI and must be encrypted at rest.

---

## 7. Backend Repository Stubs

| Repository | File |
|---|---|
| ClinicalNoteRepository | app/repositories/clinical_note_repository.py |
| ClinicalAssessmentRepository | app/repositories/clinical_assessment_repository.py |
| ClinicalPlanRepository | app/repositories/clinical_plan_repository.py |
