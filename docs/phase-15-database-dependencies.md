# HealthSetu — Phase 15: Security, Audit & Compliance Hardening
## Database Dependencies Specification

**Document Version:** 1.0.0  
**Phase:** 15 (Security, Audit & Compliance Hardening)  
**Boundary:** Backend application layer contract requirements for the database engineering team.  
**Compliance Notice:** This document establishes technical security, audit, and privacy architecture foundations. It does NOT claim that HealthSetu is legally certified or compliant with any specific regulation (HIPAA, GDPR, DISHA, ISO 27001) unless separately assessed and certified by an accredited authority.

---

### 1. Conceptual Architecture & Security Model

Phase 15 hardens all preceding phases (1 through 14) with:
1. **Centralized Immutable Audit Logging:** All access decisions, administrative actions, and consent lifecycle changes must produce tamper-evident audit records.
2. **Security Event Recording:** Authentication anomalies, SSRF attempts, rate limit breaches, and privilege escalation attempts require dedicated security event tracking.
3. **Session & Token Revocation:** Distributed invalidation of JWT tokens (`jti`), refresh tokens, and active sessions.
4. **Rate Limit Persistence:** For multi-instance deployments, token-bucket or sliding-window rate limit state.

---

### 2. Required Database Entities

#### 2.1 Table: `audit_events`
Stores immutable, append-only operational and access audit records.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(64) | PRIMARY KEY | Unique identifier with prefix (e.g. `audit-uuid`) |
| `event_type` | VARCHAR(64) | NOT NULL, INDEXED | Categorical event type (`AUTH_LOGIN_SUCCESS`, `RECORD_ACCESS`, `CONSENT_REVOKED`, etc.) |
| `actor_id` | VARCHAR(64) | NULLABLE, INDEXED | Authenticated user/service UUID who initiated the action |
| `actor_role` | VARCHAR(32) | NULLABLE | Role of the actor at time of action (`DOCTOR`, `PATIENT`, `ADMIN`, etc.) |
| `action` | VARCHAR(64) | NOT NULL | Action attempted (`read`, `create`, `update`, `delete`, `export`) |
| `resource_type` | VARCHAR(64) | NULLABLE, INDEXED | Target resource category (`patient`, `document`, `prescription`, `consent`) |
| `resource_id` | VARCHAR(64) | NULLABLE, INDEXED | Target entity UUID |
| `outcome` | VARCHAR(32) | NOT NULL, INDEXED | `SUCCESS`, `DENIED`, `ERROR` |
| `reason_code` | VARCHAR(64) | NULLABLE | Standardized decision or error reason code |
| `ip_address` | INET | NULLABLE | Client IP address (network layer trace) |
| `user_agent` | VARCHAR(255) | NULLABLE | Client User-Agent header (truncated) |
| `request_id` | VARCHAR(64) | NOT NULL, INDEXED | End-to-end correlation request ID |
| `metadata` | JSONB | NOT NULL DEFAULT '{}'::jsonb | Sanitized non-PHI contextual metadata |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW(), INDEXED | Immutably stamped timestamp (append-only) |

> **Audit Immutability Constraint:**  
> The `audit_events` table MUST NOT permit `UPDATE` or `DELETE` operations. PostgreSQL row-level security or table trigger rules should enforce append-only semantics.

---

#### 2.2 Table: `security_events`
Stores operational security signals, threat indicators, and intrusion detection alerts.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(64) | PRIMARY KEY | Unique identifier (e.g. `secevt-uuid`) |
| `event_type` | VARCHAR(64) | NOT NULL, INDEXED | Security taxonomy type (`SSRF_BLOCKED`, `PROMPT_INJECTION_DETECTED`, `RATE_LIMIT_EXCEEDED`, etc.) |
| `severity` | VARCHAR(32) | NOT NULL, INDEXED | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO` |
| `actor_id` | VARCHAR(64) | NULLABLE, INDEXED | Associated actor identifier if authenticated |
| `endpoint` | VARCHAR(255) | NULLABLE, INDEXED | Target endpoint path (query parameters stripped) |
| `ip_address` | INET | NULLABLE, INDEXED | Source IP address |
| `request_id` | VARCHAR(64) | NULLABLE, INDEXED | Correlation request ID |
| `reason` | VARCHAR(255) | NOT NULL | Human-readable explanation of security decision |
| `metadata` | JSONB | NOT NULL DEFAULT '{}'::jsonb | PHI-free threat parameters (e.g. blocked URL scheme, host pattern) |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW(), INDEXED | Time of event detection |

---

#### 2.3 Table: `revoked_tokens`
Stores revoked JWT `jti` identifiers and refresh token hashes for session invalidation.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `jti` | VARCHAR(64) | PRIMARY KEY | JWT ID claim uniquely identifying the issued token |
| `user_id` | VARCHAR(64) | NOT NULL, INDEXED | User whose token was revoked |
| `revocation_reason` | VARCHAR(64) | NOT NULL | Reason (`LOGOUT`, `PASSWORD_RESET`, `SUSPICIOUS_ACTIVITY`) |
| `expires_at` | TIMESTAMPTZ | NOT NULL, INDEXED | Token expiration time (permits automated vacuuming of expired rows) |
| `revoked_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | Timestamp revocation occurred |

---

### 3. Recommended Indexes & Retention Strategy

1. **`audit_events` Indexes:**
   - Composite index on `(created_at DESC, event_type)` for security dashboard queries.
   - Composite index on `(actor_id, created_at DESC)` for clinician audit history.
   - Composite index on `(resource_type, resource_id, created_at DESC)` for patient access trails.
2. **`revoked_tokens` Retention:**
   - Daily scheduled cleanup removing rows where `expires_at < NOW()`. Once a token has expired naturally by timestamp, it cannot be accepted by the JWT verifier regardless of revocation table presence.
3. **Partitioning:**
   - In high-volume clinical deployments, `audit_events` should be partitioned monthly by `created_at`.
