# Phase 12 — Facility Discovery & Transfer: Database Dependencies

## Document Information

| Field | Value |
|---|---|
| Phase | 12 |
| Module | Facility Discovery & Transfer |
| Backend Owner | Backend Team |
| Database Owner | Database Team |
| Status | Awaiting Database Team Delivery |

---

## 1. Overview

Phase 12 introduces patient-facing healthcare facility discovery, capability filtering, geographic proximity calculation, and explicit transfer/referral requests with minimal clinical context sharing.

The backend application layer provides in-memory repository implementations (`FacilityDiscoveryRepository` and `TransferRepository`) conforming to the contracts defined below. The Database Team owns the PostgreSQL tables, foreign keys, spatial/GIS indexes, and Alembic migrations.

---

## 2. Database Entities & Contracts

### 2.1 Facility Location & Capability Fields (`facilities` / `facility_capabilities` / `facility_services`)

To support geographic discovery and service/capability filtering, the `facilities` table (from Phase 11) is extended or linked with:

| Column / Relation | Type | Constraints | Description |
|---|---|---|---|
| `latitude` | NUMERIC(9, 6) / DOUBLE | NULLABLE, CHECK between -90 and 90 | Geographic latitude (WGS 84) |
| `longitude` | NUMERIC(9, 6) / DOUBLE | NULLABLE, CHECK between -180 and 180 | Geographic longitude (WGS 84) |
| `geom` | GEOMETRY(Point, 4326) | NULLABLE | Optional PostGIS geometry column for spatial indexing |
| `services` | TEXT[] / JSONB | NOT NULL, DEFAULT '{}' | Authoritative supported clinical services (e.g. `EMERGENCY_CARE`, `CARDIOLOGY`, `ICU`) |
| `capabilities` | TEXT[] / JSONB | NOT NULL, DEFAULT '{}' | Authoritative technical capabilities (e.g. `TRAUMA_CENTER`, `CARDIAC_CATH_LAB`) |

**Indexes:**
- `idx_facilities_geom` on `USING GIST (geom)` (if PostGIS enabled)
- `idx_facilities_lat_lon` on `(latitude, longitude)`
- `idx_facilities_services` on `USING GIN (services)`
- `idx_facilities_capabilities` on `USING GIN (capabilities)`

---

### 2.2 Patient Transfers Table (`transfers`)

Represents explicit patient transfer or clinical referral requests from a sending facility to a receiving facility.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(64) / UUID | PK | Unique transfer identifier |
| `patient_id` | VARCHAR(64) / UUID | FK `patients.id`, NOT NULL, INDEX | Owning patient |
| `encounter_id` | VARCHAR(64) / UUID | FK `encounters.id`, NULLABLE, INDEX | Associated clinical encounter |
| `sending_organization_id`| VARCHAR(64) / UUID | FK `organizations.id`, NOT NULL | Sending healthcare organization |
| `sending_facility_id` | VARCHAR(64) / UUID | FK `facilities.id`, NOT NULL, INDEX | Originating healthcare facility |
| `receiving_organization_id`| VARCHAR(64) / UUID | FK `organizations.id`, NOT NULL | Receiving healthcare organization |
| `receiving_facility_id` | VARCHAR(64) / UUID | FK `facilities.id`, NOT NULL, INDEX | Destination healthcare facility |
| `status` | VARCHAR(30) | NOT NULL, DEFAULT 'REQUESTED' | Enum: `REQUESTED`, `ACCEPTED`, `DECLINED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`, `FAILED` |
| `priority` | VARCHAR(20) | NOT NULL, DEFAULT 'ROUTINE' | Enum: `ROUTINE`, `URGENT`, `EMERGENCY` |
| `reason` | TEXT | NOT NULL | Objective / reason for referral or transfer |
| `sbar_id` | VARCHAR(64) / UUID | FK `sbar_reports.id`, NULLABLE | Optional attached SBAR report |
| `consent_id` | VARCHAR(64) / UUID | FK `consents.id`, NULLABLE | Consent record authorizing clinical data sharing |
| `clinical_context_reference`| VARCHAR(100) | NULLABLE | Unique token reference to attached clinical context snapshot |
| `notes` | TEXT | NULLABLE | Operational coordination notes |
| `status_history` | JSONB | NOT NULL, DEFAULT '[]' | Chronological array of status transitions with actor & reason |
| `created_by` | VARCHAR(64) / UUID | FK `users.id`, NOT NULL | Clinician or patient requesting transfer |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Modification timestamp |

**Constraints:**
- `chk_transfers_different_facilities` CHECK (`sending_facility_id <> receiving_facility_id`)

**Indexes:**
- `idx_transfers_patient_id` on `(patient_id)`
- `idx_transfers_sending_fac` on `(sending_facility_id)`
- `idx_transfers_receiving_fac` on `(receiving_facility_id)`
- `idx_transfers_status` on `(status)`

---

### 2.3 Transfer Clinical Context Table (`transfer_clinical_contexts`)

Stores the minimal authorized clinical snapshot attached to a transfer request.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `transfer_id` | VARCHAR(64) / UUID | PK, FK `transfers.id` | Associated transfer request |
| `patient_id` | VARCHAR(64) / UUID | FK `patients.id`, NOT NULL | Subject patient |
| `encounter_id` | VARCHAR(64) / UUID | FK `encounters.id`, NULLABLE | Optional encounter reference |
| `urgency_level` | VARCHAR(30) | NULLABLE | Triage urgency classification |
| `triage_notes` | TEXT | NULLABLE | Triage summary |
| `primary_symptoms` | JSONB / TEXT[] | NULLABLE | Snapshot of primary symptoms |
| `known_allergies` | JSONB / TEXT[] | NULLABLE | Snapshot of active allergies |
| `active_medications`| JSONB / TEXT[] | NULLABLE | Snapshot of active medications |
| `latest_vitals` | JSONB | NULLABLE | Snapshot of latest vitals |
| `sbar_id` | VARCHAR(64) / UUID | NULLABLE | SBAR reference ID |
| `sbar_situation` | TEXT | NULLABLE | SBAR situation section |
| `sbar_background` | TEXT | NULLABLE | SBAR background section |
| `sbar_assessment` | TEXT | NULLABLE | SBAR assessment section |
| `sbar_recommendation` | TEXT | NULLABLE | SBAR recommendation section |
| `consent_id` | VARCHAR(64) / UUID | NULLABLE | Authorizing consent record |
| `authorized_by` | VARCHAR(64) / UUID | FK `users.id`, NOT NULL | Authorizing user |
| `shared_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Snapshot creation timestamp |

---

## 3. State Machine & Constraints

### 3.1 Allowed Status Transitions

```
                 ┌─────────────┐
                 │  REQUESTED  │
                 └──────┬──────┘
            ┌───────────┼───────────┐
            ▼           ▼           ▼
      ┌──────────┐┌──────────┐┌───────────┐
      │ ACCEPTED ││ DECLINED ││ CANCELLED │
      └─────┬────┘└──────────┘└───────────┘
            │
            ▼
      ┌─────────────┐
      │ IN_PROGRESS │
      └─────┬───────┘
     ┌──────┴──────┐
     ▼             ▼
┌───────────┐┌──────────┐
│ COMPLETED ││  FAILED  │
└───────────┘└──────────┘
```

- Terminal states (`DECLINED`, `COMPLETED`, `CANCELLED`, `FAILED`) cannot transition to any other status.
