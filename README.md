# HealthSetu — Backend Foundation (Phase 1)

HealthSetu is a unified healthcare interoperability, clinical coordination, and patient safety backend platform.

Phase 1 establishes the production-oriented engineering foundation of the backend application without business-domain logic or database schema ownership.

---

## 1. Architectural Principles & Boundaries

### Team Boundary: Database Ownership
- **Database Schema, Models, and Migrations are owned exclusively by the Database Team.**
- The backend application establishes an asynchronous connection, session factory, and generic repository boundary (`SQLAlchemy 2.x`), but does **not** create or manage clinical/business database tables or Alembic migrations in this phase.
- If the database is unreachable, the application starts gracefully and reports its readiness state accurately via `/api/v1/ready`.

### Clean Layered Architecture
```
API Layer (/api/v1/...)
    ↓ (Dependency Injection)
Service Layer (app/services)
    ↓
Repository Layer (app/repositories)    →    External Integration Adapters (app/integrations)
    ↓                                                 ↓
Database (PostgreSQL Async Engine)          External Healthcare APIs (Future)
```

---

## 2. Technology Stack

- **Runtime**: Python 3.12+
- **Framework**: FastAPI
- **Validation & Settings**: Pydantic v2 & `pydantic-settings`
- **ASGI Server**: Uvicorn
- **Database Access Layer**: SQLAlchemy 2.x Async Engine (`asyncpg`)
- **Testing**: `pytest`, `pytest-asyncio`, `httpx`
- **Containerization**: Docker (multi-stage non-root runtime) & Docker Compose

---

## 3. Directory Structure

```text
healthsetu-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # Application entrypoint & lifespan
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py            # Root API router (v1, future v2)
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py        # v1 router aggregator
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           └── health.py    # Health & readiness probes
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # Environment-based Pydantic settings
│   │   ├── database.py          # SQLAlchemy 2.x async engine & session boundary
│   │   ├── exceptions.py        # Centralized exception handling & error models
│   │   ├── logging.py           # Structured JSON logging & sensitive data scrubber
│   │   ├── middleware.py        # Request ID, security headers, size limiting
│   │   └── security.py          # Baseline security headers & origin validation
│   ├── services/
│   │   ├── __init__.py
│   │   ├── base.py              # Generic base service
│   │   └── health.py            # Health probe service
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── base.py              # Generic base repository
│   ├── integrations/            # Future external healthcare adapters
│   │   ├── __init__.py
│   │   ├── base.py              # Base adapter interface
│   │   ├── medication_safety/   # DrugBank, openFDA, RxNorm (Phase 2+)
│   │   ├── ai/                  # Clinical decision assistance (Phase 2+)
│   │   ├── ocr/                 # Document OCR processing (Phase 2+)
│   │   ├── translation/         # Medical vernacular translation (Phase 2+)
│   │   ├── fhir/                # HL7 FHIR interoperability (Phase 2+)
│   │   └── abdm/                # Ayushman Bharat Digital Mission (Phase 2+)
│   ├── models/                  # Database models (owned by Database Team)
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── response.py          # Standardized response envelopes
│   └── utils/
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures & async test client
│   ├── test_config.py           # Settings & parser tests
│   ├── test_cors.py             # CORS & security headers tests
│   ├── test_database.py         # Database engine boundary & error tests
│   ├── test_error_handling.py   # Centralized error formats & status codes
│   ├── test_health.py           # Liveness probe tests
│   ├── test_readiness.py        # Readiness probe tests (ready & degraded)
│   ├── test_request_id.py       # Correlation ID preservation & generation
│   └── test_startup.py          # Application lifespan & OpenAPI spec
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

| Variable | Type | Default | Description |
|---|---|---|---|
| `APP_NAME` | string | `HealthSetu` | Application service name |
| `APP_ENV` | string | `development` | Environment (`development`, `testing`, `production`) |
| `APP_VERSION` | string | `0.1.0` | Semantic version |
| `DEBUG` | boolean | `false` | Debug mode (disabled in production) |
| `HOST` | string | `0.0.0.0` | Host binding |
| `PORT` | integer | `8000` | Port binding |
| `DATABASE_URL` | string | `None` | Async PostgreSQL URL (`postgresql+asyncpg://...`) |
| `CORS_ALLOWED_ORIGINS` | string | `http://localhost:3000` | Comma-separated list of allowed origins |
| `LOG_LEVEL` | string | `INFO` | Log severity level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `API_PREFIX` | string | `/api/v1` | Base API route prefix |
| `REQUEST_ID_HEADER` | string | `X-Request-ID` | Header used for request correlation |
| `MAX_REQUEST_SIZE_BYTES` | integer | `10485760` | Maximum request payload size (10MB) |

---

## 5. Local Setup & Running

### Prerequisites
- Python 3.12+
- Git

### 1. Create Virtual Environment
```bash
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Start Development Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The application starts at `http://localhost:8000`.

- Interactive API Docs (Swagger): `http://localhost:8000/docs`
- ReDoc API Docs: `http://localhost:8000/redoc`
- OpenAPI Specification: `http://localhost:8000/openapi.json`

*(Note: API documentation is automatically disabled in production mode).*

---

## 6. Testing

Run the automated test suite with `pytest`:

```bash
# Run all tests
pytest -v

# Run with test coverage
pytest --cov=app tests/
```

All 30 automated tests execute in under 1 second without external network or database dependencies.

---

## 7. Docker & Local Development Containers

### Build and Run with Docker
```bash
docker build -t healthsetu-backend:latest .
docker run -p 8000:8000 --env-file .env healthsetu-backend:latest
```

### Run Full Dev Stack with Docker Compose
```bash
docker-compose up --build
```
This boots:
1. `healthsetu-backend`: FastAPI with live volume reload.
2. `healthsetu-dev-postgres`: Local PostgreSQL 16 container for connectivity testing.

---

## 8. Core API Endpoints (Phase 1)

### Liveness Probe
- **Endpoint**: `GET /api/v1/health`
- **Authentication**: None required
- **Status Code**: `200 OK`
- **Response**:
```json
{
  "status": "ok",
  "service": "healthsetu-backend",
  "version": "0.1.0"
}
```

### Readiness Probe
- **Endpoint**: `GET /api/v1/ready`
- **Authentication**: None required
- **Status Codes**:
  - `200 OK` when dependencies are healthy
  - `503 Service Unavailable` when database or critical services are down
- **Response (Ready)**:
```json
{
  "status": "ready",
  "checks": {
    "database": "ok"
  }
}
```
- **Response (Degraded / DB Unavailable)**:
```json
{
  "status": "not_ready",
  "checks": {
    "database": "unavailable"
  }
}
```

### Error Response Envelope
All error responses adhere to the standard schema:
```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Resource not found.",
    "request_id": "a4d3bf98-727b-4021-9971-d00ea4cebe8a"
  }
}
```
Supported error codes:
- `VALIDATION_ERROR` (422 / 413)
- `NOT_FOUND` (404)
- `UNAUTHORIZED` (401)
- `FORBIDDEN` (403)
- `CONFLICT` (409)
- `INTERNAL_ERROR` (500)
- `SERVICE_UNAVAILABLE` (503)

---

## 9. Healthcare Privacy & Logging Safety

In strict compliance with healthcare data protection standards:
- All logs are formatted as structured JSON lines.
- Automatic redaction is applied to request context, intercepting clinical tokens, patient identifiers, prescriptions, diagnoses, and secrets.
- Unhandled internal errors log stack traces internally with correlation IDs, but **never** return raw stack traces or database errors to API clients.

---

## 10. Phase 1 Implementation Status Matrix

| Component | Status | Details |
|---|---|---|
| FastAPI Application & Lifespan | **IMPLEMENTED** | App factory, lifespan lifecycle, clean shutdown |
| Environment Configuration | **IMPLEMENTED** | Pydantic Settings v2, `.env.example`, origin parser |
| API Versioning (`/api/v1/`) | **IMPLEMENTED** | Modular router architecture ready for v2 |
| Liveness Probe (`/api/v1/health`) | **IMPLEMENTED** | Process health indicator |
| Readiness Probe (`/api/v1/ready`) | **IMPLEMENTED** | Async DB health check with 200/503 status |
| Correlation ID (`X-Request-ID`) | **IMPLEMENTED** | Validates/preserves incoming ID or generates UUID4 |
| Structured Logging | **IMPLEMENTED** | JSON formatter, contextual request_id, clinical scrubbing |
| Centralized Error Handling | **IMPLEMENTED** | Standard error envelopes, no stack trace leakage |
| Baseline Security Middleware | **IMPLEMENTED** | Security headers, size limits, origin check |
| CORS Configuration | **IMPLEMENTED** | Configurable allowed origins, wildcards blocked in prod |
| Service / Repository Pattern | **IMPLEMENTED** | Base classes ready for domain injection |
| External Integration Layer | **PLACEHOLDER** | Abstract adapter, packages created for ABDM, FHIR, AI, OCR, etc. |
| Database Engine Boundary | **IMPLEMENTED** | SQLAlchemy 2.x async engine & session pool; no schema invented |
| Automated Test Suite | **IMPLEMENTED** | 30 tests covering all Phase 1 foundations |
| Docker & Docker Compose | **IMPLEMENTED** | Non-root production Dockerfile & local dev compose |
| Clinical Decision-Making | **NOT IMPLEMENTED** | Deferred to subsequent phases |
| Authentication / Authorization | **NOT IMPLEMENTED** | Deferred to Phase 2 |
| Frontend | **NOT IMPLEMENTED** | Out of scope |
| Clinical Database Schema | **NOT IMPLEMENTED** | Owned by Database Team |
