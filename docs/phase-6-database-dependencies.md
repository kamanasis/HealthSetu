# HealthSetu — Phase 6: Database Team Dependencies

**Document Purpose**: Specification of database contracts, PostgreSQL schemas, table relationships, foreign keys, indexes, and enums required for Phase 6 (Prescription & Medication System).

---

## 1. Required Entities & PostgreSQL Tables

### 1.1 `prescriptions` Table
Stores prescription header entities linked to patients, prescribers, and optionally Phase 5 medical documents.

```sql
CREATE TABLE prescriptions (
    id UUID PRIMARY KEY,
    patient_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_id UUID NULL REFERENCES medical_documents(id) ON DELETE SET NULL,
    extraction_id UUID NULL REFERENCES document_extractions(id) ON DELETE SET NULL,
    prescriber_reference VARCHAR(255) NULL,
    prescription_date TIMESTAMPTZ NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'PATIENT_UPLOAD',
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Expected Indexes
CREATE INDEX idx_prescriptions_patient_id ON prescriptions(patient_id);
CREATE INDEX idx_prescriptions_created_at ON prescriptions(created_at DESC);
CREATE INDEX idx_prescriptions_document_id ON prescriptions(document_id);
```

### 1.2 `prescription_items` Table
Stores individual medication items within a prescription. Preserves raw extraction values and links to canonical normalized medication concepts.

```sql
CREATE TABLE prescription_items (
    id UUID PRIMARY KEY,
    prescription_id UUID NOT NULL REFERENCES prescriptions(id) ON DELETE CASCADE,
    drug_name_raw VARCHAR(255) NOT NULL,
    strength_raw VARCHAR(100) NULL,
    dosage_form_raw VARCHAR(100) NULL,
    dose_raw VARCHAR(100) NULL,
    route_raw VARCHAR(100) NULL,
    frequency_raw VARCHAR(100) NULL,
    duration_raw VARCHAR(100) NULL,
    quantity_raw VARCHAR(100) NULL,
    instructions_raw VARCHAR(500) NULL,
    normalized_medication_id UUID NULL REFERENCES medications(id) ON DELETE SET NULL,
    normalization_status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    extraction_reference VARCHAR(255) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Expected Indexes
CREATE INDEX idx_prescription_items_prescription_id ON prescription_items(prescription_id);
CREATE INDEX idx_prescription_items_normalized_med_id ON prescription_items(normalized_medication_id);
CREATE INDEX idx_prescription_items_norm_status ON prescription_items(normalization_status);
```

### 1.3 `medications` Table
Stores canonical normalized medication concepts derived from terminology lookups (e.g. RxNorm). Shared across all prescriptions and patients to prevent duplicate rows.

```sql
CREATE TABLE medications (
    id UUID PRIMARY KEY,
    canonical_name VARCHAR(255) NOT NULL,
    generic_name VARCHAR(255) NULL,
    brand_name VARCHAR(255) NULL,
    terminology_system VARCHAR(50) NOT NULL,   -- e.g. 'RXNORM', 'LOCAL_MOCK'
    terminology_code VARCHAR(100) NOT NULL,     -- e.g. RxCUI '8640'
    strength VARCHAR(100) NULL,                 -- e.g. '500 mg'
    dosage_form VARCHAR(100) NULL,              -- e.g. 'capsule'
    route VARCHAR(100) NULL,                    -- e.g. 'oral'
    provider VARCHAR(50) NOT NULL,              -- e.g. 'rxnorm', 'local_mock'
    provider_version VARCHAR(50) NULL,
    confidence_score FLOAT NOT NULL DEFAULT 1.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Ensure idempotent concept deduplication
    CONSTRAINT uq_medications_concept UNIQUE(terminology_system, terminology_code, strength, dosage_form)
);

-- Expected Indexes
CREATE INDEX idx_medications_system_code ON medications(terminology_system, terminology_code);
CREATE INDEX idx_medications_canonical_name ON medications(canonical_name);
```

### 1.4 `patient_medications` Table
Stores the patient's longitudinal medication records with lifecycle state, complete provenance chain, human correction tracking, and data-level duplicate detection.

```sql
CREATE TABLE patient_medications (
    id UUID PRIMARY KEY,
    patient_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'PRESCRIBED',
    verification_status VARCHAR(50) NOT NULL DEFAULT 'EXTRACTED',
    drug_name_raw VARCHAR(255) NOT NULL,
    strength_raw VARCHAR(100) NULL,
    dosage_form_raw VARCHAR(100) NULL,
    route_raw VARCHAR(100) NULL,
    frequency_raw VARCHAR(100) NULL,
    duration_raw VARCHAR(100) NULL,
    instructions_raw VARCHAR(500) NULL,
    normalized_medication_id UUID NULL REFERENCES medications(id) ON DELETE SET NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'PRESCRIPTION',
    
    -- Provenance chain
    document_id UUID NULL REFERENCES medical_documents(id) ON DELETE SET NULL,
    extraction_id UUID NULL REFERENCES document_extractions(id) ON DELETE SET NULL,
    prescription_id UUID NULL REFERENCES prescriptions(id) ON DELETE SET NULL,
    prescription_item_id UUID NULL REFERENCES prescription_items(id) ON DELETE SET NULL,
    
    -- Data-level duplicate detection
    potential_duplicate BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Human review and correction tracking
    is_corrected BOOLEAN NOT NULL DEFAULT FALSE,
    original_raw_value VARCHAR(255) NULL,
    corrected_raw_value VARCHAR(255) NULL,
    corrected_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    corrected_at TIMESTAMPTZ NULL,
    
    -- Therapy timing
    start_date TIMESTAMPTZ NULL,
    end_date TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Expected Indexes
CREATE INDEX idx_patient_medications_patient_id ON patient_medications(patient_id);
CREATE INDEX idx_patient_medications_status ON patient_medications(status);
CREATE INDEX idx_patient_medications_source ON patient_medications(source);
CREATE INDEX idx_patient_medications_created_at ON patient_medications(created_at DESC);
CREATE INDEX idx_patient_medications_prescription ON patient_medications(prescription_id);
```

---

## 2. Enums & State Machines

### 2.1 `PrescriptionSource`
- `PATIENT_UPLOAD`
- `DOCTOR_UPLOAD`
- `CLINIC_UPLOAD`
- `IMPORTED`
- `SYSTEM`

### 2.2 `PrescriptionStatus`
- `DRAFT`
- `ACTIVE`
- `COMPLETED`
- `DISCONTINUED`
- `CANCELLED`

### 2.3 `NormalizationStatus`
- `PENDING`: Item queued for normalization.
- `MATCHED`: Uniquely mapped to canonical terminology concept.
- `AMBIGUOUS`: Multiple matching concepts identified; automatic resolution forbidden.
- `UNMATCHED`: Terminology provider returned no matches.
- `FAILED`: Terminology provider timed out or returned error.

### 2.4 `PatientMedicationStatus`
- `PRESCRIBED`: Documented as prescribed (does NOT imply patient is actively taking it).
- `REPORTED`: Reported by patient.
- `ACTIVE`: Actively taken / ongoing therapy.
- `INACTIVE`: Paused or completed therapy.
- `HISTORICAL`: Previous medication no longer active.
- `UNKNOWN`: Unverified status.

### 2.5 `VerificationStatus`
- `EXTRACTED`: Automated OCR / document intake.
- `REVIEW_REQUIRED`: Disambiguation or validation needed.
- `VERIFIED`: Confirmed by clinician.
- `CORRECTED`: Corrected during human review.
- `REJECTED`: Invalid or misread extraction.

---

## 3. Unresolved Database Dependencies

1. **`provider_patient_relationship` Table**:
   - Required for doctor-initiated clinical and prescription operations. Currently handled via in-memory relationship management in `AuthorizationService`.
   - Table columns needed: `id`, `provider_id` (FK -> users), `patient_id` (FK -> users), `relationship_type` (VARCHAR), `is_active` (BOOLEAN), `established_at`, `ended_at`.
2. **`consent_records` Table**:
   - Production PostgreSQL migration required for consent records with support for `scope='prescriptions'` and `scope='medications'`.
