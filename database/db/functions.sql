-- =====================================================================
--  Health Setu — views & functions (business rules live here, so any backend can use them)
-- =====================================================================

-- ---------------------------------------------------------------------
--  TIMELINE
-- ---------------------------------------------------------------------
-- Timeline with a computed verification label (facility records are provider records;
-- uploads are only "patient_verified" once the patient has reviewed the AI extraction).
CREATE VIEW v_timeline AS
SELECT t.id, t.patient_id, t.event_type, t.category, t.occurred_at, t.title, t.summary, t.facility_id, t.source_name,
       t.origin, t.source_table, t.source_id, t.document_id, t.supersedes_event_id,
       CASE WHEN t.origin = 'facility_record' THEN 'provider_record'
            WHEN x.status IN ('verified', 'corrected') THEN 'patient_verified'   -- corrected = patient fixed the AI output
            WHEN x.status = 'rejected'         THEN 'rejected'
            ELSE 'pending_review' END                                         AS verification_status,
       EXISTS (SELECT 1 FROM timeline_events s WHERE s.supersedes_event_id = t.id) AS is_superseded
FROM timeline_events t
LEFT JOIN LATERAL (SELECT e.status FROM document_extractions e
                   WHERE e.document_id = t.document_id ORDER BY e.version DESC LIMIT 1) x ON TRUE;

-- What a doctor may see for a patient, and WHY (the legal basis is returned with every row).
-- Rule: records created at the doctor's own facility are visible (care relationship);
--       everything else needs an active, unrevoked consent grant whose scope covers the category.
CREATE FUNCTION doctor_visible_timeline(p_doctor_id INT, p_patient_id INT)
RETURNS TABLE (event_id BIGINT, event_type TEXT, category TEXT, occurred_at TIMESTAMP, title TEXT, summary TEXT,
               source_name TEXT, origin TEXT, verification_status TEXT, source_table TEXT, source_id BIGINT,
               document_id INT, access_basis TEXT)
LANGUAGE sql STABLE AS $$
    SELECT v.id, v.event_type, v.category, v.occurred_at, v.title, v.summary, v.source_name, v.origin,
           v.verification_status, v.source_table, v.source_id, v.document_id,
           CASE WHEN v.origin = 'facility_record' AND v.facility_id = d.facility_id THEN 'own_facility_record'
                ELSE 'consent_grant:' || g.id END
    FROM v_timeline v
    JOIN doctors d ON d.id = p_doctor_id AND d.is_active
    LEFT JOIN LATERAL (
        SELECT cg.id FROM consent_grants cg
        WHERE cg.doctor_id = d.id AND cg.patient_id = v.patient_id AND cg.revoked_at IS NULL
          AND now() >= cg.granted_at AND now() < cg.expires_at AND v.category = ANY (cg.scope)
        ORDER BY cg.expires_at DESC LIMIT 1) g ON TRUE
    WHERE v.patient_id = p_patient_id AND NOT v.is_superseded
      AND ((v.origin = 'facility_record' AND v.facility_id = d.facility_id) OR g.id IS NOT NULL)
    ORDER BY v.occurred_at
$$;

-- How many of the patient's records the doctor can NOT see (drives the "records elsewhere" notice).
CREATE FUNCTION hidden_record_count(p_doctor_id INT, p_patient_id INT) RETURNS INT
LANGUAGE sql STABLE AS $$
    SELECT (SELECT COUNT(*) FROM timeline_events WHERE patient_id = p_patient_id)::int
         - (SELECT COUNT(*) FROM doctor_visible_timeline(p_doctor_id, p_patient_id))::int
$$;

-- ---------------------------------------------------------------------
--  MEDICATION SAFETY CHECK  (rule-based and explainable: no AI involved)
--    medication_safety_check(doctor, patient)              -> review the patient's current medicines
--    medication_safety_check(doctor, patient, ARRAY[ids])  -> check medicines the doctor is about to prescribe
--  Uses only records the doctor is allowed to see, plus allergies (always visible: safety-critical).
--  The demo rule set is a small teaching list, NOT a clinical reference.
-- ---------------------------------------------------------------------
CREATE FUNCTION medication_safety_check(p_doctor_id INT, p_patient_id INT, p_new_medication_ids INT[] DEFAULT '{}')
RETURNS TABLE (severity TEXT, check_type TEXT, medication TEXT, conflicts_with TEXT, message TEXT, recommendation TEXT, evidence TEXT)
LANGUAGE sql STABLE AS $$
WITH vis AS (SELECT * FROM doctor_visible_timeline(p_doctor_id, p_patient_id)),
rx_active AS (
    SELECT pi.medication_id,
           'Prescribed ' || to_char(p.prescribed_at, 'DD Mon YYYY') || ' at ' || vis.source_name AS evidence
    FROM vis
    JOIN prescriptions p ON vis.source_table = 'prescriptions' AND p.id = vis.source_id
    JOIN prescription_items pi ON pi.prescription_id = p.id
    WHERE p.prescribed_at + pi.duration_days * interval '1 day' >= now()
    UNION ALL
    SELECT (m->>'matched_medication_id')::int,
           'Uploaded prescription from ' || doc.issuer_name || ', ' || to_char(doc.document_date, 'DD Mon YYYY')
           || CASE WHEN vis.verification_status <> 'patient_verified' THEN ' (UNVERIFIED)' ELSE ' (patient-verified)' END
    FROM vis
    JOIN documents doc ON vis.source_table = 'documents' AND doc.id = vis.source_id
    JOIN LATERAL (SELECT extracted_data FROM document_extractions e
                  WHERE e.document_id = doc.id ORDER BY e.version DESC LIMIT 1) x ON TRUE
    CROSS JOIN LATERAL jsonb_array_elements(COALESCE(x.extracted_data->'medications', '[]'::jsonb)) m
    WHERE vis.verification_status IN ('patient_verified', 'pending_review')
      AND m ? 'matched_medication_id'
      AND doc.document_date + COALESCE((m->>'duration_days')::int, 0) * interval '1 day' >= now()
),
active AS (SELECT medication_id, string_agg(DISTINCT evidence, '; ') AS evidence FROM rx_active GROUP BY medication_id),
cand AS (
    SELECT DISTINCT unnest(CASE WHEN COALESCE(cardinality(p_new_medication_ids), 0) > 0 THEN p_new_medication_ids
                                ELSE ARRAY(SELECT medication_id FROM active) END) AS medication_id
),
pool AS (SELECT medication_id FROM cand UNION SELECT medication_id FROM active),
conds AS (
    SELECT DISTINCT ON (split_part(dg.icd_code, '.', 1))
           split_part(dg.icd_code, '.', 1) AS icd_prefix, c.description,
           'Diagnosed ' || to_char(dg.diagnosed_at, 'DD Mon YYYY') || ' at ' || vis.source_name AS evidence
    FROM vis
    JOIN diagnoses dg ON vis.source_table = 'diagnoses' AND dg.id = vis.source_id
    JOIN icd10_codes c ON c.code = dg.icd_code
    WHERE c.is_chronic OR dg.diagnosed_at >= now() - interval '90 days'
       OR (dg.icd_code LIKE 'Z34%' AND dg.diagnosed_at >= now() - interval '280 days')
    ORDER BY split_part(dg.icd_code, '.', 1), dg.diagnosed_at DESC
),
findings AS (
    SELECT di.severity, 'drug_interaction' AS check_type, ma.name AS medication, mb.name AS conflicts_with,
           di.description AS message, di.recommendation,
           NULLIF(concat_ws('; ', aa.evidence, ab.evidence), '') AS evidence
    FROM drug_interactions di
    JOIN pool pa ON pa.medication_id = di.medication_a_id
    JOIN pool pb ON pb.medication_id = di.medication_b_id
    JOIN medications ma ON ma.id = di.medication_a_id
    JOIN medications mb ON mb.id = di.medication_b_id
    LEFT JOIN active aa ON aa.medication_id = di.medication_a_id
    LEFT JOIN active ab ON ab.medication_id = di.medication_b_id
    WHERE di.medication_a_id IN (SELECT medication_id FROM cand) OR di.medication_b_id IN (SELECT medication_id FROM cand)
    UNION ALL
    SELECT dc.severity, 'condition_caution', m.name, cd.description || ' (' || cd.icd_prefix || ')',
           dc.description, dc.recommendation, cd.evidence
    FROM drug_condition_cautions dc
    JOIN cand ON cand.medication_id = dc.medication_id
    JOIN conds cd ON cd.icd_prefix = dc.icd_prefix
    JOIN medications m ON m.id = dc.medication_id
    UNION ALL
    SELECT CASE WHEN a.severity = 'severe' THEN 'contraindicated' ELSE 'major' END, 'allergy', m.name, a.allergen || ' allergy',
           'Patient has a recorded ' || a.allergen || ' allergy (' || COALESCE(a.reaction, 'reaction not recorded') || ').',
           'Do not prescribe; choose a medicine from a different class.',
           'Allergy ' || replace(a.source, '_', ' ') || ', ' || to_char(a.recorded_at, 'DD Mon YYYY')
    FROM cand
    JOIN medications m ON m.id = cand.medication_id
    JOIN patient_allergies a ON a.patient_id = p_patient_id AND a.allergen_class = ANY (m.drug_classes)
    UNION ALL
    SELECT 'minor', 'duplicate_therapy', m.name, m.name, 'Patient already has an active prescription for this medicine.',
           'Adjust the existing prescription instead of adding a duplicate.', ac.evidence
    FROM cand JOIN active ac ON ac.medication_id = cand.medication_id JOIN medications m ON m.id = cand.medication_id
    WHERE COALESCE(cardinality(p_new_medication_ids), 0) > 0
    UNION ALL
    SELECT 'info', 'coverage', NULL, NULL,
           h.n || ' record(s) for this patient are held elsewhere and not shared with you. This check only covers records you can see.',
           'Ask the patient for consent to include them.', NULL
    FROM (SELECT hidden_record_count(p_doctor_id, p_patient_id) AS n) h WHERE h.n > 0
)
SELECT * FROM findings
ORDER BY CASE severity WHEN 'contraindicated' THEN 1 WHEN 'major' THEN 2 WHEN 'moderate' THEN 3 WHEN 'minor' THEN 4 ELSE 5 END,
         check_type, medication
$$;

-- ---------------------------------------------------------------------
--  CONSENT  (every action writes to audit_log)
-- ---------------------------------------------------------------------
CREATE FUNCTION request_consent(p_doctor_id INT, p_patient_id INT, p_scope TEXT[], p_purpose TEXT, p_hours INT,
                                p_message TEXT DEFAULT NULL) RETURNS INT
LANGUAGE plpgsql AS $$
DECLARE rid INT; fac INT;
BEGIN
    SELECT facility_id INTO fac FROM doctors WHERE id = p_doctor_id AND is_active;
    IF fac IS NULL THEN RAISE EXCEPTION 'Doctor % not found or inactive', p_doctor_id; END IF;
    INSERT INTO consent_requests (patient_id, doctor_id, facility_id, purpose, requested_scope, requested_hours, message, status, requested_at)
    VALUES (p_patient_id, p_doctor_id, fac, p_purpose, p_scope, p_hours, p_message, 'pending', now()) RETURNING id INTO rid;
    INSERT INTO audit_log (user_id, action, table_name, record_id, patient_id, occurred_at, details)
    SELECT u.id, 'CONSENT_REQUEST', 'consent_requests', rid, p_patient_id, now(),
           'Scope: ' || array_to_string(p_scope, ', ') || '; ' || p_hours || 'h'
    FROM users u WHERE u.doctor_id = p_doctor_id;
    RETURN rid;
END $$;

-- The patient may approve all or part of the requested scope, for the same or a shorter time.
CREATE FUNCTION approve_consent(p_request_id INT, p_scope TEXT[] DEFAULT NULL, p_hours INT DEFAULT NULL) RETURNS INT
LANGUAGE plpgsql AS $$
DECLARE r consent_requests%ROWTYPE; gid INT; sc TEXT[]; hrs INT;
BEGIN
    SELECT * INTO r FROM consent_requests WHERE id = p_request_id FOR UPDATE;
    IF r.id IS NULL OR r.status <> 'pending' THEN RAISE EXCEPTION 'Request % is not pending', p_request_id; END IF;
    sc  := COALESCE(p_scope, r.requested_scope);
    hrs := LEAST(COALESCE(p_hours, r.requested_hours), r.requested_hours);
    IF NOT sc <@ r.requested_scope THEN RAISE EXCEPTION 'Granted scope must be within the requested scope'; END IF;
    UPDATE consent_requests SET status = 'approved', responded_at = now() WHERE id = p_request_id;
    INSERT INTO consent_grants (request_id, patient_id, doctor_id, grant_type, scope, granted_at, expires_at)
    VALUES (r.id, r.patient_id, r.doctor_id, 'patient_granted', sc, now(), now() + hrs * interval '1 hour') RETURNING id INTO gid;
    INSERT INTO audit_log (user_id, action, table_name, record_id, patient_id, consent_grant_id, occurred_at, details)
    SELECT u.id, 'CONSENT_GRANT', 'consent_grants', gid, r.patient_id, gid, now(),
           'Granted ' || array_to_string(sc, ', ') || ' for ' || hrs || 'h'
    FROM users u WHERE u.patient_id = r.patient_id;
    RETURN gid;
END $$;

CREATE FUNCTION deny_consent(p_request_id INT) RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE pid INT;
BEGIN
    UPDATE consent_requests SET status = 'denied', responded_at = now()
    WHERE id = p_request_id AND status = 'pending' RETURNING patient_id INTO pid;
    IF pid IS NULL THEN RAISE EXCEPTION 'Request % is not pending', p_request_id; END IF;
    INSERT INTO audit_log (user_id, action, table_name, record_id, patient_id, occurred_at)
    SELECT u.id, 'CONSENT_DENY', 'consent_requests', p_request_id, pid, now() FROM users u WHERE u.patient_id = pid;
END $$;

CREATE FUNCTION revoke_consent(p_grant_id INT, p_reason TEXT DEFAULT NULL) RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE pid INT; uid INT;
BEGIN
    SELECT g.patient_id, u.id INTO pid, uid FROM consent_grants g LEFT JOIN users u ON u.patient_id = g.patient_id
    WHERE g.id = p_grant_id AND g.revoked_at IS NULL AND g.expires_at > now();
    IF pid IS NULL THEN RAISE EXCEPTION 'Grant % is not active', p_grant_id; END IF;
    UPDATE consent_grants SET revoked_at = now(), revoked_by_user_id = uid, revoke_reason = p_reason WHERE id = p_grant_id;
    INSERT INTO audit_log (user_id, action, table_name, record_id, patient_id, consent_grant_id, occurred_at, details)
    VALUES (uid, 'CONSENT_REVOKE', 'consent_grants', p_grant_id, pid, p_grant_id, now(), p_reason);
END $$;

-- Call this whenever a doctor opens a patient's records: logs the access with its legal basis.
CREATE FUNCTION log_record_access(p_doctor_id INT, p_patient_id INT, p_details TEXT DEFAULT 'Viewed patient timeline') RETURNS VOID
LANGUAGE sql AS $$
    INSERT INTO audit_log (user_id, action, table_name, patient_id, consent_grant_id, occurred_at, details)
    SELECT u.id, 'VIEW', 'timeline_events', p_patient_id,
           (SELECT cg.id FROM consent_grants cg
             WHERE cg.doctor_id = p_doctor_id AND cg.patient_id = p_patient_id AND cg.revoked_at IS NULL
               AND now() BETWEEN cg.granted_at AND cg.expires_at ORDER BY cg.expires_at DESC LIMIT 1),
           now(), p_details
    FROM users u WHERE u.doctor_id = p_doctor_id
$$;

CREATE VIEW v_active_consents AS
SELECT g.id AS grant_id, g.grant_type, p.patient_code, p.first_name || ' ' || p.last_name AS patient_name,
       'Dr. ' || d.first_name || ' ' || d.last_name AS doctor, f.name AS doctor_facility, g.scope,
       g.granted_at, g.expires_at, round(EXTRACT(EPOCH FROM g.expires_at - now()) / 3600, 1) AS hours_left
FROM consent_grants g
JOIN patients p ON p.id = g.patient_id
JOIN doctors d ON d.id = g.doctor_id
JOIN facilities f ON f.id = d.facility_id
WHERE g.revoked_at IS NULL AND now() BETWEEN g.granted_at AND g.expires_at;

-- ---------------------------------------------------------------------
--  DOCUMENTS
-- ---------------------------------------------------------------------
CREATE VIEW v_pending_extractions AS
SELECT doc.id AS document_id, doc.document_code, p.patient_code, doc.document_type, doc.issuer_name, doc.uploaded_at,
       e.version, e.confidence, e.low_confidence_fields, e.extracted_data
FROM documents doc
JOIN patients p ON p.id = doc.patient_id
JOIN LATERAL (SELECT * FROM document_extractions x WHERE x.document_id = doc.id ORDER BY x.version DESC LIMIT 1) e ON TRUE
WHERE e.status = 'pending_review';

-- ---------------------------------------------------------------------
--  HOSPITAL CAPACITY  (always shown with its timestamp; indicative until confirmed)
-- ---------------------------------------------------------------------
CREATE VIEW v_latest_bed_availability AS
SELECT DISTINCT ON (r.facility_id, r.ward_type)
       r.facility_id, f.code AS facility_code, f.name AS facility_name, r.ward_type, r.total_beds, r.available_beds,
       r.reported_at, r.source, (r.source = 'hospital_confirmed') AS confirmed,
       GREATEST(0, floor(EXTRACT(EPOCH FROM now() - r.reported_at) / 60))::int AS minutes_since_update,
       CASE WHEN now() - r.reported_at <= interval '2 hours'  THEN 'fresh'
            WHEN now() - r.reported_at <= interval '12 hours' THEN 'aging'
            ELSE 'stale' END AS freshness
FROM bed_availability_reports r
JOIN facilities f ON f.id = r.facility_id
ORDER BY r.facility_id, r.ward_type, r.reported_at DESC;

CREATE VIEW v_facility_directory AS
SELECT f.id, f.code, f.name, f.facility_type, f.ownership, f.locality, f.city, f.pincode, f.latitude, f.longitude,
       f.phone, f.emergency_24x7,
       (SELECT array_agg(DISTINCT dep.name) FROM doctors d JOIN departments dep ON dep.id = d.department_id
         WHERE d.facility_id = f.id AND d.is_active)                                                   AS departments,
       (SELECT array_agg(s.service ORDER BY s.service) FROM facility_services s
         WHERE s.facility_id = f.id AND s.is_available)                                                AS services_available,
       (SELECT jsonb_agg(jsonb_build_object('service', s.service, 'note', s.note, 'updated_at', s.updated_at))
          FROM facility_services s WHERE s.facility_id = f.id AND NOT s.is_available)                  AS services_unavailable,
       (SELECT jsonb_agg(jsonb_build_object('ward_type', b.ward_type, 'available', b.available_beds, 'total', b.total_beds,
                                            'reported_at', b.reported_at, 'freshness', b.freshness, 'confirmed', b.confirmed)
                         ORDER BY b.ward_type)
          FROM v_latest_bed_availability b WHERE b.facility_id = f.id)                                  AS bed_availability,
       f.is_synthetic
FROM facilities f
WHERE f.is_participating;

-- Facilities near a point, optionally needing a ward type (e.g. 'icu') or a service (e.g. 'Dialysis').
CREATE FUNCTION search_facilities(p_lat NUMERIC, p_lon NUMERIC, p_ward_type TEXT DEFAULT NULL,
                                  p_service TEXT DEFAULT NULL, p_radius_km NUMERIC DEFAULT 50)
RETURNS TABLE (facility_code TEXT, facility_name TEXT, city TEXT, distance_km NUMERIC, emergency_24x7 BOOLEAN,
               ward_type TEXT, available_beds INT, total_beds INT, reported_at TIMESTAMP, minutes_since_update INT,
               freshness TEXT, confirmed BOOLEAN, services TEXT[])
LANGUAGE sql STABLE AS $$
    SELECT f.code, f.name, f.city, round(dist.km, 1), f.emergency_24x7,
           b.ward_type, b.available_beds, b.total_beds, b.reported_at, b.minutes_since_update, b.freshness, b.confirmed, s.svc
    FROM facilities f
    CROSS JOIN LATERAL (SELECT (6371 * 2 * asin(sqrt(
            power(sin(radians(f.latitude - p_lat) / 2), 2) +
            cos(radians(p_lat)) * cos(radians(f.latitude)) * power(sin(radians(f.longitude - p_lon) / 2), 2))))::numeric AS km) dist
    CROSS JOIN LATERAL (SELECT array_agg(fs.service ORDER BY fs.service) AS svc FROM facility_services fs
                        WHERE fs.facility_id = f.id AND fs.is_available) s
    LEFT JOIN v_latest_bed_availability b ON b.facility_id = f.id AND (p_ward_type IS NULL OR b.ward_type = p_ward_type)
    WHERE f.is_participating
      AND dist.km <= p_radius_km
      AND (p_service IS NULL OR p_service = ANY (s.svc))
      AND (p_ward_type IS NULL OR b.facility_id IS NOT NULL)
    ORDER BY dist.km, b.ward_type
$$;

-- ---------------------------------------------------------------------
--  HOSPITAL OPERATIONS & FINANCE (per facility)
-- ---------------------------------------------------------------------
CREATE VIEW v_current_bed_occupancy AS
SELECT f.code AS facility_code, f.name AS facility, w.name AS ward, w.ward_type,
       COUNT(b.id) AS total_beds, COUNT(a.id) AS occupied_beds, COUNT(b.id) - COUNT(a.id) AS free_beds,
       ROUND(100.0 * COUNT(a.id) / NULLIF(COUNT(b.id), 0), 1) AS occupancy_pct
FROM wards w
JOIN facilities f ON f.id = w.facility_id
JOIN beds b ON b.ward_id = w.id
LEFT JOIN admissions a ON a.bed_id = b.id AND a.status = 'admitted'
GROUP BY f.id, f.code, f.name, w.id, w.name, w.ward_type
ORDER BY f.id, w.id;

CREATE VIEW v_monthly_revenue AS
WITH paid AS (SELECT invoice_id, SUM(amount) AS amt FROM payments GROUP BY invoice_id)
SELECT f.code AS facility_code, date_trunc('month', i.issued_at)::date AS month,
       COUNT(*) FILTER (WHERE i.invoice_type = 'opd') AS opd_invoices,
       COUNT(*) FILTER (WHERE i.invoice_type = 'ipd') AS ipd_invoices,
       SUM(i.total_amount) AS billed, SUM(COALESCE(p.amt, 0)) AS collected,
       SUM(i.total_amount - COALESCE(p.amt, 0)) AS outstanding
FROM invoices i JOIN facilities f ON f.id = i.facility_id LEFT JOIN paid p ON p.invoice_id = i.id
GROUP BY f.code, 2 ORDER BY 1, 2;

CREATE VIEW v_abnormal_lab_results AS
SELECT r.id AS result_id, f.code AS facility_code, p.patient_code, p.first_name || ' ' || p.last_name AS patient_name,
       t.name AS test, r.result_value, t.unit, t.normal_min, t.normal_max, r.flag, r.resulted_at,
       (o.admission_id IS NOT NULL) AS is_inpatient
FROM lab_results r
JOIN lab_orders o ON o.id = r.lab_order_id
JOIN facilities f ON f.id = o.facility_id
JOIN patients p ON p.id = o.patient_id
JOIN lab_tests t ON t.id = r.lab_test_id
WHERE r.flag <> 'normal'
ORDER BY r.resulted_at DESC;

CREATE VIEW v_doctor_workload AS
SELECT d.id AS doctor_id, 'Dr. ' || d.first_name || ' ' || d.last_name AS doctor, f.code AS facility_code,
       dep.name AS department, d.is_active,
       (SELECT COUNT(*) FROM appointments a WHERE a.doctor_id = d.id AND a.status = 'completed'
          AND a.scheduled_at >= now() - interval '30 days')                                  AS completed_last_30d,
       (SELECT COUNT(*) FROM appointments a WHERE a.doctor_id = d.id AND a.status = 'scheduled'
          AND a.scheduled_at >= now())                                                       AS upcoming_appointments,
       (SELECT COUNT(*) FROM admissions ad WHERE ad.attending_doctor_id = d.id AND ad.status = 'admitted') AS current_inpatients
FROM doctors d JOIN departments dep ON dep.id = d.department_id JOIN facilities f ON f.id = d.facility_id
ORDER BY f.code, dep.name, doctor;

CREATE VIEW v_patient_summary AS
SELECT p.id AS patient_id, p.patient_code, p.first_name || ' ' || p.last_name AS patient_name,
       date_part('year', age(p.date_of_birth))::int AS age, p.gender, p.blood_group, p.city,
       (SELECT COUNT(DISTINCT t.facility_id) FROM timeline_events t WHERE t.patient_id = p.id AND t.facility_id IS NOT NULL) AS facilities_visited,
       (SELECT COUNT(*) FROM appointments a WHERE a.patient_id = p.id AND a.status = 'completed') AS completed_visits,
       (SELECT COUNT(*) FROM admissions ad WHERE ad.patient_id = p.id) AS total_admissions,
       EXISTS (SELECT 1 FROM admissions ad WHERE ad.patient_id = p.id AND ad.status = 'admitted') AS currently_admitted,
       (SELECT COUNT(*) FROM documents d WHERE d.patient_id = p.id) AS uploaded_documents,
       (SELECT string_agg(DISTINCT dg.icd_code, ', ') FROM diagnoses dg JOIN icd10_codes c ON c.code = dg.icd_code
         WHERE dg.patient_id = p.id AND c.is_chronic) AS chronic_conditions,
       (SELECT string_agg(a.allergen, ', ') FROM patient_allergies a WHERE a.patient_id = p.id) AS allergies,
       (SELECT MAX(t.occurred_at) FROM timeline_events t WHERE t.patient_id = p.id) AS last_event
FROM patients p;

CREATE VIEW v_pharmacy_alerts AS
SELECT f.code AS facility_code, m.name AS medication, pi.batch_number, pi.quantity_on_hand, pi.reorder_level, pi.expiry_date,
       CASE WHEN pi.expiry_date < CURRENT_DATE           THEN 'expired'
            WHEN pi.expiry_date < CURRENT_DATE + 30      THEN 'expiring_soon'
            WHEN pi.quantity_on_hand <= pi.reorder_level THEN 'low_stock' END AS alert
FROM pharmacy_inventory pi
JOIN medications m ON m.id = pi.medication_id
JOIN facilities f ON f.id = pi.facility_id
WHERE pi.expiry_date < CURRENT_DATE + 30 OR pi.quantity_on_hand <= pi.reorder_level
ORDER BY pi.expiry_date;
