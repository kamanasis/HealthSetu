# HealthSetu — Phase 15: Security Incident Response Playbook

**Document Version:** 1.0.0  
**Phase:** 15 (Security, Audit & Compliance Hardening)  
**Notice:** Standard operating procedures for investigating, containing, and remediating security incidents on the HealthSetu platform.

---

### 1. Incident Classification & Severity Matrix

| Severity | Description | Examples | Target Containment SLA |
|---|---|---|---|
| **P1 - CRITICAL** | Active compromise of patient records, credential leak, or complete service denial | Unauthorized bulk data export, active SQL injection, breached JWT secret | < 1 hour |
| **P2 - HIGH** | Potential unauthorized access or targeted exploitation attempt | Blocked SSRF attempt to cloud metadata, repeated privilege escalation, prompt injection attack | < 4 hours |
| **P3 - MEDIUM** | Suspicious automated activity or non-critical security control failure | High rate-limit breach volume, single invalid credential spike, MIME-type mismatch flood | < 24 hours |
| **P4 - LOW** | Informational anomaly or transient configuration warning | Development debug mode enabled in non-prod, single failed login attempt | < 72 hours |

---

### 2. Incident Response Workflow

```
[ Detection & Alerting ]
        │ (SIEM, SecurityEventService, CloudWatch, Prometheus)
        ▼
[ Triage & Classification ]
        │ (Assign Severity P1–P4, determine affected patient/provider scope)
        ▼
[ Containment ]
        │ (Revoke sessions, block offending IPs, rotate credentials, isolate tenant)
        ▼
[ Eradication & Remediation ]
        │ (Patch vulnerability, deploy updated policies, invalidate compromised tokens)
        ▼
[ Recovery & Verification ]
        │ (Restore clean operations, verify audit trail integrity)
        ▼
[ Post-Incident Review ]
        │ (Root-cause analysis, compliance assessment, documentation updates)
```

---

### 3. Scenario-Specific Playbooks

#### Scenario A: Blocked SSRF Attempt to Cloud Metadata (`SSRF_BLOCKED`)
1. **Identify Actor:** Check `SecurityEventService` log for `ip_address`, `actor_id`, and `request_id`.
2. **Review Target URL:** Inspect `metadata.blocked_url_prefix` in the security event record.
3. **Assess Scope:** Check whether the endpoint was public (e.g. document download or webhook registration) or authenticated.
4. **Containment:** If malicious actor is authenticated, immediately revoke their session and set their account status to `SUSPENDED`.
5. **Firewall Rule:** Add the requesting external IP address to the perimeter WAF blocklist.

#### Scenario B: Prompt Injection or Adversarial AI Attack (`PROMPT_INJECTION_DETECTED`)
1. **Identify Source Document:** Extract `task_id` and originating document or clinical note from the event.
2. **Quarantine Content:** Mark the document record lifecycle state as `REJECTED` / `SECURITY_HOLD`.
3. **Verify Model Dispatch:** Confirm that `AISecurityValidator` blocked the request before external LLM dispatch occurred (zero outbound API calls).
4. **Review Clinician / Uploader:** Determine whether the input was an intentional adversarial test or a malicious external upload.

#### Scenario C: Suspected JWT Secret Compromise
1. **Immediate Secret Rotation:** Deploy updated, cryptographically random `JWT_SECRET_KEY` (minimum 32 bytes) in environment variables.
2. **Mass Session Revocation:** All existing tokens signed with the legacy secret will fail verification immediately (`Invalid token signature`).
3. **Audit History Review:** Query `audit_events` for abnormal administrative or clinical queries spanning the suspected exposure window.
4. **Notify Affected Entities:** Initiate compliance review to evaluate breach notification obligations.

---

### 4. Post-Incident Review (PIR) Checklist

- [ ] Complete timeline of incident from initial entry to full containment.
- [ ] Root-cause analysis identifying code, policy, or human factors.
- [ ] Verification that audit trail remained intact and was not tampered with.
- [ ] Action items created with engineering owners and delivery deadlines.
- [ ] Incident report archived in compliance record repository.
