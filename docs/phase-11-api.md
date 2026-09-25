# Phase 11 — Hospital & Organization Network: API Documentation

## Document Information

| Field | Value |
|---|---|
| Phase | 11 |
| Module | Hospital & Organization Network |
| Base Path | `/api/v1` |
| Authentication | Bearer JWT (`Authorization: Bearer <token>`) |

---

## 1. Endpoints Overview

| Method | Path | Summary | Authorization |
|---|---|---|---|
| `GET` | `/organizations` | List accessible healthcare organizations | `organization:read` |
| `GET` | `/organizations/search` | Search internal organizations with filters | `organization:read` |
| `GET` | `/organizations/{organization_id}` | Retrieve single organization details | `organization:read` |
| `GET` | `/organizations/{organization_id}/facilities` | List facilities belonging to an organization | `facility:read` |
| `GET` | `/facilities/search` | Search internal facilities with filters | `facility:read` |
| `GET` | `/facilities/{facility_id}` | Retrieve single facility details | `facility:read` |
| `GET` | `/facilities/{facility_id}/departments` | List departments belonging to a facility | `department:read` |
| `GET` | `/departments/{department_id}` | Retrieve single department details | `department:read` |
| `GET` | `/clinicians/me/organizations` | List organizations affiliated with caller clinician | `clinician_network:read` |
| `GET` | `/clinicians/me/facilities` | List facilities accessible to caller clinician | `clinician_network:read` |
| `GET` | `/clinicians/me/organizations/{organization_id}/context` | Consolidated clinician organization context | `clinician_network:read` |
| `GET` | `/clinicians/me/facilities/{facility_id}/context` | Consolidated clinician facility context | `clinician_network:read` |

---

## 2. Endpoint Details

### 2.1 `GET /api/v1/organizations`

List healthcare organizations accessible to the caller.

- **Authentication:** Required (Bearer JWT)
- **Authorization:** `organization:read` (Roles: `DOCTOR`, `ADMIN`, `PATIENT`)
- **Query Parameters:**
  - `name` (optional, string): Case-insensitive substring match.
  - `status` (optional, string): `ACTIVE`, `INACTIVE`, `SUSPENDED`, `PENDING`, `ARCHIVED`.
  - `org_type` (optional, string): `HOSPITAL`, `CLINIC`, `DIAGNOSTIC_CENTER`, etc.
  - `limit` (optional, int, default: 50, max: 100)
  - `offset` (optional, int, default: 0)
- **Response:** `200 OK`
  ```json
  {
    "success": true,
    "data": {
      "items": [
        {
          "id": "org-1",
          "name": "Apollo Hospitals Group",
          "organization_type": "HOSPITAL",
          "status": "ACTIVE",
          "identifier": "IND-HOSP-001",
          "created_at": "2026-09-25T12:00:00Z",
          "updated_at": "2026-09-25T12:00:00Z"
        }
      ],
      "total": 1,
      "limit": 50,
      "offset": 0
    },
    "request_id": "req-123"
  }
  ```
- **Audit Event:** `ORGANIZATION_LIST_VIEWED`

---

### 2.2 `GET /api/v1/organizations/{organization_id}`

Retrieve details for a specific healthcare organization.

- **Authentication:** Required
- **Authorization:** `organization:read`
- **Path Parameters:**
  - `organization_id` (string, required)
- **Response:** `200 OK`
  ```json
  {
    "success": true,
    "data": {
      "id": "org-1",
      "name": "Apollo Hospitals Group",
      "organization_type": "HOSPITAL",
      "status": "ACTIVE",
      "identifier": "IND-HOSP-001",
      "email": "contact@apollo.test",
      "phone": "+91-44-28290200",
      "website": "https://apollo.test",
      "created_at": "2026-09-25T12:00:00Z",
      "updated_at": "2026-09-25T12:00:00Z"
    },
    "request_id": "req-123"
  }
  ```
- **Errors:**
  - `404 Not Found`: `ORGANIZATION_NOT_FOUND`
- **Audit Event:** `ORGANIZATION_VIEWED`

---

### 2.3 `GET /api/v1/organizations/{organization_id}/facilities`

List facilities belonging to an organization. Validates organization existence and active status.

- **Authentication:** Required
- **Authorization:** `facility:read`
- **Path Parameters:**
  - `organization_id` (string, required)
- **Query Parameters:**
  - `status` (optional, string): `ACTIVE`, `INACTIVE`, etc.
  - `facility_type` (optional, string)
  - `limit` (optional, int, default: 50)
  - `offset` (optional, int, default: 0)
- **Response:** `200 OK` with paginated `FacilityListResponse`
- **Errors:**
  - `404 Not Found`: `ORGANIZATION_NOT_FOUND`
  - `400 Bad Request`: `ORGANIZATION_INACTIVE`
- **Audit Event:** `FACILITY_LIST_VIEWED`

---

### 2.4 `GET /api/v1/facilities/{facility_id}`

Retrieve facility details and validate facility status.

- **Authentication:** Required
- **Authorization:** `facility:read`
- **Path Parameters:**
  - `facility_id` (string, required)
- **Response:** `200 OK` with `FacilityResponse`
- **Errors:**
  - `404 Not Found`: `FACILITY_NOT_FOUND`
  - `400 Bad Request`: `FACILITY_INACTIVE` (if status validation required)
- **Audit Event:** `FACILITY_VIEWED`

---

### 2.5 `GET /api/v1/facilities/{facility_id}/departments`

List departments belonging to a specific facility.

- **Authentication:** Required
- **Authorization:** `department:read`
- **Path Parameters:**
  - `facility_id` (string, required)
- **Query Parameters:**
  - `status` (optional, string): `ACTIVE`, `INACTIVE`
- **Response:** `200 OK` with `DepartmentListResponse`
- **Errors:**
  - `404 Not Found`: `FACILITY_NOT_FOUND`
- **Audit Event:** `DEPARTMENT_LIST_VIEWED`

---

### 2.6 `GET /api/v1/departments/{department_id}`

Retrieve individual department details.

- **Authentication:** Required
- **Authorization:** `department:read`
- **Path Parameters:**
  - `department_id` (string, required)
- **Response:** `200 OK` with `DepartmentResponse`
- **Errors:**
  - `404 Not Found`: `DEPARTMENT_NOT_FOUND`

---

### 2.7 `GET /api/v1/clinicians/me/organizations`

Retrieve all active organizations associated with the caller clinician. Sourced strictly from server-side JWT `current_user.user_id`.

- **Authentication:** Required
- **Authorization:** `clinician_network:read` (Roles: `DOCTOR`, `ADMIN`)
- **Response:** `200 OK` with `list[OrganizationResponse]`
- **Audit Event:** `CLINICIAN_ORGANIZATIONS_VIEWED`

---

### 2.8 `GET /api/v1/clinicians/me/facilities`

Retrieve all active facilities where the caller clinician has active privileges. Sourced strictly from server-side JWT.

- **Authentication:** Required
- **Authorization:** `clinician_network:read`
- **Response:** `200 OK` with `list[FacilityResponse]`
- **Audit Event:** `CLINICIAN_FACILITIES_VIEWED`

---

### 2.9 `GET /api/v1/clinicians/me/organizations/{organization_id}/context`

Return consolidated organization context for the authenticated clinician.

- **Authentication:** Required
- **Authorization:** `clinician_network:read`
- **Path Parameters:**
  - `organization_id` (string, required)
- **Response:** `200 OK`
  ```json
  {
    "success": true,
    "data": {
      "organization": { ... },
      "organization_status": "ACTIVE",
      "clinician_relationship": {
        "clinician_id": "doc-uuid",
        "organization_id": "org-1",
        "role_title": "Attending Physician",
        "status": "ACTIVE",
        "joined_at": "2026-01-01T00:00:00Z"
      },
      "accessible_facilities": [ ... ]
    },
    "request_id": "req-123"
  }
  ```
- **Errors:**
  - `404 Not Found`: `ORGANIZATION_NOT_FOUND`
  - `400 Bad Request`: `ORGANIZATION_INACTIVE`
  - `403 Forbidden`: `CLINICIAN_ORGANIZATION_ACCESS_DENIED`
- **Audit Event:** `ORGANIZATION_CONTEXT_VIEWED`

---

### 2.10 `GET /api/v1/clinicians/me/facilities/{facility_id}/context`

Return consolidated facility context for the authenticated clinician.

- **Authentication:** Required
- **Authorization:** `clinician_network:read`
- **Path Parameters:**
  - `facility_id` (string, required)
- **Response:** `200 OK`
  ```json
  {
    "success": true,
    "data": {
      "facility": { ... },
      "organization": { ... },
      "departments": [ ... ],
      "clinician_relationship": {
        "clinician_id": "doc-uuid",
        "facility_id": "fac-1",
        "organization_id": "org-1",
        "role_title": "Cardiologist",
        "status": "ACTIVE",
        "joined_at": "2026-01-01T00:00:00Z"
      },
      "facility_status": "ACTIVE"
    },
    "request_id": "req-123"
  }
  ```
- **Errors:**
  - `404 Not Found`: `FACILITY_NOT_FOUND`
  - `400 Bad Request`: `FACILITY_INACTIVE`
  - `400 Bad Request`: `ORGANIZATION_INACTIVE`
  - `403 Forbidden`: `CLINICIAN_FACILITY_ACCESS_DENIED`
- **Audit Event:** `FACILITY_CONTEXT_VIEWED`
