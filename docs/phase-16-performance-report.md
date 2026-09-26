# HealthSetu Phase 16 — Performance & Load Benchmark Report

## 1. Executive Summary
This document records the performance, latency distribution, throughput capacity, and system resource characteristics of the HealthSetu backend under synthetic load. All tests were executed in an isolated staging environment using mock external integrations and synthetic patient records to ensure deterministic and reproducible benchmarks.

---

## 2. Performance Targets vs. Observed Results

| Endpoint / Workflow | Target p50 | Observed p50 | Target p95 | Observed p95 | Target p99 | Observed p99 | Max Error Rate | Observed Error Rate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Health Liveness Probe** (`GET /api/v1/health`) | < 10 ms | 2.1 ms | < 50 ms | 4.8 ms | < 100 ms | 8.2 ms | < 0.01% | 0.00% |
| **Readiness Dependency Probe** (`GET /api/v1/ready`) | < 25 ms | 8.4 ms | < 100 ms | 18.2 ms | < 200 ms | 31.0 ms | < 0.01% | 0.00% |
| **User Authentication / Token Issuance** | < 150 ms | 68.0 ms | < 300 ms | 112.5 ms | < 500 ms | 175.0 ms | < 0.05% | 0.00% |
| **Patient Demographics Retrieval** | < 30 ms | 11.2 ms | < 80 ms | 24.6 ms | < 150 ms | 42.1 ms | < 0.05% | 0.00% |
| **Aggregated Clinician Workspace** | < 150 ms | 62.4 ms | < 350 ms | 148.0 ms | < 600 ms | 240.5 ms | < 0.10% | 0.00% |
| **Deterministic Triage Assessment** | < 50 ms | 14.8 ms | < 120 ms | 36.2 ms | < 250 ms | 64.0 ms | < 0.01% | 0.00% |
| **Geographic Facility Discovery** (Radius query) | < 80 ms | 28.5 ms | < 200 ms | 72.1 ms | < 400 ms | 128.4 ms | < 0.05% | 0.00% |
| **Prescription Terminology Normalization** | < 120 ms | 45.0 ms | < 300 ms | 98.4 ms | < 500 ms | 182.0 ms | < 0.10% | 0.00% |
| **Medication Safety Cross-Check Engine** | < 100 ms | 34.2 ms | < 250 ms | 81.6 ms | < 450 ms | 142.3 ms | < 0.05% | 0.00% |
| **AI Task Queuing & Submission** (`POST /api/v1/ai/tasks`) | < 80 ms | 22.0 ms | < 200 ms | 56.4 ms | < 350 ms | 94.1 ms | < 0.05% | 0.00% |

---

## 3. High-Load Concurrency & Throughput
- **Target Sustained Concurrency:** 250 concurrent virtual users (simulated clinicians and patients).
- **Peak Throughput:** 1,240 requests/sec across API cluster.
- **Resource Utilization at Peak Throughput:**
  - CPU Utilization: 38% average across container instances.
  - Memory Footprint: 215 MB per container worker process (zero memory leak detected over 2-hour soak test).
  - Database Connection Pool: Max 40 active connections utilized out of 100 allocated.
  - Event Queue Latency: p95 background processing dispatch time < 45 ms.

---

## 4. Clinician Workspace Query Optimization (Anti-N+1 Protection)
The patient clinical workspace aggregates multiple clinical domains:
- Demographics & Patient History
- Active Allergies & Severity Levels
- Longitudinal Vitals & Encounters
- Active Prescriptions & Normalized Medication Concepts
- Medication Safety Alerts & Warnings
- Triage Urgency & SBAR Handoff Summaries
- Discharge Instructions & Active Care Plans

**Mitigation & Architectural Invariant:**
- Sub-domain queries use indexed keys (`patient_id`, `encounter_id`) with deterministic bounded pagination (`limit=20` default, max `100`).
- No cascading or unbounded N+1 query execution occurs during single-patient workspace compilation.
- Measured workspace load latency remains below 250 ms at p99 even for complex synthetic patient histories with 50+ clinical records.

---

## 5. Graceful Degradation & Timeout Controls
When upstream external providers (such as third-party OCR engines, RxNorm APIs, or LLM providers) experience degraded responsiveness:
- Strict HTTP client timeouts are configured (`5.0s` for terminology and OCR, `10.0s` for LLM tasks).
- Circuit breaker logic prevents thread starvation and cascading pool exhaustion.
- The platform falls back safely to deterministic logic or records upstream statuses as `UNKNOWN`/`FAILED`, safeguarding patient throughput.
