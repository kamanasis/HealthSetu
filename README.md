# HealthSetu — Backend (Phases 1 – 7)

HealthSetu is a unified healthcare interoperability, clinical coordination, and patient safety backend platform.

- **Phase 1**: Production-oriented backend engineering foundation.
- **Phase 2**: Identity & Authentication layer (Argon2id, JWT, refresh rotation).
- **Phase 3**: Authorization, Access Control & Consent engine (RBAC, ownership, consent validation).
- **Phase 4**: Patient Clinical Record foundation (demographics, history, allergies, vitals, encounters, clinical summary).
- **Phase 5**: Medical Document Processing pipeline (secure object storage, OCR extraction, background processing, idempotency, PHI protection).
- **Phase 6**: Prescription & Medication System (extraction linkage, terminology normalization, longitudinal medication record).
- **Phase 7**: Medication Safety System (authoritative provider abstraction, DDI, allergy cross-reactivity, contraindications, duplicate therapy).

---

## 1. Architectural Principles & Boundaries

### Team Boundaries
| Team | Responsibility |
|---|---|
| **Backend** | FastAPI application, API routes, business logic, authentication/authorization, tests |
| **Database** | PostgreSQL schema, tables, migrations, indexes — **exclusively owned by Database Team** |
| **Frontend** | Not in scope for Phase 1 or 2 |

### Database Ownership Rule
The backend establishes an async connection layer and repository abstractions **only**. It does **not** create or modify database schema. When the database team delivers their models, repositories plug in cleanly.

### Clean Layered Architecture
```
HTTP Request
     ↓
API Endpoint (/api/v1/...)
     ↓ (Dependency Injection via FastAPI Depends)
Authentication Middleware / Dependency (get_current_user)
     ↓
Service Layer (app/services)
     ↓
Repository Layer (app/repositories)   ←→   External Adapters (app/integrations)
     ↓
Database (PostgreSQL Async Engine via SQLAlchemy 2.x)
```

---

## 2. Technology Stack

| Component | Technology |
|---|---|
| Runtime | Python 3.12+ |
| Framework | FastAPI |
| Validation & Settings | Pydantic v2, pydantic-settings |
| ASGI Server | Uvicorn |
| Database Access Layer | SQLAlchemy 2.x Async Engine + asyncpg |
| Password Hashing | Argon2id (via `argon2-cffi`) |
| JWT Tokens | PyJWT |
| Testing | pytest, pytest-asyncio, httpx |
| Containerization | Docker (non-root runtime), Docker Compose |

---

## 3. Directory Structure

```text
healthsetu-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                              # Application entrypoint & lifespan
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py                        # Root API router (v1, future v2)
│   │   ├── deps.py                          # ⭐ Reusable auth dependencies (get_current_user)
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py                    # v1 router aggregator
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── health.py                # Liveness & readiness probes
│   │           └── auth.py                  # ⭐ Authentication endpoints (Phase 2)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                        # Environment-based settings (incl. JWT config)
│   │   ├── database.py                      # SQLAlchemy 2.x async engine & session boundary
│   │   ├── exceptions.py                    # Centralized exception handling & error envelopes
│   │   ├── logging.py                       # Structured JSON logging with clinical data scrubbing
│   │   ├── middleware.py                    # Request ID, security headers, size limiting
│   │   └── security.py                      # ⭐ Argon2id, JWT create/decode, token utilities
│   ├── services/
│   │   ├── __init__.py
│   │   ├── base.py                          # Generic base service
│   │   ├── health.py                        # Health probe service
│   │   └── auth_service.py                  # ⭐ Authentication business logic (Phase 2)
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base.py                          # Generic base repository
│   │   ├── user_repository.py               # ⭐ User identity data access (Phase 2)
│   │   └── auth_session_repository.py       # ⭐ Refresh session lifecycle (Phase 2)
│   ├── integrations/                        # External provider adapters (future phases)
│   │   ├── __init__.py, base.py
│   │   └── {medication_safety, ai, ocr, translation, fhir, abdm}/
│   ├── models/                              # Reserved for Database Team schema models
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── response.py                      # Standard HTTP response envelopes
│   │   ├── auth.py                          # ⭐ Auth request/response models (Phase 2)
│   │   └── user.py                          # ⭐ User identity models & AuthenticatedUserContext
│   └── utils/__init__.py
├── tests/
│   ├── conftest.py                          # Fixtures, seeded test users, clean state
│   ├── test_auth.py                         # ⭐ 25 authentication test cases (Phase 2)
│   ├── test_security_auth.py                # ⭐ Security-specific tests (Phase 2)
│   ├── test_config.py
│   ├── test_cors.py
│   ├── test_database.py
│   ├── test_error_handling.py
│   ├── test_health.py
│   ├── test_readiness.py
│   ├── test_request_id.py
│   └── test_startup.py
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## 4. Configuration & Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

### Phase 1 Variables

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `HealthSetu` | Application service name |
| `APP_ENV` | `development` | Environment (`development`, `testing`, `production`) |
| `APP_VERSION` | `0.1.0` | Semantic version |
| `DEBUG` | `false` | Debug mode |
| `HOST` | `0.0.0.0` | Host binding |
| `PORT` | `8000` | Port binding |
| `DATABASE_URL` | *None* | Async PostgreSQL URL (`postgresql+asyncpg://...`) |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |
| `LOG_LEVEL` | `INFO` | Log severity |
| `API_PREFIX` | `/api/v1` | Base API route prefix |
| `REQUEST_ID_HEADER` | `X-Request-ID` | Correlation ID header name |
| `MAX_REQUEST_SIZE_BYTES` | `10485760` | Max payload size (10MB) |

### Phase 2 Variables (Authentication)

| Variable | Default | Description |
|---|---|---|
| `JWT_SECRET_KEY` | *must set in prod* | Cryptographic key for signing JWTs |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token lifetime (minutes) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Refresh token lifetime (days) |
| `PASSWORD_HASHING_SCHEME` | `argon2id` | Password hashing algorithm |
| `AUTH_RATE_LIMIT_ENABLED` | `false` | Enable login rate limiting hook |

> **Security**: Generate a strong production JWT secret key:
> ```bash
> openssl rand -hex 32
> ```

---

## 5. Phase 2 — Authentication Architecture

### Token Lifecycle

```
User (POST /auth/login)
     ↓  identifier + password
AuthService.authenticate()
     ↓  verify Argon2id hash
     ↓  check account status (ACTIVE only)
Issue: access_token (JWT, 15 min) + refresh_token (opaque, 30 days)
Persist: hash(refresh_token) → database as RefreshSession
     ↓
Protected API calls → Bearer access_token → get_current_user()
     ↓
(POST /auth/refresh) → validate + rotate refresh_token
     ↓  old token revoked, new token issued
     ↓  token reuse detected → ALL user sessions terminated
(POST /auth/logout) → revoke refresh session (idempotent)
```

### Security Design Decisions

| Decision | Implementation |
|---|---|
| Password hashing | **Argon2id** (time_cost=2, mem=64MB, parallelism=1) |
| Access token | **Short-lived JWT** (15 min), signed HS256 |
| Refresh token | **Opaque random token** (32-byte URL-safe) |
| Refresh storage | **SHA-256 hash only** — raw token never persisted |
| Token rotation | ✅ Old token revoked on each refresh |
| Reuse detection | ✅ Compromised token reuse triggers full session wipe |
| Account status | ✅ ACTIVE only may authenticate |
| Error messages | ✅ Generic — never reveals whether account exists |
| Timing attacks | ✅ Dummy Argon2id hash run even for unknown users |
| PHI in tokens | ✅ JWT claims contain **zero clinical data** |
| Credential logging | ✅ Passwords, tokens, and Authorization headers never logged |

### Authenticated User Context
```python
AuthenticatedUserContext:
    user_id: str
    role: UserRole         # PATIENT | DOCTOR | ADMIN
    account_status: AccountStatus
```
This is the **only** identity object passed to protected endpoints — no clinical data loaded until explicitly required by later phases.

### Using the Authentication Dependency

```python
from app.api.deps import get_current_user
from app.schemas.user import AuthenticatedUserContext

@router.get("/some-protected-endpoint")
async def protected(
    current_user: AuthenticatedUserContext = Depends(get_current_user),
):
    # current_user.user_id, .role, .account_status
    ...
```

---

## 6. API Endpoints

### Phase 1 — Health

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/health` | None | Application liveness probe |
| `GET` | `/api/v1/ready` | None | Database readiness probe |

### Phase 2 — Authentication

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/login` | None | Authenticate and receive tokens |
| `POST` | `/api/v1/auth/refresh` | None | Rotate refresh token for new tokens |
| `POST` | `/api/v1/auth/logout` | None | Revoke session (idempotent) |
| `GET` | `/api/v1/auth/me` | Bearer | Get authenticated caller identity |

### Standard Response Envelopes

**Success:**
```json
{
  "success": true,
  "data": { ... },
  "request_id": "abc-123"
}
```

**Error:**
```json
{
  "success": false,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid credentials.",
    "request_id": "abc-123"
  }
}
```

---

## 7. Local Setup & Development

```bash
# 1. Create & activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1       # Windows PowerShell
# source .venv/bin/activate       # Linux / macOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — set JWT_SECRET_KEY and DATABASE_URL

# 4. Start dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

*(API documentation is disabled in `production` mode)*

---

## 8. Running Tests

```bash
# Run all tests
pytest -v

# Run only auth-related tests
pytest tests/test_auth.py tests/test_security_auth.py -v
```

**Current Test Suite: 59 tests / 59 passed**

| Test File | Tests | Coverage Area |
|---|---|---|
| `test_auth.py` | 25 | Login, refresh, logout, /me, token format, PHI checks |
| `test_security_auth.py` | 4 | Token reuse attack, credential log scrubbing, secret exposure |
| `test_config.py` | 3 | Settings loading, CORS parser |
| `test_cors.py` | 3 | CORS origin filtering, security headers |
| `test_database.py` | 3 | DB boundary, engine lifecycle |
| `test_error_handling.py` | 9 | Standardized error envelopes, 404/401/500/413 |
| `test_health.py` | 3 | Liveness probe |
| `test_readiness.py` | 3 | Readiness probe (DB mocking) |
| `test_request_id.py` | 3 | Correlation ID generation & propagation |
| `test_startup.py` | 3 | OpenAPI schema, Swagger, ReDoc |

---

## 9. Docker

```bash
# Build image
docker build -t healthsetu-backend:latest .

# Run with env file
docker run -p 8000:8000 --env-file .env healthsetu-backend:latest

# Full local dev stack (backend + dev PostgreSQL)
docker-compose up --build
```

> ⚠️ The dev PostgreSQL container in `docker-compose.yml` is for local connectivity testing only. The **Database Team owns the schema** — no domain tables are initialized automatically.

---

## 10. Database Team Dependencies

**Phase 2 requires the following entities from the Database Team:**

### User Identity Entity
```
id              : Primary Key (UUID / string)
identifier      : UNIQUE string (email / phone / username) — case-insensitive lookup
password_hash   : VARCHAR — Argon2id hash (never plaintext)
role            : ENUM ('PATIENT', 'DOCTOR', 'ADMIN')
status          : ENUM ('ACTIVE', 'DISABLED', 'LOCKED', 'PENDING')
created_at      : TIMESTAMP WITH TIME ZONE
updated_at      : TIMESTAMP WITH TIME ZONE
```

### Refresh Session Entity
```
id                      : Primary Key (UUID)
user_id                 : FOREIGN KEY → users.id
token_hash              : VARCHAR — SHA-256(raw_token) — NEVER raw token
expires_at              : TIMESTAMP WITH TIME ZONE
is_revoked              : BOOLEAN DEFAULT FALSE
replaced_by_session_id  : NULLABLE FOREIGN KEY → refresh_sessions.id
created_at              : TIMESTAMP WITH TIME ZONE
```

> The backend repository interfaces (`UserRepository`, `AuthSessionRepository`) have documented `# NOTE FOR DATABASE TEAM:` comment blocks showing exact integration points. When schema is delivered, swap in the SQLAlchemy model queries without touching the service layer.

---

## 11. Security Considerations

- Passwords are **never** stored, logged, or returned in plaintext
- Refresh tokens are **only stored as SHA-256 hashes** — the raw token is ephemeral
- JWTs contain **zero clinical information** (no diagnoses, prescriptions, history, PHI)
- All authentication failures return an **identical generic message** to prevent account enumeration
- Token reuse detection terminates **all sessions for the affected user**
- `SENSITIVE_FIELD_NAMES` in the logging module automatically redacts credentials and clinical keywords from all structured logs
- Production: `DEBUG=false`, wildcard CORS blocked, stack traces never exposed

---

## 12. Phase 3 — Authorization, Access Control & Consent

Phase 3 introduces the centralized authorization evaluation engine and patient consent management:

- **Permission Policy Registry**: Strict role-to-permission mapping (`ROLE_PERMISSIONS`) adhering to least privilege. Admin accounts have zero clinical access by default.
- **Access Evaluation Pipeline**: Stepwise evaluation (`Authentication` → `Permission Check` → `Ownership Check` → `Relationship Check` → `Consent Check`).
- **Consent Lifecycle**: Patients grant and revoke access for explicit purposes (`care_delivery`, `research`, `emergency_access`) and scopes (`clinical_records`, `prescriptions`, etc.).
- **Consent Endpoints**:
  - `POST /api/v1/consents` — Grant consent
  - `GET /api/v1/consents` — List active consents
  - `GET /api/v1/consents/{id}` — Retrieve specific consent grant
  - `POST /api/v1/consents/{id}/revoke` — Revoke consent grant

---

## 13. Phase 4 — Patient Clinical Record Foundation

Phase 4 implements the core clinical record entities and operations with strict PHI protections and zero inference:

### Endpoints
- **Patient Profile**:
  - `GET /api/v1/patients/{patient_id}` — View patient profile (self or authorized doctor)
  - `PATCH /api/v1/patients/{patient_id}` — Update permitted demographics (self only)
  - `GET /api/v1/patients/{patient_id}/clinical-summary` — Controlled aggregated summary
- **Clinical History**:
  - `GET /api/v1/patients/{patient_id}/history` — List history entries
  - `POST /api/v1/patients/{patient_id}/history` — Record past condition / event
  - `GET /api/v1/patients/{patient_id}/history/{id}` — View history entry
  - `PATCH /api/v1/patients/{patient_id}/history/{id}` — Update history entry (clinician only)
- **Allergies**:
  - `GET /api/v1/patients/{patient_id}/allergies` — List patient allergies
  - `POST /api/v1/patients/{patient_id}/allergies` — Record allergy
  - `GET /api/v1/patients/{patient_id}/allergies/{id}` — View allergy
  - `PATCH /api/v1/patients/{patient_id}/allergies/{id}` — Update allergy (clinician only)
- **Vitals (Append-Only)**:
  - `GET /api/v1/patients/{patient_id}/vitals` — List vitals with filtering
  - `POST /api/v1/patients/{patient_id}/vitals` — Append vital measurement
  - `GET /api/v1/patients/{patient_id}/vitals/{id}` — View vital measurement
  - *No update or deletion endpoints exist for vitals.*
- **Encounters**:
  - `GET /api/v1/patients/{patient_id}/encounters` — List encounters
  - `POST /api/v1/patients/{patient_id}/encounters` — Record encounter (clinician only)
  - `GET /api/v1/patients/{patient_id}/encounters/{id}` — View encounter

### Security & Privacy Guarantees
- **No PHI in logs, JWTs, or audit events**: Audit events record opaque IDs and field names only, never demographic values.
- **Anti-Enumeration 404s**: Unauthorized attempts to access another patient's records return generic 404s instead of 403s.
- **Soft-Delete Only**: Clinical records are archived with `is_archived=True`, never hard deleted. Archived records cannot be updated.
- **Append-Only Vitals**: Measurements cannot be updated or removed once recorded.
- **No Clinical Inference**: Backend does not diagnose, score severity, infer allergies, or triage.

---

## 14. Phase 5 — Medical Document Processing

Phase 5 establishes the secure medical document intake, object storage, and background OCR/text-extraction pipeline:

### Critical Domain Boundary
> **"Document extraction is not clinical verification."**  
> **"Extracted content does not automatically update the patient's clinical record."**  
> Extraction results represent machine-read document transcriptions for clinical review only. They never automatically create or mutate allergies, vitals, condition histories, or medications.

### Document Lifecycle & Processing States
- **Document Lifecycle**: `UPLOADING` → `UPLOADED` → `QUEUED` → `PROCESSING` → `EXTRACTED` (or `FAILED`) → `ARCHIVED`.
- **Processing Job Status**: `PENDING`, `QUEUED`, `PROCESSING`, `COMPLETED`, `FAILED`.
- **Separation of Concerns**: Document record existence is decoupled from job processing status; a failed processing job preserves the source document binary in storage.
- **Idempotency**: Reprocessing an already extracted document safely returns the existing extraction without redundant execution.
- **Controlled Retries**: Transient failures can be retried up to `MAX_PROCESSING_RETRIES` (default: 3).

### Secure Storage & OCR Architecture
- **Object Storage Abstraction**: `DocumentStorage` decouples business logic from storage backends (`LocalDocumentStorage`, S3, cloud blob stores).
- **Private Storage**: Documents are stored under randomized, safe internal keys (`documents/{patient_id}/{doc_id}/{token}.ext`). No public bucket access is permitted.
- **Controlled Download Access**: Short-lived, signed authorization tokens are issued strictly after evaluating patient relationship and consent.
- **OCR & Extraction Abstraction**: `OCRProvider` and `DocumentProcessorRegistry` route document types to appropriate processors (`GenericDocumentProcessor`), recording extraction provenance (processor name, version, timestamp, page counts, confidence).
- **Malware Scanning Hook**: Uploaded bytes pass through `DocumentSecurityScanner` (supporting EICAR signatures and enterprise antivirus hooks) prior to persistence.
- **PHI Scrubbing**: Audit event metadata records only opaque identifiers and timestamps; document content, OCR transcriptions, and clinical texts are strictly excluded.

### Document API Endpoints
| Method | Path | Description | Access |
|---|---|---|---|
| `POST` | `/api/v1/patients/{id}/documents` | Multipart document upload + enqueue background OCR | Patient (self) / Doctor (treating) |
| `GET` | `/api/v1/patients/{id}/documents` | List patient document metadata | Patient (self) / Doctor (treating) |
| `GET` | `/api/v1/patients/{id}/documents/{doc_id}` | Retrieve document metadata & processing status | Patient (self) / Doctor (treating) |
| `GET` | `/api/v1/patients/{id}/documents/{doc_id}/download` | Generate short-lived signed download authorization URL | Patient (self) / Doctor (treating) |
| `POST` | `/api/v1/patients/{id}/documents/{doc_id}/retry` | Retry failed processing within retry limits | Authorized uploader / provider |
| `GET` | `/api/v1/patients/{id}/documents/{doc_id}/extraction` | View structured OCR extraction result | Patient (self) / Doctor (treating) |
| `POST` | `/api/v1/patients/{id}/documents/{doc_id}/archive` | Soft-delete / archive document | Patient (self) / Doctor (treating) |

---

## 15. Phase Status Summary

| Phase | Component | Status |
|---|---|---|
| **Phase 1** | Application startup & lifecycle | ✅ IMPLEMENTED |
| **Phase 1** | Environment configuration | ✅ IMPLEMENTED |
| **Phase 1** | API versioning | ✅ IMPLEMENTED |
| **Phase 1** | Liveness & readiness probes | ✅ IMPLEMENTED |
| **Phase 1** | Correlation ID middleware | ✅ IMPLEMENTED |
| **Phase 1** | Structured JSON logging | ✅ IMPLEMENTED |
| **Phase 1** | Centralized error handling | ✅ IMPLEMENTED |
| **Phase 1** | Security headers & CORS | ✅ IMPLEMENTED |
| **Phase 1** | Service / Repository pattern | ✅ IMPLEMENTED |
| **Phase 1** | Database engine boundary | ✅ IMPLEMENTED |
| **Phase 1** | Docker & Compose | ✅ IMPLEMENTED |
| **Phase 2** | Argon2id password hashing | ✅ IMPLEMENTED |
| **Phase 2** | JWT access tokens | ✅ IMPLEMENTED |
| **Phase 2** | Refresh token (hashed, rotatable) | ✅ IMPLEMENTED |
| **Phase 2** | Token reuse detection | ✅ IMPLEMENTED |
| **Phase 2** | `POST /auth/login` | ✅ IMPLEMENTED |
| **Phase 2** | `POST /auth/refresh` | ✅ IMPLEMENTED |
| **Phase 2** | `POST /auth/logout` | ✅ IMPLEMENTED |
| **Phase 2** | `GET /auth/me` | ✅ IMPLEMENTED |
| **Phase 2** | `get_current_user` reusable dependency | ✅ IMPLEMENTED |
| **Phase 2** | AuthenticatedUserContext | ✅ IMPLEMENTED |
| **Phase 2** | Account status enforcement | ✅ IMPLEMENTED |
| **Phase 2** | Anti-enumeration error messages | ✅ IMPLEMENTED |
| **Phase 2** | Security event logging | ✅ IMPLEMENTED |
| **Phase 2** | Clinical data exclusion from JWT | ✅ IMPLEMENTED |
| **Phase 3** | Centralized Policy Registry | ✅ IMPLEMENTED |
| **Phase 3** | AuthorizationService (RBAC + Ownership + Relationship + Consent) | ✅ IMPLEMENTED |
| **Phase 3** | Consent management service & repository | ✅ IMPLEMENTED |
| **Phase 3** | Consent API endpoints (`/api/v1/consents`) | ✅ IMPLEMENTED |
| **Phase 3** | Audit event emission for authorization & consent decisions | ✅ IMPLEMENTED |
| **Phase 4** | Patient profile lifecycle (`/api/v1/patients/{id}`) | ✅ IMPLEMENTED |
| **Phase 4** | Clinical history management (`/patients/{id}/history`) | ✅ IMPLEMENTED |
| **Phase 4** | Allergy tracking (`/patients/{id}/allergies`) | ✅ IMPLEMENTED |
| **Phase 4** | Vitals append-only recording (`/patients/{id}/vitals`) | ✅ IMPLEMENTED |
| **Phase 4** | Clinical encounters (`/patients/{id}/encounters`) | ✅ IMPLEMENTED |
| **Phase 4** | Clinical summary assembly (`/patients/{id}/clinical-summary`) | ✅ IMPLEMENTED |
| **Phase 4** | PHI redaction & anti-enumeration 404 security | ✅ IMPLEMENTED |
| **Phase 5** | Secure document upload & validation | ✅ IMPLEMENTED |
| **Phase 5** | Object storage abstraction (`DocumentStorage`) | ✅ IMPLEMENTED |
| **Phase 5** | OCR & text extraction provider (`OCRProvider`) | ✅ IMPLEMENTED |
| **Phase 5** | Document processing worker & idempotency | ✅ IMPLEMENTED |
| **Phase 5** | Structured extraction & provenance tracking | ✅ IMPLEMENTED |
| **Phase 5** | Malware scanning hook (`DocumentSecurityScanner`) | ✅ IMPLEMENTED |
| **Phase 5** | Short-lived signed download authorization | ✅ IMPLEMENTED |
| **Phase 5** | Controlled retry & failure handling | ✅ IMPLEMENTED |
| **Phase 5** | Document endpoints (`/patients/{id}/documents`) | ✅ IMPLEMENTED |
| **Phase 5** | Clinical domain boundary enforcement | ✅ IMPLEMENTED |
| **Phase 6** | Prescription domain service & items (`/patients/{id}/prescriptions`) | ✅ IMPLEMENTED |
| **Phase 6** | Phase 5 extraction ingestion & mapper | ✅ IMPLEMENTED |
| **Phase 6** | Raw medication value preservation | ✅ IMPLEMENTED |
| **Phase 6** | Terminology provider abstraction (`MedicationTerminologyProvider`) | ✅ IMPLEMENTED |
| **Phase 6** | Local mock terminology provider & RxNorm adapter | ✅ IMPLEMENTED |
| **Phase 6** | Strength, dosage-form, and route data normalization | ✅ IMPLEMENTED |
| **Phase 6** | Disambiguation & ambiguity handling (no guessing) | ✅ IMPLEMENTED |
| **Phase 6** | Patient longitudinal medication records (`/patients/{id}/medications`) | ✅ IMPLEMENTED |
| **Phase 6** | Prescription vs active medication separation | ✅ IMPLEMENTED |
| **Phase 6** | Provenance chain tracking across documents & prescriptions | ✅ IMPLEMENTED |
| **Phase 6** | Human review & correction workflow with audit history | ✅ IMPLEMENTED |
| **Phase 6** | Data-level duplicate detection without clinical claims | ✅ IMPLEMENTED |
| **Phase 7** | Medication safety provider abstraction (`MedicationSafetyProvider`) | ✅ IMPLEMENTED |
| **Phase 7** | Deterministic mock safety provider (`MockMedicationSafetyProvider`) | ✅ IMPLEMENTED |
| **Phase 7** | Licensed provider adapter stub with credential validation | ✅ IMPLEMENTED |
| **Phase 7** | Drug-Drug Interaction (DDI) checking & normalization | ✅ IMPLEMENTED |
| **Phase 7** | Drug-Allergy conflict evaluation (Phase 4 allergy linkage) | ✅ IMPLEMENTED |
| **Phase 7** | Drug-Disease interaction evaluation (Phase 4 conditions) | ✅ IMPLEMENTED |
| **Phase 7** | Contraindication & Duplicate Therapy detection | ✅ IMPLEMENTED |
| **Phase 7** | Provider failure safety (UNKNOWN/ERROR, never false CLEAR) | ✅ IMPLEMENTED |
| **Phase 7** | Prospective new medication checking (`check-medications`) | ✅ IMPLEMENTED |
| **Phase 7** | Patient data minimization for external providers (zero PHI leaks) | ✅ IMPLEMENTED |
| **Phase 7** | Immutable evaluations & audit event integration | ✅ IMPLEMENTED |
| **Database Team** | PostgreSQL schema & migrations | 🔲 PENDING CONTRACT |
| **Phase 8** | Triage & SBAR (Structured Clinical Communication) | ⏳ UPCOMING |

---

## Phase 7 — Medication Safety System Architecture

### Pipeline
```
Patient
   ↓
Current Medication Context (Phase 6 Active Medications)
   ↓
Normalized Medication Identifiers (RxNorm / Canonical Codes)
   ↓
Medication Safety Service
   ↓
Licensed / Authoritative Safety Provider (FDB / DrugBank / Synthetic Mock)
   ↓
Safety Evidence (DDI, Allergy Cross-Reactivity, Contraindications)
   ↓
Normalized Safety Result (CRITICAL, MAJOR, MODERATE, MINOR, INFO)
   ↓
Patient / Clinician Review
```

### Critical Clinical Safety Boundaries
> [!IMPORTANT]
> **Safety results are clinical decision-support evidence, NOT autonomous clinical decisions.**
> 1. **Zero Autonomous Clinical Action**: Phase 7 NEVER automatically cancels prescriptions, changes dosages, stops medications, or generates allergy records.
> 2. **Provider Failure Safety**: If the external safety provider times out or fails, the system returns `UNKNOWN` or `ERROR`. It **NEVER** yields a false `CLEAR` status.
> 3. **No LLM Clinical Authority**: Large language models must NEVER independently determine clinical medication safety. Authoritative evidence must originate from licensed clinical databases.
> 4. **RxNorm & openFDA Boundary**: Neither RxNorm nor openFDA alone constitute a complete medication safety or interaction checking engine.

### Phase 7 API Endpoints

| Method | Path | Auth / Scope | Description |
|---|---|---|---|
| `POST` | `/api/v1/patients/{id}/medication-safety/check` | `medication_safety:check` | Evaluate patient active/selected medications for interactions, allergies, and contraindications |
| `POST` | `/api/v1/patients/{id}/medication-safety/check-medications` | `medication_safety:check` | Evaluate prospective new medications against current patient medications and allergies |
| `GET` | `/api/v1/patients/{id}/medication-safety/capabilities` | `medication_safety:read` | Retrieve supported capabilities for configured safety provider |
| `GET` | `/api/v1/patients/{id}/medication-safety/evaluations/{eval_id}` | `medication_safety:read` | Retrieve full details, findings, alerts, and provenance for a specific evaluation |
| `GET` | `/api/v1/patients/{id}/medication-safety/evaluations` | `medication_safety:read` | List historical evaluations with pagination, date, and status filtering |


