# HealthSetu — Phase 15: Privacy & Data Protection Architecture

**Document Version:** 1.0.0  
**Phase:** 15 (Security, Audit & Compliance Hardening)  
**Notice:** This document outlines technical privacy safeguards and architectural controls. It does NOT claim formal legal certification under HIPAA, GDPR, or state healthcare privacy acts without independent assessment.

---

### 1. Healthcare Privacy Principles

HealthSetu adheres to five core privacy engineering principles:

1. **Data Minimization:** Only transmit and persist the minimum necessary clinical fields required for the authorized workflow.
2. **Strict Purpose Binding:** Consent records tie access to explicit purposes (`care_delivery`, `referral`, `second_opinion`, `emergency`). Access attempts outside the granted purpose are blocked.
3. **Zero PHI in Secondary Telemetry:** Standard application logs, security event streams, metrics, and error responses MUST NEVER contain Protected Health Information (PHI).
4. **Segregation of Identity and Clinical Data:** Administrative functions (e.g. user directory management) do not have visibility into clinical diagnoses or records.
5. **No AI Provider Model Training:** Patient data processed through external LLMs or intelligence engines must not be retained or used for foundation model training.

---

### 2. PHI-Safe Logging Architecture

All logging passes through [app/core/log_sanitizer.py](file:///c:/Users/SAYAN/OneDrive/Desktop/HealthSetu/app/core/log_sanitizer.py):

- **Key Matching:** Case-insensitive check against exact sensitive field names (`diagnosis`, `prescription`, `ssn`, `dob`, `clinical_notes`, etc.) and substring matches.
- **Pattern Matching:** Regex redaction of JWT tokens, Bearer tokens, and API keys embedded in string messages.
- **Header Redaction:** Stripping of `Authorization`, `Cookie`, and client tokens from HTTP request headers prior to output.
- **Recursive Sanitization:** Deep traversal of dictionaries, lists, and tuples up to a max depth guard to prevent stack overflow.

---

### 3. Error Response Privacy

When API exceptions occur:
- Clients receive a standardized JSON response conforming to `StandardErrorResponse`.
- Internal stack traces, raw SQL queries, database hostnames, and clinical text are never reflected in response bodies.
- A unique correlation `request_id` is returned to the client to facilitate administrative tracing without leaking sensitive context.

---

### 4. AI & Cloud Provider Privacy Safeguards

- `AI_TRAINING_OPT_IN` is hardcoded to `False` by default; startup validation fails closed if set to `True` in production.
- `AI_DATA_RETENTION_MODE` must be configured as `disabled` or `stateless` with external AI providers to prevent vendor-side caching of patient prompts.
- Delimiter boundaries prevent patient data from being interpreted as system prompt modifications.
