-- =====================================================================
--  Demo queries — copy any of these into Adminer / psql / your API.
-- =====================================================================

-- =====================================================================
--  HEALTH SETU DEMO SCRIPT  (run top to bottom in psql; the \gset lines store ids)
--  Tip: wrap in BEGIN; ... ROLLBACK; to rehearse without changing the data.
-- =====================================================================
SELECT id AS meera FROM doctors WHERE first_name = 'Meera' AND last_name = 'Banerjee' \gset
SELECT id AS subrata FROM patients WHERE patient_code = 'PT-000001' \gset

-- H1. Doctor opens the patient: only her own hospital's records are visible
SELECT access_basis, COUNT(*) FROM doctor_visible_timeline(:meera, :subrata) GROUP BY 1;
SELECT hidden_record_count(:meera, :subrata) AS records_held_elsewhere;

-- H2. Safety check before consent: only a coverage warning, the CKD diagnosis is invisible
SELECT * FROM medication_safety_check(:meera, :subrata);

-- H3. Doctor requests access; patient approves (the patient may narrow scope or shorten time)
SELECT request_consent(:meera, :subrata, ARRAY['encounters','diagnoses','prescriptions','lab_results','documents'],
                       'consultation', 72, 'Diabetes review') AS req \gset
SELECT * FROM consent_requests WHERE id = :req;
SELECT approve_consent(:req) AS grant_id \gset

-- H4. Now the whole history is visible, each row with its legal basis
SELECT occurred_at::date, title, source_name, verification_status, access_basis
FROM doctor_visible_timeline(:meera, :subrata);
SELECT log_record_access(:meera, :subrata);

-- H5. The safety check now sees the CKD diagnosis from another hospital
SELECT severity, check_type, medication, conflicts_with, recommendation, evidence FROM medication_safety_check(:meera, :subrata);

-- H6. Checking a new prescription before saving it (e.g. diclofenac for knee pain)
SELECT severity, check_type, medication, conflicts_with, evidence
FROM medication_safety_check(:meera, :subrata, ARRAY[(SELECT id FROM medications WHERE name LIKE 'Diclofenac%')]);

-- H7. Bed availability near Howrah station, with freshness labels
SELECT * FROM search_facilities(22.5838, 88.3426, 'icu', NULL, 25);
SELECT code, name, services_unavailable, bed_availability FROM v_facility_directory WHERE code = 'SHH';  -- stale on purpose

-- H8. Patient revokes access: visibility disappears, the audit trail stays
SELECT revoke_consent(:grant_id, 'Consultation done');
SELECT COUNT(*) AS still_visible FROM doctor_visible_timeline(:meera, :subrata);
SELECT occurred_at, action, details FROM audit_log WHERE patient_id = :subrata ORDER BY occurred_at DESC, id DESC LIMIT 10;

-- H9. Second hero: pregnant patient still on an outside BP prescription (her OB has an active grant)
SELECT severity, check_type, medication, conflicts_with, evidence
FROM medication_safety_check((SELECT id FROM doctors WHERE first_name = 'Tanushree'), 2);

-- H10. Uploads waiting for the patient to verify the AI extraction
SELECT document_code, patient_code, document_type, confidence, low_confidence_fields FROM v_pending_extractions;

-- H11. Who accessed a patient's data, and on what basis (patient-facing access log)
SELECT a.occurred_at, u.username, a.action, a.consent_grant_id, a.details
FROM audit_log a LEFT JOIN users u ON u.id = a.user_id WHERE a.patient_id = 2 ORDER BY a.occurred_at DESC, a.id DESC;

-- H12. Emergency (break-glass) accesses, for compliance review
SELECT g.id, g.granted_at, 'Dr. ' || d.last_name AS doctor, p.patient_code, g.justification
FROM consent_grants g JOIN doctors d ON d.id = g.doctor_id JOIN patients p ON p.id = g.patient_id
WHERE g.grant_type = 'emergency_override' ORDER BY g.granted_at DESC;

-- ---------------- CLINICAL ----------------

-- 1. Full source-linked timeline for one patient, with verification labels
SELECT occurred_at, event_type, title, source_name, verification_status
FROM v_timeline WHERE patient_id = 1 ORDER BY occurred_at;

-- 2. Current inpatients whose latest SpO2 is below 92% (early-warning list)
SELECT * FROM (
    SELECT DISTINCT ON (ad.id) p.patient_code, p.first_name || ' ' || p.last_name AS patient, w.name AS ward,
           v.recorded_at, v.spo2_percent, v.pulse_bpm, v.temperature_c
    FROM admissions ad
    JOIN patients p ON p.id = ad.patient_id
    JOIN beds b ON b.id = ad.bed_id JOIN wards w ON w.id = b.ward_id
    JOIN vitals v ON v.admission_id = ad.id
    WHERE ad.status = 'admitted'
    ORDER BY ad.id, v.recorded_at DESC
) latest
WHERE spo2_percent < 92;

-- 3. Top 10 diagnoses in the last 30 days
SELECT dg.icd_code, c.description, COUNT(*) AS cases
FROM diagnoses dg JOIN icd10_codes c ON c.code = dg.icd_code
WHERE dg.diagnosed_at >= now() - interval '30 days' AND dg.diagnosis_type = 'primary'
GROUP BY 1, 2 ORDER BY cases DESC LIMIT 10;

-- 4. 30-day readmissions (a classic hospital quality metric)
SELECT p.patient_code, a1.discharged_at AS first_discharge, a2.admitted_at AS readmitted_at,
       a2.admitted_at - a1.discharged_at AS gap
FROM admissions a1
JOIN admissions a2 ON a2.patient_id = a1.patient_id AND a2.admitted_at > a1.discharged_at
                  AND a2.admitted_at <= a1.discharged_at + interval '30 days'
JOIN patients p ON p.id = a1.patient_id
ORDER BY gap;

-- 5. Average length of stay per ward
SELECT w.name AS ward, COUNT(*) AS discharges,
       ROUND(AVG(EXTRACT(EPOCH FROM ad.discharged_at - ad.admitted_at) / 86400)::numeric, 1) AS avg_days
FROM admissions ad JOIN beds b ON b.id = ad.bed_id JOIN wards w ON w.id = b.ward_id
WHERE ad.status = 'discharged'
GROUP BY w.name ORDER BY avg_days DESC;

-- ---------------- OPERATIONS & FINANCE ----------------

-- 6. Revenue per department (last 90 days)
SELECT dep.name AS department, SUM(ii.amount) AS revenue
FROM invoice_items ii
JOIN invoices i ON i.id = ii.invoice_id
LEFT JOIN appointments a ON a.id = i.appointment_id
LEFT JOIN admissions ad ON ad.id = i.admission_id
JOIN doctors d ON d.id = COALESCE(a.doctor_id, ad.attending_doctor_id)
JOIN departments dep ON dep.id = d.department_id
WHERE i.issued_at >= now() - interval '90 days'
GROUP BY dep.name ORDER BY revenue DESC;

-- 7. Insurance claim outcomes per insurer
SELECT ip.name AS insurer, COUNT(*) AS claims,
       ROUND(100.0 * AVG((c.status = 'rejected')::int), 1) AS rejection_pct,
       SUM(c.claimed_amount) AS claimed, SUM(c.approved_amount) AS approved
FROM insurance_claims c
JOIN patient_insurance pi ON pi.id = c.patient_insurance_id
JOIN insurance_providers ip ON ip.id = pi.provider_id
GROUP BY ip.name ORDER BY claims DESC;

-- 8. No-show rate per doctor
SELECT 'Dr. ' || d.first_name || ' ' || d.last_name AS doctor,
       ROUND(100.0 * AVG((a.status = 'no_show')::int), 1) AS no_show_pct, COUNT(*) AS appointments
FROM appointments a JOIN doctors d ON d.id = a.doctor_id
WHERE a.scheduled_at < now()
GROUP BY doctor ORDER BY no_show_pct DESC;

-- ---------------- SECURITY (audit log) ----------------

-- 9. Brute-force detection: many failed logins from one IP within 10 minutes
SELECT host(ip_address) AS ip, username_attempted, COUNT(*) AS failures,
       MIN(occurred_at) AS first_try, MAX(occurred_at) AS last_try
FROM audit_log
WHERE action = 'LOGIN_FAILED'
GROUP BY ip_address, username_attempted, date_trunc('hour', occurred_at)
HAVING COUNT(*) >= 10;

-- 10. Staff logins from outside the hospital network (10.0.0.0/8). Patients log in from home, so they are excluded.
SELECT a.occurred_at, u.username, r.name AS role, host(a.ip_address) AS ip, a.details
FROM audit_log a JOIN users u ON u.id = a.user_id JOIN roles r ON r.id = u.role_id
WHERE a.action = 'LOGIN' AND r.name <> 'patient' AND NOT a.ip_address << '10.0.0.0/8'
ORDER BY a.occurred_at DESC;

-- 11. Bulk record access: users who viewed > 50 patient records in one hour
SELECT u.username, date_trunc('hour', a.occurred_at) AS hour, COUNT(*) AS records_viewed
FROM audit_log a JOIN users u ON u.id = a.user_id
WHERE a.action = 'VIEW' AND a.table_name = 'patients'
GROUP BY u.username, hour HAVING COUNT(*) > 50
ORDER BY records_viewed DESC;

-- 12. Access outside a user's role (e.g. receptionists reading lab results)
SELECT u.username, r.name AS role, a.table_name, COUNT(*) AS hits
FROM audit_log a JOIN users u ON u.id = a.user_id JOIN roles r ON r.id = u.role_id
WHERE (r.name = 'receptionist' AND a.table_name IN ('lab_results', 'prescriptions', 'diagnoses'))
   OR (r.name = 'billing'      AND a.table_name IN ('lab_results', 'diagnoses', 'vitals'))
GROUP BY u.username, r.name, a.table_name;

-- 13. Activity by deactivated accounts
SELECT a.occurred_at, u.username, a.action, host(a.ip_address) AS ip, a.details
FROM audit_log a JOIN users u ON u.id = a.user_id
WHERE u.is_active = FALSE AND a.occurred_at >= (SELECT left_on FROM doctors d WHERE d.id = u.doctor_id);
