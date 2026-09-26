# HealthSetu — Phase 15: Security Architecture & Controls

**Document Version:** 1.0.0  
**Phase:** 15 (Security, Audit & Compliance Hardening)  
**Notice:** This document details technical security architecture controls implemented in the HealthSetu backend. It does NOT constitute legal or regulatory certification.

---

### 1. Security Architecture Principles

HealthSetu implements defense-in-depth across the entire application stack:

```
[ Incoming Request ]
        │
        ▼
[ 1. Request ID Middleware ] (Correlation ID injection: X-Request-ID)
        │
        ▼
[ 2. Rate Limiting Middleware ] (Sliding window per-IP and per-user)
        │
        ▼
[ 3. CORS Hardening ] (Strict origin enumeration, no wildcards in prod)
        │
        ▼
[ 4. Request Size Limit Middleware ] (10 MB payload ceiling)
        │
        ▼
[ 5. Security Headers Middleware ] (HSTS, CSP, nosniff, DENY, Referrer-Policy)
        │
        ▼
[ 6. Authentication & Policy Engine ] (Argon2id, short-lived JWT, Deny-by-default)
        │
        ▼
[ 7. Object-Level Access Control & Consent ] (Patient boundary, active relationship)
        │
        ▼
[ 8. Input Sanitization & Threat Guards ] (SSRF blocker, Prompt injection, Path traversal)
        │
        ▼
[ 9. Centralized Audit & PHI-Safe Logging ] (Redaction, separate audit/security event streams)
```

---

### 2. Authentication Hardening

- **Password Storage:** Argon2id with OWASP baseline parameters (`time_cost=2`, `memory_cost=65536` [64MB], `parallelism=1`, `hash_len=32`).
- **Token Format:** Short-lived JWTs (default 30 minutes) containing minimal identity claims (`sub`, `role`, `type`, `iat`, `exp`, `jti`).
- **Zero-PHI Token Rule:** Access tokens strictly exclude clinical details, diagnoses, prescriptions, or patient identifiers other than subject UUID.
- **Fail-Closed Verification:** JWT verification requires cryptographic signature match, non-expired validity, algorithm match, and explicit `type: "access"`.

---

### 3. Authorization & IDOR Defenses

- **Policy Registry:** Centralized in [app/core/policies.py](file:///c:/Users/SAYAN/OneDrive/Desktop/HealthSetu/app/core/policies.py).
- **Separation of Duties:**
  - Administrative roles (`ADMIN`) have user and system management capabilities, but are strictly barred from clinical records (`clinical_record:read`, `prescription:read`, etc.).
  - Clinical roles (`DOCTOR`, `CLINICIAN`) require both role permissions AND a valid clinical relationship or explicit patient consent.
  - Patient self-access is strictly bounded to the patient's own records.
- **Anti-Enumeration Semantics:** Inaccessible patient records return generic 404 (Not Found) rather than 403 (Forbidden) to prevent unauthorized actors from probing patient existence.

---

### 4. Network & SSRF Defenses

Outbound HTTP calls to external providers (medication terminology, AI models, OCR, healthcare registries) pass through [app/core/ssrf_protection.py](file:///c:/Users/SAYAN/OneDrive/Desktop/HealthSetu/app/core/ssrf_protection.py):
- **Blocked IP Ranges:** RFC 1918 (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16), loopback (127.0.0.0/8, ::1), link-local (169.254.0.0/16, fe80::/10), CGNAT, and reserved blocks.
- **Cloud Metadata Protection:** Explicit blocking of AWS/GCP/Azure instance metadata endpoints (`169.254.169.254`, `metadata.google.internal`).
- **DNS Rebinding Protection:** Resolves target hostnames prior to connection to inspect underlying IPs.

---

### 5. AI Safety & Prompt Injection Guards

- **Strict Delimiters:** Untrusted clinical texts are encapsulated within strict structural delimiters before assembly into AI prompts.
- **Adversarial Pattern Matching:** Scans for prompt injection directives ("ignore previous instructions", "jailbroken", "system prompt reveal") and neutralizes or blocks them.
- **Training Opt-In Lock:** `AI_TRAINING_OPT_IN` is strictly `False` by default and validated at startup to ensure patient data is never used for foundation model fine-tuning.

---

### 6. Document & File Upload Security

- **Magic Bytes Validation:** Validates binary headers for PDF (`%PDF`), JPEG (`\xff\xd8\xff`), PNG (`\x89PNG`), WebP (`RIFF`), and DICOM (`DICM`).
- **Path Traversal Neutralization:** Rejects traversal sequences (`../`, `..\`, null bytes) and generates deterministic server-controlled storage keys.
- **Executable Blocking:** Automatic rejection or sanitization of dangerous extensions (`.exe`, `.sh`, `.bat`, `.php`).
