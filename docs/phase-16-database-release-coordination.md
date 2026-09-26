# HealthSetu Phase 16 — Database Release Coordination Protocol

## 1. Team Ownership & Operational Boundaries

| Area / Responsibility | Owner Team | Boundaries & Constraints |
| :--- | :--- | :--- |
| **Application Domain Logic & Repositories** | Backend Team | Implements data access patterns, ORM/repository layers, entity validation, and transactional rollbacks. |
| **Database Schema, DDL & Indexes** | Database Team | Exclusively designs and creates tables, indexes, constraints, foreign keys, partition schemes, and column types. |
| **Alembic Migration Scripts** | Database Team | Authoring, testing, and applying migration scripts. Backend team does NOT write or edit migration files. |
| **Database Infrastructure & Performance** | Database Team | PostgreSQL deployment, configuration tuning, connection pooling, replication, vacuuming, and disk sizing. |
| **Backup, Retention & Disaster Recovery** | Database Team | Point-in-time recovery (PITR), automated snapshots, backup encryption, and restore runbooks. |
| **Application Data Compatibility** | Joint (Backend + DB) | Both teams co-validate schema contract compatibility prior to staging or production execution. |

---

## 2. Release & Migration Coordination Workflow

To ensure zero-downtime deployments and prevent schema-application desynchronization:

```
[Phase 1] DB Teammate Prepares Migration
       │
       ▼
[Phase 2] Backend Validates Schema Contract against Repository Layer
       │
       ▼
[Phase 3] Migration Applied in Staging Environment
       │
       ▼
[Phase 4] Automated Backend Integration & Regression Test Suite Run (463 tests)
       │
       ▼
[Phase 5] Sign-off & Controlled Production Migration
       │
       ▼
[Phase 6] Backend Application Rolling Update Deployed
```

### Protocol Steps:
1. **Schema Contract Review:** Database teammate presents DDL changes and migration diff. Backend team verifies entity models and repository queries against proposed columns and constraints.
2. **Backward Compatibility Rule (Expand/Contract):**
   - All migrations must be backward-compatible with the currently running backend version.
   - Column additions must be nullable or possess defaults.
   - Column removals or renames must follow a two-release deprecation cycle (Expand in Release N, Contract in Release N+1).
3. **Staging Execution & Automated Verification:**
   - Database migration is executed on staging PostgreSQL.
   - Backend automated test suite (including `test_patient_safety_journey.py` and `test_concurrency_idempotency.py`) runs against migrated database.
4. **Production Deployment Sequencing:**
   - Database migration runs during maintenance window or live if fully backward-compatible.
   - New backend container image is deployed via rolling update.
   - Health and readiness endpoints are continuously probed.

---

## 3. Backup & Restore Validation (Section 57)
Backend Phase 16 verifies application resilience after a database restore:
1. **Connectivity Re-establishment:** Backend connection pool automatically re-establishes connections upon restored database availability.
2. **Schema & Data Integrity Verification:**
   - Authenticated user records remain retrievable with intact Argon2id password hashes.
   - Patient clinical records, historical vitals, and signed clinical notes retain referential integrity.
   - Non-repudiable audit logs reflect continuous sequential events.
3. **Disaster Recovery Testing:**
   - Restored database snapshot verified in staging with full regression suite run.
