# HealthSetu — Phase 15: Centralized Audit Logging Architecture

**Document Version:** 1.0.0  
**Phase:** 15 (Security, Audit & Compliance Hardening)  
**Notice:** This document defines the technical audit architecture. It does NOT claim that HealthSetu is legally certified under HIPAA, GDPR, or other regulations.

---

### 1. Three-Tier Separation of Observability

HealthSetu maintains three strictly segregated telemetry channels to ensure accountability without compromising privacy:

| Channel | Module | Primary Purpose | PHI Handling | Retention / Storage |
|---|---|---|---|---|
| **Application Logs** | `app/core/logging.py` | Operational diagnostics and debugging | Strict recursive redaction via `log_sanitizer.py` | Standard log rotation (e.g. 30–90 days) |
| **Audit Events** | `app/services/audit_service.py` | Regulatory accountability & access history | Metadata filtered to technical keys only; no clinical notes | Immutable append-only storage (e.g. 7 years) |
| **Security Events** | `app/services/security_event_service.py` | Intrusion detection & security anomalies | Strictly PHI-free; captures attack vectors & indicators | Real-time SIEM / security monitoring stream |

---

### 2. Audit Event Structure

Every recorded audit event contains standard envelope attributes:

```json
{
  "id": "audit-4f7e2b1a-8c90-4d56-a123-abcdef012345",
  "event_type": "RECORD_ACCESS",
  "actor_id": "usr-550e8400-e29b-41d4-a716-446655440000",
  "actor_role": "DOCTOR",
  "action": "read",
  "resource_type": "patient_clinical_summary",
  "resource_id": "pat-123e4567-e89b-12d3-a456-426614174000",
  "outcome": "SUCCESS",
  "reason_code": "ACTIVE_ENCOUNTER",
  "ip_address": "198.51.100.42",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
  "request_id": "req-987fc2a1-1234-5678-90ab-cdef12345678",
  "metadata": {
    "organization_id": "org-99",
    "facility_id": "fac-1"
  },
  "created_at": "2026-09-26T03:00:00Z"
}
```

---

### 3. Metadata PHI Redaction Rule

Before any metadata dictionary is persisted to the audit repository, it passes through `_sanitize_metadata()`. The following keys are automatically dropped:
- Credentials: `password`, `token`, `access_token`, `refresh_token`, `secret`, `api_key`
- Clinical Details: `diagnosis`, `diagnoses`, `prescription`, `prescriptions`, `medication`, `medications`, `history`, `medical_history`, `clinical_notes`, `document_content`, `patient_data`, `symptoms`

Only non-clinical structural identifiers (e.g. `organization_id`, `facility_id`, `export_format`) are retained.

---

### 4. Access Governance

- Access to query audit logs is governed strictly by `Permission.ADMIN_AUDIT_READ`.
- Only the `ADMIN` role possesses this permission.
- Clinicians, doctors, and patients cannot access administrative audit trails.
- Audit queries are themselves audited to detect unauthorized investigation of access logs.
