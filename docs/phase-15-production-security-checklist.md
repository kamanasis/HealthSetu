# HealthSetu — Phase 15: Production Security Deployment Checklist

**Document Version:** 1.0.0  
**Phase:** 15 (Security, Audit & Compliance Hardening)  
**Notice:** Complete this checklist prior to promoting any release to staging or production environments.

---

### 1. Configuration & Secrets Hardening

- [ ] **DEBUG Disabled:** Verify `DEBUG=false` in environment configuration. Application will fail startup if `DEBUG=true` in production.
- [ ] **JWT Secret Strength:** Verify `JWT_SECRET_KEY` is a cryptographically random secret of at least 32 bytes (256-bit entropy). Never use default or dictionary strings.
- [ ] **Database Credentials:** Ensure `DATABASE_URL` uses strong, randomly generated credentials and connects over TLS (`sslmode=require` or `verify-full`).
- [ ] **External API Keys:** Verify production API keys are configured for AI (`AI_API_KEY`), medication safety, and interoperability endpoints.
- [ ] **Fail-Closed Verification:** Run startup checks to confirm `enforce_security_config(settings)` succeeds with production environment variables.

---

### 2. Network, CORS & HTTP Headers

- [ ] **CORS Origins Enumerated:** Confirm `CORS_ALLOWED_ORIGINS` explicitly lists allowed HTTPS origins (e.g. `https://app.healthsetu.com`). Wildcard `*` is strictly blocked in production.
- [ ] **HTTPS Enforced:** All external and internal service communications must use TLS 1.3 or TLS 1.2 with secure cipher suites.
- [ ] **HSTS Enabled:** Verify `Strict-Transport-Security` header is active (`max-age=31536000; includeSubDomains; preload`).
- [ ] **Content Security Policy:** Verify `Content-Security-Policy` header restricts frame ancestors (`frame-ancestors 'none'`) and object sources (`object-src 'none'`).
- [ ] **Anti-Sniffing & Framing:** Verify `X-Content-Type-Options: nosniff` and `X-Frame-Options: DENY` are emitted on all API responses.

---

### 3. Rate Limiting & Denial-of-Service Defenses

- [ ] **Rate Limiting Enabled:** Verify `RATE_LIMIT_ENABLED=true` in production configuration.
- [ ] **Authentication Limits:** Ensure `/auth/` routes are capped at tight limits (default: 10 requests/minute per client).
- [ ] **Payload Size Limit:** Confirm `MAX_REQUEST_SIZE_BYTES` is enforced (default: 10 MB).
- [ ] **WAF / Perimeter Protection:** Ensure edge CloudFront / Cloudflare or Kubernetes Ingress rules block volumetric floods before application ingress.

---

### 4. Storage & File Upload Security

- [ ] **Private Cloud Storage:** Ensure `DOCUMENT_STORAGE_PROVIDER` is set to a private object store (e.g. S3 private bucket with KMS encryption) rather than local storage.
- [ ] **Presigned URLs:** Ensure downloads are served exclusively through short-lived presigned URLs, never direct public bucket links.
- [ ] **Magic Bytes Inspection:** Verify file upload pipeline verifies binary headers for PDF, JPEG, PNG, WebP, and DICOM.
- [ ] **Path Traversal Protection:** Verify uploaded filenames are sanitized and storage keys are deterministic server-generated UUID paths.

---

### 5. AI Security & Privacy Settings

- [ ] **Training Opt-In Disabled:** Verify `AI_TRAINING_OPT_IN=false`. Application will fail startup if set to true in production.
- [ ] **Stateless Retention:** Ensure `AI_DATA_RETENTION_MODE` is set to `disabled` or `stateless` with external LLM providers.
- [ ] **Prompt Injection Defense:** Confirm `AISecurityValidator` is active on all untrusted inputs.
- [ ] **Structured Output Validation:** Ensure `AI_STRUCTURED_OUTPUT_ENABLED=true` to enforce strict Pydantic schema validation on generated content.

---

### 6. Audit, Logging & Monitoring

- [ ] **PHI-Safe Logging Active:** Ensure `PHI_SAFE_LOGGING_ENABLED=true` and `app/core/log_sanitizer.py` is engaged.
- [ ] **Audit Trail Immutability:** Verify database table permissions prevent `UPDATE` and `DELETE` on `audit_events`.
- [ ] **Security Event Routing:** Confirm high/critical security events trigger real-time operational alerts in the security monitoring dashboard.
- [ ] **Audit Access Restricted:** Verify only `ADMIN` roles can query audit endpoints.
