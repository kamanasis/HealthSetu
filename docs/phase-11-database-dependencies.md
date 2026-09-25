# Phase 11 — Hospital & Organization Network: Database Dependencies

## Document Information

| Field | Value |
|---|---|
| Phase | 11 |
| Module | Hospital & Organization Network |
| Backend Owner | Backend Team |
| Database Owner | Database Team |
| Status | Awaiting Database Team Delivery |

---

## 1. Overview

Phase 11 introduces the healthcare organization network layer, establishing the multi-tiered institutional hierarchy:

$$\text{Organization} \longrightarrow \text{Facility} \longrightarrow \text{Department} \longrightarrow \text{Clinician}$$

The backend application layer provides in-memory repository implementations conforming to the contracts below. The Database Team owns the actual PostgreSQL tables, foreign keys, indexes, and Alembic migrations.

---

## 2. Database Entities & Contracts

### 2.1 Healthcare Organizations Table (`organizations`)

Represents healthcare legal entities, hospital networks, diagnostic chains, or independent clinics.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID / VARCHAR(64) | PK | Unique organization identifier |
| `name` | VARCHAR(255) | NOT NULL, INDEX | Legal or operational name |
| `organization_type` | VARCHAR(50) | NOT NULL | Enum: `HOSPITAL`, `CLINIC`, `DIAGNOSTIC_CENTER`, `PHARMACY`, `LABORATORY`, `HEALTHCARE_NETWORK`, `OTHER` |
| `status` | VARCHAR(50) | NOT NULL | Enum: `ACTIVE`, `INACTIVE`, `SUSPENDED`, `PENDING`, `ARCHIVED` |
| `identifier` | VARCHAR(100) | NULLABLE, UNIQUE | External registry or national licensing identifier |
| `description` | TEXT | NULLABLE | Organizational profile or summary |
| `email` | VARCHAR(255) | NULLABLE | Official contact email |
| `phone` | VARCHAR(50) | NULLABLE | Official telephone number |
| `website` | VARCHAR(255) | NULLABLE | Web address |
| `address` | JSONB | NULLABLE | Structured address (`street`, `city`, `state`, `postal_code`, `country`) |
| `provenance` | JSONB | NOT NULL | Provenance tracking (`source`, `provider`, `provider_version`, `retrieved_at`) |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Modification timestamp |

**Indexes:**
- `idx_organizations_name` on `(lower(name))`
- `idx_organizations_status` on `(status)`
- `idx_organizations_type` on `(organization_type)`

---

### 2.2 Healthcare Facilities Table (`facilities`)

Represents physical or operational healthcare delivery sites belonging to an organization.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID / VARCHAR(64) | PK | Unique facility identifier |
| `organization_id` | UUID / VARCHAR(64) | FK `organizations.id`, NOT NULL, INDEX | Owning organization |
| `name` | VARCHAR(255) | NOT NULL, INDEX | Facility name |
| `facility_type` | VARCHAR(50) | NOT NULL | Enum: `HOSPITAL`, `CLINIC`, `URGENT_CARE`, `EMERGENCY_DEPARTMENT`, `DIAGNOSTIC_CENTER`, `LABORATORY`, `PHARMACY`, `SPECIALTY_CENTER`, `OTHER` |
| `status` | VARCHAR(50) | NOT NULL | Enum: `ACTIVE`, `INACTIVE`, `SUSPENDED`, `PENDING`, `ARCHIVED` |
| `identifier` | VARCHAR(100) | NULLABLE | Facility registration / licensing number |
| `description` | TEXT | NULLABLE | Facility operational scope |
| `email` | VARCHAR(255) | NULLABLE | Facility contact email |
| `phone` | VARCHAR(50) | NULLABLE | Facility phone number |
| `address` | JSONB | NULLABLE | Physical location address |
| `operational_metadata`| JSONB | NULLABLE | Hours, capacity, and operational metadata |
| `provenance` | JSONB | NOT NULL | Provenance tracking metadata |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Modification timestamp |

**Indexes:**
- `idx_facilities_organization_id` on `(organization_id)`
- `idx_facilities_name` on `(lower(name))`
- `idx_facilities_status` on `(status)`

---

### 2.3 Healthcare Departments Table (`departments`)

Represents medical or administrative departments within a specific facility.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID / VARCHAR(64) | PK | Unique department identifier |
| `facility_id` | UUID / VARCHAR(64) | FK `facilities.id`, NOT NULL, INDEX | Parent facility |
| `organization_id` | UUID / VARCHAR(64) | FK `organizations.id`, NOT NULL | Parent organization |
| `name` | VARCHAR(255) | NOT NULL | Department name (e.g. Cardiology, Radiology) |
| `code` | VARCHAR(50) | NULLABLE | Internal billing/department code |
| `status` | VARCHAR(50) | NOT NULL, DEFAULT 'ACTIVE' | Enum: `ACTIVE`, `INACTIVE` |
| `description` | TEXT | NULLABLE | Scope of services |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Modification timestamp |

**Indexes:**
- `idx_departments_facility_id` on `(facility_id)`
- `idx_departments_status` on `(status)`

---

### 2.4 Clinician Organization Memberships (`clinician_organizations`)

Associates clinicians (users with role `DOCTOR`) with organizations. Supports clinicians belonging to multiple organizations.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID / VARCHAR(64) | PK | Unique membership identifier |
| `clinician_id` | UUID / VARCHAR(64) | FK `users.id`, NOT NULL, INDEX | Clinician user identifier |
| `organization_id` | UUID / VARCHAR(64) | FK `organizations.id`, NOT NULL, INDEX | Organization identifier |
| `role_title` | VARCHAR(100) | NULLABLE | Clinician title (e.g. Chief of Staff, Consultant) |
| `status` | VARCHAR(50) | NOT NULL, DEFAULT 'ACTIVE' | Membership status: `ACTIVE`, `INACTIVE` |
| `joined_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Affiliation start date |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Record creation date |

**Unique Constraint:**
- `uq_clinician_organization` on `(clinician_id, organization_id)`

---

### 2.5 Clinician Facility Memberships (`clinician_facilities`)

Associates clinicians with specific facilities. Supports clinicians having privileges across multiple facilities.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID / VARCHAR(64) | PK | Unique membership identifier |
| `clinician_id` | UUID / VARCHAR(64) | FK `users.id`, NOT NULL, INDEX | Clinician user identifier |
| `facility_id` | UUID / VARCHAR(64) | FK `facilities.id`, NOT NULL, INDEX | Facility identifier |
| `organization_id` | UUID / VARCHAR(64) | FK `organizations.id`, NOT NULL | Organization identifier |
| `role_title` | VARCHAR(100) | NULLABLE | Clinical appointment title |
| `status` | VARCHAR(50) | NOT NULL, DEFAULT 'ACTIVE' | Privilege status: `ACTIVE`, `INACTIVE` |
| `joined_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Privilege grant date |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Record creation date |

**Unique Constraint:**
- `uq_clinician_facility` on `(clinician_id, facility_id)`

---

## 3. Data Integrity & Validation Rules

1. **Organization-Facility Relationship Validation**: A facility must reference a valid parent organization (`facility.organization_id = organization.id`).
2. **Facility-Department Relationship Validation**: A department must reference a valid facility (`department.facility_id = facility.id`).
3. **Status Invariant**: Inactive (`INACTIVE`), Suspended (`SUSPENDED`), or Archived (`ARCHIVED`) organizations or facilities reject operational access (`400 Bad Request`).
4. **Multi-Affiliation Support**: Clinicians may hold active memberships in $N$ organizations and $M$ facilities simultaneously.
