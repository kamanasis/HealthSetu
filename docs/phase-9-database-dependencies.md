# Phase 9 — Database Team Dependencies: Care Plan & Discharge System

**Document Version:** 1.0.0  
**Phase:** 9 — Care Plan & Discharge System  
**Status:** Backend Implemented (In-Memory Repositories Active, Pending Database Team PostgreSQL Schema)

---

## 1. Overview & System Boundary

Phase 9 establishes post-discharge continuity of care by connecting unstructured hospital discharge summaries to actionable daily patient care plans:

```
Discharge Document (Phase 5)
        ↓
Document Processing (Phase 5 OCR & Extraction)
        ↓
Discharge Information Extraction (Phase 9 Local/AI Extractor)
        ↓
Structured Discharge Instructions (Status: UNVERIFIED)
        ↓
Clinical Verification Boundary (Clinician Review & Correction)
        ↓
Personalized Care Plan (Actionable Daily Schedule & Red Flags)
        ↓
Medication / Activity / Follow-up / Wound Care Instructions
        ↓
Patient Care Plan (Goal Tracking, Task Check-off, Status Lifecycle)
```

### Strict Clinical & Architectural Invariants:
1. **Zero Autonomous Diagnosis:**
   - Discharge diagnoses are strictly extracted from hospital discharge notes as documented by the discharging physician.
   - The system attributes all diagnoses to the hospital record/attending clinician, never autonomous AI determination.
2. **Zero Autonomous Prescriptions:**
   - Medication instructions represent extracted discharge regimens. The system never autonomously creates or alters prescriptions.
3. **Clinical Verification Boundary:**
   - Extracted discharge instructions have initial verification status `UNVERIFIED`.
   - Active personalized recovery plans require clinician sign-off (`VERIFIED` or `CORRECTED`) before generation unless explicitly overridden.
4. **Patient Task Check-Off & Adherence:**
   - Patients can mark scheduled daily tasks as `COMPLETED` and record notes.
   - Updates increment the care plan `version` counter and record audit events.

---

## 2. Required PostgreSQL Entities & Schemas

### 2.1 Entity: `discharge_instructions`
Stores structured extraction results from processed hospital discharge summaries.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY` | Discharge instruction record identifier |
| `patient_id` | `UUID` | `NOT NULL, REFERENCES patients(id) ON DELETE CASCADE` | Associated patient |
| `document_id` | `UUID` | `NOT NULL, REFERENCES documents(id) ON DELETE RESTRICT` | Source Phase 5 clinical document |
| `encounter_id` | `UUID` | `NULLABLE, REFERENCES clinical_encounters(id) ON DELETE SET NULL` | Optional associated encounter |
| `verification_status` | `VARCHAR(50)` | `NOT NULL DEFAULT 'UNVERIFIED'` | Verification status enum (see 3.1) |
| `discharge_diagnoses` | `JSONB` | `NOT NULL DEFAULT '[]'` | Documented discharge diagnoses array |
| `medications` | `JSONB` | `NOT NULL DEFAULT '[]'` | Structured discharge medications array |
| `activity_instructions` | `JSONB` | `NOT NULL DEFAULT '[]'` | Activity restrictions and mobilization |
| `diet_instructions` | `JSONB` | `NOT NULL DEFAULT '[]'` | Dietary guidance and restrictions |
| `wound_care_instructions` | `JSONB` | `NOT NULL DEFAULT '[]'` | Wound care and dressing instructions |
| `warning_signs` | `JSONB` | `NOT NULL DEFAULT '[]'` | Red flag warning signs & emergency steps |
| `follow_up_instructions` | `JSONB` | `NOT NULL DEFAULT '[]'` | Follow-up clinics, timeframes, and tests |
| `confidence_score` | `NUMERIC(4,3)` | `NOT NULL DEFAULT 1.0` | Extraction confidence score (0.0 to 1.0) |
| `extractor_version` | `VARCHAR(50)` | `NOT NULL DEFAULT '1.0.0'` | Extractor version or model tag |
| `clinician_notes` | `TEXT` | `NULLABLE` | Clinician review notes or corrections |
| `verified_by` | `UUID` | `NULLABLE, REFERENCES users(id)` | Clinician who reviewed and verified record |
| `verified_at` | `TIMESTAMPTZ` | `NULLABLE` | Verification timestamp |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT NOW()` | Record creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT NOW()` | Record modification timestamp |

#### Indexes:
- `CREATE INDEX idx_discharge_instructions_patient ON discharge_instructions(patient_id, created_at DESC);`
- `CREATE INDEX idx_discharge_instructions_document ON discharge_instructions(document_id);`
- `CREATE INDEX idx_discharge_instructions_status ON discharge_instructions(patient_id, verification_status);`

---

### 2.2 Entity: `patient_care_plans`
Stores personalized post-discharge care plans and daily recovery schedules.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY` | Care plan unique identifier |
| `patient_id` | `UUID` | `NOT NULL, REFERENCES patients(id) ON DELETE CASCADE` | Associated patient |
| `discharge_id` | `UUID` | `NULLABLE, REFERENCES discharge_instructions(id) ON DELETE SET NULL` | Source discharge instruction record |
| `encounter_id` | `UUID` | `NULLABLE, REFERENCES clinical_encounters(id) ON DELETE SET NULL` | Optional associated encounter |
| `title` | `VARCHAR(255)` | `NOT NULL` | Care plan title (e.g., 'Post-PCI Care Plan') |
| `status` | `VARCHAR(50)` | `NOT NULL DEFAULT 'ACTIVE'` | Care plan lifecycle status (see 3.2) |
| `start_date` | `DATE` | `NOT NULL` | Care plan horizon start date |
| `end_date` | `DATE` | `NOT NULL` | Care plan horizon end date |
| `goals` | `JSONB` | `NOT NULL DEFAULT '[]'` | Clinical recovery goals array |
| `tasks` | `JSONB` | `NOT NULL DEFAULT '[]'` | Actionable daily task schedule array |
| `warning_signs` | `JSONB` | `NOT NULL DEFAULT '[]'` | Red flag warning sign guidance array |
| `notes` | `TEXT` | `NULLABLE` | General coordination and recovery notes |
| `version` | `INTEGER` | `NOT NULL DEFAULT 1` | Optimistic lock and version counter |
| `created_by` | `UUID` | `NULLABLE, REFERENCES users(id)` | Authorizing actor who initiated care plan |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT NOW()` | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT NOW()` | Last updated timestamp |

#### Indexes:
- `CREATE INDEX idx_care_plans_patient ON patient_care_plans(patient_id, status, start_date DESC);`
- `CREATE INDEX idx_care_plans_discharge ON patient_care_plans(discharge_id);`

---

## 3. Enumerations & Value Domains

### 3.1 `DischargeVerificationStatus`
- `EXTRACTED`: Preliminary automated extraction complete.
- `UNVERIFIED`: Extracted instructions awaiting clinician review.
- `PENDING_VERIFICATION`: Clinician review in progress.
- `VERIFIED`: Clinician approved instructions without modification.
- `CORRECTED`: Clinician approved instructions with clinical corrections.
- `REJECTED`: Clinician rejected extraction (unfit for care planning).

### 3.2 `CarePlanStatus`
- `DRAFT`: Initial draft plan.
- `ACTIVE`: Active patient recovery schedule.
- `COMPLETED`: Patient completed horizon goals and tasks.
- `DISCONTINUED`: Clinician discontinued plan (superseded or patient readmitted).

### 3.3 `CarePlanTaskCategory`
- `MEDICATION`: Daily scheduled medication administration.
- `ACTIVITY`: Physical activity, mobilization, or restriction.
- `DIET`: Nutritional and dietary guidance.
- `WOUND_CARE`: Surgical site or wound dressing care.
- `VITALS_MONITORING`: Self-reported blood pressure, glucose, temperature.
- `FOLLOW_UP_APPOINTMENT`: Scheduled outpatient follow-up consultation.

### 3.4 `CarePlanTaskStatus`
- `PENDING`: Task awaiting completion by patient or caregiver.
- `COMPLETED`: Patient marked task complete.

---

## 4. JSONB Schema Structures

### 4.1 Discharge Medication JSONB Structure (`discharge_instructions.medications`)
```json
[
  {
    "drug_name": "Atorvastatin",
    "dosage": "80 mg",
    "frequency": "Daily at bedtime",
    "duration": "Indefinite",
    "instructions": "Take with water at bedtime",
    "is_new": true,
    "is_changed": false,
    "discontinued": false
  }
]
```

### 4.2 Care Plan Tasks JSONB Structure (`patient_care_plans.tasks`)
```json
[
  {
    "id": "c1f7b8e2-...",
    "category": "MEDICATION",
    "title": "Take Atorvastatin",
    "instructions": "80 mg Daily at bedtime",
    "frequency": "DAILY",
    "day_offset": 0,
    "due_date": "2026-09-25",
    "status": "COMPLETED",
    "completed_at": "2026-09-25T21:30:00Z",
    "notes": "Taken as directed"
  },
  {
    "id": "e2a9c3d4-...",
    "category": "FOLLOW_UP_APPOINTMENT",
    "title": "Follow-up: Cardiology Clinic",
    "instructions": "Purpose: Post-PCI evaluation. Timing: In 14 days",
    "frequency": "ONCE",
    "day_offset": 14,
    "due_date": "2026-10-09",
    "status": "PENDING",
    "completed_at": null,
    "notes": null
  }
]
```

---

## 5. Security & Multi-Tenancy Rules

1. **Patient Data Isolation:** Every query on `discharge_instructions` and `patient_care_plans` MUST filter by `patient_id`.
2. **Clinical Consent Enforcement:** Provider access to `discharge_instructions` requires `discharge_summary` consent scope; access to `patient_care_plans` requires `care_plan` consent scope.
3. **Anti-Enumeration:** Requests for non-existent records or cross-patient attempts return `404 Not Found`.
4. **Audit Logging:** Every state change emits an audit event with IDs and operational metadata only; zero clinical narrative PHI is stored in audit logs.
