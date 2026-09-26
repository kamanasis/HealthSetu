# HealthSetu Phase 16 — Production Rollback Strategy & Runbook

## 1. Objective & Rollback Philosophy
The HealthSetu rollback strategy ensures that any unforeseen production instability, data integrity risk, or clinical safety anomaly can be mitigated within minutes by reverting to the previous known-good release candidate without corrupting existing patient records.

---

## 2. Automated Rollback Triggers & Alert Thresholds

A rollback is immediately initiated if any of the following conditions occur post-deployment:
1. **HTTP Error Rate Surge:** 5xx error responses exceed 0.5% of total requests over any 3-minute rolling window.
2. **Readiness Probe Failure:** `/api/v1/ready` returns HTTP 503 for more than 3 consecutive health probe cycles.
3. **Latency Degradation:** p99 latency on core clinical endpoints (`/triage`, `/prescriptions`, `/medication-safety`) exceeds 1,200 ms for 5 minutes.
4. **Clinical Safety Anomaly:** Any occurrence of an ungrounded clinical output, an unauthenticated clinical record modification, or a safety check returning unexpected `CLEAR` on provider failure.
5. **Database Transaction Deadlocks:** Sustained database deadlocks or connection pool exhaustion (>90% saturation for >2 minutes).

---

## 3. Component Rollback Procedures

### A. Application Container Image Rollback
1. **Container Orchestrator Reversion:**
   - In Kubernetes/ECS: Roll back to previous image tag:
     ```bash
     kubectl rollout undo deployment/healthsetu-backend
     ```
   - In Docker Compose:
     ```bash
     IMAGE_TAG=v1.15.0 docker-compose up -d --no-deps backend
     ```
2. **Verification of Rolling Pods:**
   - Confirm new pods pass `/api/v1/health` and `/api/v1/ready` within 30 seconds.
   - Terminate malfunctioning release candidate instances.

### B. Configuration & Secret Rollback
1. If failure is caused by an erroneous environment variable or secret update:
   - Revert environment configuration to the previously archived version in parameter store / secret manager.
   - Trigger a rolling restart of backend workers.

### C. External Provider Fallback
1. If an upstream external provider (e.g., RxNorm, OCR, or AI service) suffers unexpected downtime or breaking contract changes:
   - Toggle feature flag to fallback provider or mock provider mode:
     ```bash
     MEDICATION_TERMINOLOGY_PROVIDER=local
     AI_ENABLED=false
     ```
   - Reload configuration without full container redeployment.

### D. Database Rollback Constraints (Critical Safety Rule)
- **Do NOT execute uncontrolled database down-migrations.**
- Schema changes are authored with expand/contract backward compatibility.
- If a database rollback is strictly required:
  1. Notify Database Team Lead immediately.
  2. The database team reviews down-migration scripts or initiates point-in-time recovery (PITR) to a pre-release snapshot.
  3. Backend team verifies application compatibility with the restored snapshot before re-routing patient traffic.

---

## 4. Post-Rollback Verification & Audit Checklist
- [ ] Application liveness probe returns HTTP 200.
- [ ] Application readiness probe returns HTTP 200 (`status: "ready"`).
- [ ] Clinician workspace access verified for authorized staff.
- [ ] Patient symptom intake and deterministic triage verified.
- [ ] Incident commander records incident in `docs/phase-15-security-incident-response.md`.
- [ ] Incident post-mortem scheduled within 24 hours.
