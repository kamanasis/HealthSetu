# Phase 13 — Interoperability & Healthcare Data Exchange: API Documentation

## Document Information

| Field | Value |
|---|---|
| Phase | 13 |
| Module | Interoperability & Healthcare Data Exchange |
| Base Path | `/api/v1` |
| Authentication | Bearer JWT (`Authorization: Bearer <token>`) |

---

## 1. Endpoints Overview

| Method | Path | Summary | Authorization |
|---|---|---|---|
| `POST` | `/interoperability/import` | Accept an authorized external healthcare resource/message | `interoperability:import` |
| `GET` | `/interoperability/imports/{import_id}` | Return authorized import status and metadata | `interoperability:read` |
| `POST` | `/interoperability/export` | Create an authorized patient data export | `interoperability:export` + Patient Access + Consent |
| `GET` | `/interoperability/exports/{export_id}` | Return export status and metadata | `interoperability:read` |
| `POST` | `/patients/{patient_id}/interoperability/export` | Export specific patient data | `interoperability:export` + Patient Access + Consent |

---

## 2. Endpoint Details

### 2.1 `POST /api/v1/interoperability/import`

Accepts an authorized external healthcare resource or message for validation, deterministic identity resolution, transformation, and staging in candidate status.

- **Authentication:** Required
- **Authorization:** `interoperability:import` (Roles: `DOCTOR`, `ADMIN`)
- **Request Body:**
  ```json
  {
    "source_system": "Hospital-A",
    "source_organization_id": "org-ext-01",
    "format": "FHIR",
    "resource_type": "Observation",
    "payload": {
      "resourceType": "Observation",
      "id": "ext-obs-101",
      "status": "final",
      "code": {
        "coding": [
          { "system": "http://loinc.org", "code": "8867-4", "display": "Heart rate" }
        ],
        "text": "Heart Rate"
      },
      "subject": { "reference": "Patient/pat-001" },
      "effectiveDateTime": "2026-09-25T10:00:00Z",
      "valueQuantity": { "value": 78, "unit": "bpm" }
    },
    "external_resource_id": "ext-obs-101",
    "external_resource_version": "1",
    "healthsetu_patient_id": "pat-001"
  }
  ```
- **Response:** `201 Created`
  ```json
  {
    "success": true,
    "data": {
      "import_id": "imp-9b34fae2d78a",
      "status": "REVIEW_REQUIRED",
      "source_system": "Hospital-A",
      "resource_type": "Observation",
      "external_resource_id": "ext-obs-101",
      "healthsetu_patient_id": "pat-001",
      "verification_status": "REVIEW_REQUIRED",
      "message": "Resource Observation received and placed in status REVIEW_REQUIRED",
      "created_at": "2026-09-25T18:15:00Z"
    },
    "message": "External healthcare data accepted successfully",
    "request_id": "req-12345"
  }
  ```
- **Errors:**
  - `400 Bad Request` (`INTEROPERABILITY_DISABLED`, `UNSUPPORTED_INTEROPERABILITY_FORMAT`, `UNSUPPORTED_RESOURCE_TYPE`, `INVALID_FHIR_RESOURCE`, `RESOURCE_VALIDATION_FAILED`)
  - `422 Unprocessable Entity` (`EXTERNAL_IDENTITY_UNRESOLVED`, `AMBIGUOUS_PATIENT_MATCH`)

---

### 2.2 `GET /api/v1/interoperability/imports/{import_id}`

Retrieves the status, transformation outcome, and metadata of an import record. Raw clinical payloads are omitted to maintain PHI minimization.

- **Authentication:** Required
- **Authorization:** `interoperability:read` (Roles: `PATIENT` (own records), `DOCTOR`, `ADMIN`)
- **Response:** `200 OK`
  ```json
  {
    "success": true,
    "data": {
      "id": "imp-9b34fae2d78a",
      "source_system": "Hospital-A",
      "source_organization_id": "org-ext-01",
      "resource_type": "Observation",
      "external_resource_id": "ext-obs-101",
      "external_resource_version": "1",
      "healthsetu_patient_id": "pat-001",
      "status": "REVIEW_REQUIRED",
      "verification_status": "REVIEW_REQUIRED",
      "mapped_entity_id": null,
      "provenance": {
        "source_system": "Hospital-A",
        "resource_type": "Observation",
        "external_resource_id": "ext-obs-101",
        "provider": "MockProvider",
        "mapper_version": "1.0.0",
        "fhir_version": "R4",
        "verification_status": "REVIEW_REQUIRED"
      },
      "created_at": "2026-09-25T18:15:00Z",
      "updated_at": "2026-09-25T18:15:00Z"
    },
    "message": "Import record retrieved successfully",
    "request_id": "req-12345"
  }
  ```
- **Errors:**
  - `404 Not Found` (`IMPORT_NOT_FOUND`)
  - `403 Forbidden` (`FORBIDDEN` if a patient attempts to access another patient's import)

---

### 2.3 `POST /api/v1/interoperability/export`

Initiates an authorized export of patient clinical data conforming to FHIR R4 Bundles. Enforces data minimization scopes (`PATIENT_BASIC`, `ENCOUNTER`, `MEDICATIONS`, `ALLERGIES`, `VITALS`, `DOCUMENTS`, `CLINICAL_SUMMARY`, `FULL_AUTHORIZED_RECORD`) and verifies Phase 3 patient consent.

- **Authentication:** Required
- **Authorization:** `interoperability:export` (Roles: `PATIENT` (self), `DOCTOR` (relationship + consent), `ADMIN`)
- **Request Body:**
  ```json
  {
    "patient_id": "pat-001",
    "scope": "CLINICAL_SUMMARY",
    "format": "FHIR",
    "target_system": "Partner-Clinic",
    "consent_id": "cst-001"
  }
  ```
- **Response:** `202 Accepted`
  ```json
  {
    "success": true,
    "data": {
      "export_id": "exp-a1c2e3f4",
      "status": "DELIVERED",
      "patient_id": "pat-001",
      "format": "FHIR",
      "scope": "CLINICAL_SUMMARY",
      "target_system": "Partner-Clinic",
      "delivered_bundle_id": "bundle-pat-001-20260925",
      "message": "Export request completed with status DELIVERED",
      "created_at": "2026-09-25T18:20:00Z"
    },
    "message": "Export processed successfully",
    "request_id": "req-12345"
  }
  ```
- **Errors:**
  - `403 Forbidden` (`INTEROPERABILITY_CONSENT_REQUIRED`, `PATIENT_ACCESS_DENIED`, `EXPORT_NOT_AUTHORIZED`)
  - `404 Not Found` (`PATIENT_NOT_FOUND`)
  - `502 Bad Gateway` (`EXTERNAL_PROVIDER_UNAVAILABLE`, `EXTERNAL_PROVIDER_TIMEOUT`)

---

### 2.4 `GET /api/v1/interoperability/exports/{export_id}`

Retrieves the status, generated bundle identifier, and metadata for a previously dispatched export.

- **Authentication:** Required
- **Authorization:** `interoperability:read` (Roles: `PATIENT` (self), `DOCTOR`, `ADMIN`)
- **Response:** `200 OK`
  ```json
  {
    "success": true,
    "data": {
      "id": "exp-a1c2e3f4",
      "patient_id": "pat-001",
      "format": "FHIR",
      "scope": "CLINICAL_SUMMARY",
      "target_system": "Partner-Clinic",
      "consent_id": "cst-001",
      "status": "DELIVERED",
      "resource_types": ["Patient", "Observation", "AllergyIntolerance", "MedicationRequest"],
      "delivered_bundle_id": "bundle-pat-001-20260925",
      "provenance": {
        "target_system": "Partner-Clinic",
        "provider": "MockProvider",
        "fhir_version": "R4",
        "scope": "CLINICAL_SUMMARY",
        "exported_by": "usr-doctor-001"
      },
      "created_by": "usr-doctor-001",
      "created_at": "2026-09-25T18:20:00Z",
      "updated_at": "2026-09-25T18:20:01Z"
    },
    "message": "Export record retrieved successfully",
    "request_id": "req-12345"
  }
  ```
- **Errors:**
  - `404 Not Found` (`EXPORT_NOT_FOUND`)

---

### 2.5 `POST /api/v1/patients/{patient_id}/interoperability/export`

Convenience endpoint scoped to the patient resource path, supporting resource type filtering and format specification.

- **Authentication:** Required
- **Authorization:** `interoperability:export` (Roles: `PATIENT` (self), `DOCTOR` (relationship + consent), `ADMIN`)
- **Request Body:**
  ```json
  {
    "format": "FHIR",
    "scope": "FULL_AUTHORIZED_RECORD",
    "resource_types": ["Patient", "Observation", "Encounter"],
    "target_system": "Hospital-B",
    "consent_id": "cst-001"
  }
  ```
- **Response:** `202 Accepted` (Matching `InteroperabilityExportResponse`)

---

## 3. Audit Events Emitted

All operations generate structured audit log entries without logging PHI or raw FHIR payloads:
- `INTEROPERABILITY_IMPORT_STARTED`
- `INTEROPERABILITY_IMPORT_COMPLETED`
- `INTEROPERABILITY_IMPORT_FAILED`
- `INTEROPERABILITY_IMPORT_REJECTED`
- `INTEROPERABILITY_EXPORT_STARTED`
- `INTEROPERABILITY_EXPORT_COMPLETED`
- `INTEROPERABILITY_EXPORT_FAILED`
- `INTEROPERABILITY_RESOURCE_VIEWED`
- `EXTERNAL_IDENTITY_RESOLVED`
- `EXTERNAL_IDENTITY_UNRESOLVED`
- `INTEROPERABILITY_DATA_SHARED`
- `INTEROPERABILITY_VERIFICATION_REQUIRED`
