# Health Setu: database handoff (for the backend dev)

The database is **PostgreSQL**. The important logic lives *inside* it as SQL functions, so your backend
only needs to connect and call them. Do not port it to Firebase/MongoDB: that would lose the consent rules,
the safety check, the append-only triggers and the bed double-booking constraints.

## What you are getting

| File | What it is | When to use |
|---|---|---|
| `health_setu_dump.sql.gz` | Ready-made database (15k patients, 9 hospitals, ~170 MB restored) | Fastest start. Restore once, done. |
| `storage.zip` | The uploaded prescription / lab-report images the database points to (`documents.storage_uri` is relative to this folder) | Unzip next to your backend; set `STORAGE_DIR` to it |
| `health-setu-data.zip` | Source: schema, SQL functions, seeder, a working FastAPI layer (`api/`) | To re-seed fresh data, or to copy routes from |

## Option A: one shared database on Supabase (recommended for a 3-person team)

Everyone (backend, frontend, you) uses the same data, no Docker needed. Free tier is enough (500 MB).

1. Create a **new, separate** Supabase project for this. Copy the connection string from
   *Connect → Session pooler* (it works on IPv4 networks; the "direct" one may not).
2. Load the data (needs `psql` installed):
   ```bash
   gunzip -c health_setu_dump.sql.gz | psql "postgresql://postgres.xxxx:PASSWORD@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"
   ```
3. **Lock it down (important).** Supabase auto-exposes tables in `public` through its REST API to anyone with the
   anon key. Our backend should be the only way in, so run this in the Supabase SQL editor:
   ```sql
   REVOKE ALL ON ALL TABLES    IN SCHEMA public FROM anon, authenticated;
   REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;
   REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM anon, authenticated;
   DO $$ DECLARE t text; BEGIN
     FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
       EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
     END LOOP;
   END $$;
   ```
   The backend connects as `postgres` (the table owner), so it is not affected.
   **Do not use supabase-js in the frontend to read these tables.** The frontend talks only to the backend.
4. Backend `.env`: `DATABASE_URL=<the pooler string>` and `STORAGE_DIR=./storage`.

## Option B: local PostgreSQL (each dev has their own copy)

```bash
createdb health_setu
gunzip -c health_setu_dump.sql.gz | psql health_setu
```
or, with Docker, from `health-setu-data/`: `docker compose up -d db && docker compose run --rm seeder`.

## The functions your API should call (don't re-implement these)

| Feature | SQL |
|---|---|
| What a doctor may see (+ why, per row) | `SELECT * FROM doctor_visible_timeline(doctor_id, patient_id)` |
| "N records held elsewhere" | `SELECT hidden_record_count(doctor_id, patient_id)` |
| Log that a doctor opened records | `SELECT log_record_access(doctor_id, patient_id)` |
| Medication safety check | `SELECT * FROM medication_safety_check(doctor_id, patient_id, ARRAY[new_med_ids]::int[])` |
| Consent | `request_consent(doctor, patient, scope[], purpose, hours, message)` → id · `approve_consent(request_id, scope[] = NULL, hours = NULL)` → grant id · `deny_consent(request_id)` · `revoke_consent(grant_id, reason)` |
| Bed search | `SELECT * FROM search_facilities(lat, lon, 'icu', NULL, 25)` |
| Patient timeline | `SELECT * FROM v_timeline WHERE patient_id = $1 AND NOT is_superseded ORDER BY occurred_at` |
| Uploads awaiting review | `v_pending_extractions` · Directory: `v_facility_directory` · Active grants: `v_active_consents` |

Rule errors come back as Postgres exceptions (e.g. `Request 355 is not pending`); return them as HTTP 400.
Every one of these is already wired up in `api/` (FastAPI). Copy the SQL from there even if you use another framework.

**Two rules the database enforces:** `documents` and `timeline_events` are append-only (UPDATE/DELETE raise an
error; corrections are new rows with `supersedes_event_id`). And every login, view and consent action should
write to `audit_log`.

## Logins (password `demo@123`)
Patients `subrata`, `rupa` · Doctors `dr.meera`, `dr.kaushik`, `dr.sourav`, `dr.arindam`, `dr.tanushree` ·
Hospital admins `admin.gvh`, `admin.hjh`, … (`admin.<facility code>`).
Passwords are stored as `sha256$<salt>$<hex of sha256(salt + password)>`. See `check_password` in `api/auth.py`.

## Reset before judging

The data is relative to *when it was generated*: bed reports age, consents expire, "yesterday's" prescription
gets older, and rehearsals add rows. **About 30 minutes before judging, reload fresh data** (1 minute):
```bash
python seed.py --database-url "<DATABASE_URL>" --storage-dir ./storage
```
The seeder drops and recreates the `public` schema. That is why Supabase must be a separate project for this.
On Supabase, **run the lock-down SQL from step 3 again** after every re-seed.
The seeder also rewrites the images in `./storage`, so the backend must use that same folder.
If the seeder fails on Supabase, drop the tables and restore the dump again instead.

Everything is synthetic. Not connected to ABDM or any real hospital.
