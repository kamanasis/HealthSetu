# HealthSetu Phase 16 — Production Deployment & Operations Guide

## 1. Container & Deployment Architecture
The HealthSetu backend is packaged as an immutable, hardened OCI container image using multi-stage Docker builds.

### Key Deployment Characteristics:
- **Base Image:** Minimal Python 3.12 slim Debian runtime.
- **Security Context:** Runs exclusively as an unprivileged non-root user (`healthsetu`, UID 10001).
- **Attack Surface Minimization:** Build tools, compilers, and development headers are purged in the final image layer.
- **Read-Only Filesystem Compatible:** Ephemeral file storage occurs only in designated `/tmp` or mounted volume storage.

---

## 2. Environment Configuration & Validation (Section 55)
The platform enforces strict startup configuration validation. Startup fails immediately if:
- `DEBUG=True` in a production environment.
- Required secrets (`JWT_SECRET_KEY`, `ENCRYPTION_KEY`) are missing, empty, or use default insecure placeholders.
- Database connection strings are missing or unparseable.
- CORS origins are configured as wildcard `*` with credentials enabled.
- External provider endpoints use unencrypted HTTP rather than HTTPS.

---

## 3. Operational Probes: Health & Readiness (Sections 51 & 52)

### Liveness Health Probe (`GET /api/v1/health`)
- **Purpose:** Verifies that the FastAPI process is active, responding to HTTP traffic, and handling event loop tasks.
- **Privacy & Security Guarantee:** Exposes NO internal secrets, credentials, environment variables, or database connection strings.
- **Response Format:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production"
}
```

### Dependency Readiness Probe (`GET /api/v1/ready`)
- **Purpose:** Verifies runtime connectivity to critical backend dependencies before routing patient traffic:
  - PostgreSQL database connection pool check.
  - Object storage provider accessibility.
  - Background worker thread / queue readiness.
- **Behavior:**
  - Returns HTTP 200 OK when all critical dependencies are accessible (`status: "ready"`).
  - Returns HTTP 503 Service Unavailable when a critical dependency fails (`status: "not_ready"`).
  - Optional third-party providers (e.g., experimental AI engines) do not block core healthcare availability.

---

## 4. Background Workers & Graceful Shutdown (Sections 42 & 54)
- **Signal Handling:** Listens for `SIGTERM` and `SIGINT`.
- **Drain Period:**
  - Stops accepting new inbound HTTP requests immediately upon receiving shutdown signal.
  - Grants a 30-second drain window for active in-flight clinical transactions to commit or rollback cleanly.
  - Closes database connection pools gracefully, preventing broken transaction states.
  - Flushes pending structured audit logs to persistent storage.

---

## 5. Automated CI/CD Pipeline (Section 64)
```
[Git Push to Main / Release Tag]
       │
       ▼
[Lint & Type Check] (Ruff, Flake8, Mypy)
       │
       ▼
[Security & Secret Scan] (Trufflehog / GitLeaks)
       │
       ▼
[Unit & Service Tests] (439 tests)
       │
       ▼
[Docker Multi-Stage Build]
       │
       ▼
[Integration & API Tests]
       │
       ▼
[Clinical Safety Regression (15 Rules)]
       │
       ▼
[End-to-End Patient Safety Journey Test]
       │
       ▼
[Staging Deployment & Smoke Verification]
       │
       ▼
[Production Release Approval & Rolling Update]
```
