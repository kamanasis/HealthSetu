# Phase 12 — Facility Discovery & Transfer: API Documentation

## Document Information

| Field | Value |
|---|---|
| Phase | 12 |
| Module | Facility Discovery & Transfer |
| Base Path | `/api/v1` |
| Authentication | Bearer JWT (`Authorization: Bearer <token>`) |

---

## 1. Endpoints Overview

| Method | Path | Summary | Authorization |
|---|---|---|---|
| `GET` | `/facilities/discover` | Discover healthcare facilities by location & criteria | `facility:discover` |
| `GET` | `/patients/{patient_id}/facilities/discover` | Discover facilities in patient/triage context | `facility:discover` + Patient access |
| `POST` | `/patients/{patient_id}/transfers` | Create an explicit transfer or referral request | `transfer:create` + Patient access |
| `GET` | `/patients/{patient_id}/transfers` | List transfer history for a patient | `transfer:read` + Patient access |
| `GET` | `/patients/{patient_id}/transfers/{transfer_id}` | Retrieve specific transfer details | `transfer:read` + Patient access |
| `POST` | `/patients/{patient_id}/transfers/{transfer_id}/status` | Transition transfer status in state machine | `transfer:update_status` |

---

## 2. Endpoint Details

### 2.1 `GET /api/v1/facilities/discover`

Patient-facing facility discovery by geographic proximity, facility type, supported services, and capabilities.

- **Authentication:** Required
- **Authorization:** `facility:discover` (Roles: `PATIENT`, `DOCTOR`, `ADMIN`)
- **Query Parameters:**
  - `latitude` (optional, float): Coordinate between -90 and 90.
  - `longitude` (optional, float): Coordinate between -180 and 180.
  - `radius_km` (optional, float): Search radius in km (must be > 0 and <= max configured, e.g. 100).
  - `facility_type` (optional, string): Filter by facility type (e.g. `HOSPITAL`, `CLINIC`).
  - `required_service` (optional, string): Filter by supported service (e.g. `EMERGENCY_CARE`, `CARDIOLOGY`).
  - `required_capability` (optional, string): Filter by technical capability (e.g. `ICU`, `TRAUMA_CENTER`).
  - `organization_id` (optional, string): Filter by parent organization.
  - `limit` (optional, int, default: 50)
  - `offset` (optional, int, default: 0)
- **Response:** `200 OK`
  ```json
  {
    "success": true,
    "data": {
      "items": [
        {
          "facility_id": "fac-1",
          "organization_id": "org-1",
          "name": "Apollo Emergency Care",
          "facility_type": "HOSPITAL",
          "status": "ACTIVE",
          "address": { "city": "Kolkata", "state": "WB" },
          "latitude": 22.5726,
          "longitude": 88.3639,
          "distance_km": 4.82,
          "services": ["EMERGENCY_CARE", "ICU"],
          "capabilities": ["TRAUMA_CENTER"],
          "departments": ["Emergency Medicine", "Radiology"]
        }
      ],
      "total": 1,
      "limit": 50,
      "offset": 0,
      "origin_latitude": 22.5700,
      "origin_longitude": 88.3600,
      "radius_km": 25.0
    },
    "request_id": "req-123"
  }
  ```
- **Errors:**
  - `400 Bad Request`: `INVALID_LATITUDE`, `INVALID_LONGITUDE`, `INVALID_RADIUS`, `INCOMPLETE_LOCATION`, `FACILITY_DISCOVERY_DISABLED`
- **Audit Events:** `FACILITY_DISCOVERY_STARTED`, `FACILITY_DISCOVERY_COMPLETED`, `FACILITY_DISCOVERY_FAILED`

---

### 2.2 `GET /api/v1/patients/{patient_id}/facilities/discover`

Discover facilities in patient context. Automatically integrates latest triage urgency (e.g. routing to emergency services) without performing independent triage or reinterpretation.

- **Authentication:** Required
- **Authorization:** `facility:discover` + patient relationship / ownership
- **Path Parameters:**
  - `patient_id` (string, required)
- **Query Parameters:** Same as `GET /facilities/discover`.
- **Response:** `200 OK` with `FacilityDiscoveryResponse`
- **Errors:**
  - `403 Forbidden`: `PATIENT_ACCESS_DENIED`
  - `400 Bad Request`: Geolocation validation errors
- **Audit Events:** `FACILITY_DISCOVERY_STARTED`, `FACILITY_DISCOVERY_COMPLETED`

---

### 2.3 `POST /api/v1/patients/{patient_id}/transfers`

Create an explicit transfer or referral request to a destination facility.

- **Authentication:** Required
- **Authorization:** `transfer:create` + patient relationship
- **Consent Requirements:** Valid active patient consent for `care_delivery` or `transfer` scope.
- **Request Body:**
  ```json
  {
    "sending_facility_id": "fac-a1",
    "receiving_facility_id": "fac-b1",
    "reason": "Specialized tertiary cardiac intervention required",
    "encounter_id": "enc-1",
    "priority": "URGENT",
    "sbar_id": "sbar-1",
    "notes": "Coordinated with receiving chief resident"
  }
  ```
- **Response:** `201 Created`
  ```json
  {
    "success": true,
    "data": {
      "id": "trf-abc12345",
      "patient_id": "pat-1",
      "encounter_id": "enc-1",
      "sending_organization_id": "org-a",
      "sending_facility_id": "fac-a1",
      "receiving_organization_id": "org-b",
      "receiving_facility_id": "fac-b1",
      "status": "REQUESTED",
      "priority": "URGENT",
      "reason": "Specialized tertiary cardiac intervention required",
      "sbar_id": "sbar-1",
      "clinical_context_reference": "ctx-trf-abc12345",
      "created_by": "usr-doctor-1",
      "created_at": "2026-09-25T18:00:00Z",
      "updated_at": "2026-09-25T18:00:00Z"
    },
    "request_id": "req-123"
  }
  ```
- **Errors:**
  - `400 Bad Request`: `SENDING_FACILITY_INVALID`, `RECEIVING_FACILITY_INVALID`, `ENCOUNTER_ACCESS_DENIED`
  - `403 Forbidden`: `TRANSFER_CONSENT_REQUIRED`, `SBAR_ACCESS_DENIED`
- **Audit Events:** `TRANSFER_CREATED`, `TRANSFER_SBAR_ATTACHED`, `TRANSFER_CLINICAL_CONTEXT_SHARED`

---

### 2.4 `GET /api/v1/patients/{patient_id}/transfers`

Retrieve transfer and referral history for a patient.

- **Authentication:** Required
- **Authorization:** `transfer:read` + patient relationship
- **Response:** `200 OK` with `TransferListResponse`
- **Audit Event:** `TRANSFER_VIEWED`

---

### 2.5 `GET /api/v1/patients/{patient_id}/transfers/{transfer_id}`

Retrieve single transfer details.

- **Authentication:** Required
- **Authorization:** `transfer:read` + patient relationship
- **Response:** `200 OK` with `TransferResponse`
- **Errors:**
  - `404 Not Found`: `TRANSFER_NOT_FOUND`
- **Audit Event:** `TRANSFER_VIEWED`

---

### 2.6 `POST /api/v1/patients/{patient_id}/transfers/{transfer_id}/status`

Transition transfer through allowed states in the transfer lifecycle.

- **Authentication:** Required
- **Authorization:** `transfer:update_status` (Roles: `DOCTOR`)
- **Request Body:**
  ```json
  {
    "status": "ACCEPTED",
    "reason": "Bed available and cardiac surgery team on standby"
  }
  ```
- **Response:** `200 OK` with updated `TransferResponse`
- **Errors:**
  - `400 Bad Request`: `TRANSFER_INVALID_STATE` (if transition is prohibited by state machine)
  - `404 Not Found`: `TRANSFER_NOT_FOUND`
- **Audit Events:** `TRANSFER_ACCEPTED`, `TRANSFER_DECLINED`, `TRANSFER_CANCELLED`, `TRANSFER_COMPLETED`, `TRANSFER_FAILED`, `TRANSFER_STATUS_UPDATED`
