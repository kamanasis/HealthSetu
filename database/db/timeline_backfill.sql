-- =====================================================================
--  Builds the append-only patient timeline from facility records and uploaded documents.
--  Every event links back to its source row (source_table, source_id) and names its source.
--  In the app, new events are inserted the same way as each record is created.
-- =====================================================================
INSERT INTO timeline_events (patient_id, event_type, category, occurred_at, title, summary, facility_id,
                             source_name, origin, source_table, source_id, document_id, created_at)
SELECT patient_id, event_type, category, occurred_at, title, summary, facility_id, source_name, origin,
       source_table, source_id, document_id, occurred_at + interval '5 minutes'
FROM (
    -- OPD visits
    SELECT a.patient_id, 'opd_visit' AS event_type, 'encounters' AS category, a.scheduled_at AS occurred_at,
           'OPD visit - ' || dep.name AS title,
           'Seen by Dr. ' || d.first_name || ' ' || d.last_name || '. ' || COALESCE(a.reason, '') AS summary,
           a.facility_id, f.name AS source_name, 'facility_record' AS origin, 'appointments' AS source_table,
           a.id::bigint AS source_id, NULL::int AS document_id
    FROM appointments a
    JOIN doctors d ON d.id = a.doctor_id
    JOIN departments dep ON dep.id = d.department_id
    JOIN facilities f ON f.id = a.facility_id
    WHERE a.status = 'completed'

    UNION ALL  -- admissions
    SELECT ad.patient_id, 'admission', 'encounters', ad.admitted_at,
           'Admitted - ' || w.name,
           initcap(ad.admission_type) || ' admission: ' || ad.reason || '. Attending: Dr. ' || d.first_name || ' ' || d.last_name,
           ad.facility_id, f.name, 'facility_record', 'admissions', ad.id, NULL
    FROM admissions ad
    JOIN beds b ON b.id = ad.bed_id JOIN wards w ON w.id = b.ward_id
    JOIN doctors d ON d.id = ad.attending_doctor_id
    JOIN facilities f ON f.id = ad.facility_id

    UNION ALL  -- discharges
    SELECT ad.patient_id, 'discharge', 'encounters', ad.discharged_at,
           'Discharged (' || ad.discharge_disposition || ')', ad.discharge_summary,
           ad.facility_id, f.name, 'facility_record', 'admissions', ad.id, NULL
    FROM admissions ad JOIN facilities f ON f.id = ad.facility_id
    WHERE ad.discharged_at IS NOT NULL

    UNION ALL  -- diagnoses
    SELECT dg.patient_id, 'diagnosis', 'diagnoses', dg.diagnosed_at,
           c.description || ' (' || dg.icd_code || ')',
           initcap(dg.diagnosis_type) || ', ' || dg.severity || COALESCE('. ' || dg.notes, ''),
           COALESCE(a.facility_id, ad.facility_id), f.name, 'facility_record', 'diagnoses', dg.id, NULL
    FROM diagnoses dg
    JOIN icd10_codes c ON c.code = dg.icd_code
    LEFT JOIN appointments a ON a.id = dg.appointment_id
    LEFT JOIN admissions ad ON ad.id = dg.admission_id
    JOIN facilities f ON f.id = COALESCE(a.facility_id, ad.facility_id)

    UNION ALL  -- prescriptions
    SELECT p.patient_id, 'prescription', 'prescriptions', p.prescribed_at,
           'Prescription: ' || string_agg(m.name, ', ' ORDER BY pi.id),
           string_agg(m.name || ' - ' || pi.frequency || ' x ' || pi.duration_days || ' days', '; ' ORDER BY pi.id)
             || '. By Dr. ' || d.first_name || ' ' || d.last_name || COALESCE('. Note: ' || p.notes, ''),
           p.facility_id, f.name, 'facility_record', 'prescriptions', p.id, NULL
    FROM prescriptions p
    JOIN prescription_items pi ON pi.prescription_id = p.id
    JOIN medications m ON m.id = pi.medication_id
    JOIN doctors d ON d.id = p.doctor_id
    JOIN facilities f ON f.id = p.facility_id
    GROUP BY p.id, d.first_name, d.last_name, f.name

    UNION ALL  -- lab reports (one event per completed order)
    SELECT o.patient_id, 'lab_result', 'lab_results', MAX(r.resulted_at),
           'Lab report: ' || string_agg(t.code, ', ' ORDER BY t.id),
           string_agg(t.name || ' ' || rtrim(to_char(r.result_value, 'FM999990.999'), '.') || ' ' || COALESCE(t.unit, '')
                      || CASE WHEN r.flag <> 'normal' THEN ' (' || upper(r.flag) || ')' ELSE '' END, '; ' ORDER BY t.id),
           o.facility_id, f.name, 'facility_record', 'lab_orders', o.id, NULL
    FROM lab_orders o
    JOIN lab_results r ON r.lab_order_id = o.id
    JOIN lab_tests t ON t.id = r.lab_test_id
    JOIN facilities f ON f.id = o.facility_id
    WHERE o.status = 'completed'
    GROUP BY o.id, f.name

    UNION ALL  -- patient-uploaded documents
    SELECT doc.patient_id, 'document', 'documents', doc.document_date::timestamp + interval '12 hours',
           'Uploaded ' || replace(doc.document_type, '_', ' ') || ' - ' || doc.issuer_name,
           CASE doc.document_type
             WHEN 'prescription' THEN (SELECT 'Medicines: ' || string_agg(m->>'name' || ' (' || (m->>'frequency') || ' x '
                                              || (m->>'duration_days') || ' days)', '; ')
                                       FROM jsonb_array_elements(x.extracted_data->'medications') m)
             WHEN 'lab_report' THEN (SELECT 'Results: ' || string_agg((t->>'name') || ' ' || (t->>'value') || ' ' || (t->>'unit')
                                            || CASE WHEN t->>'flag' <> 'normal' THEN ' (' || upper(t->>'flag') || ')' ELSE '' END, '; ')
                                     FROM jsonb_array_elements(x.extracted_data->'tests') t)
           END,
           doc.issuing_facility_id, doc.issuer_name, 'patient_upload', 'documents', doc.id, doc.id
    FROM documents doc
    JOIN LATERAL (SELECT extracted_data FROM document_extractions e
                  WHERE e.document_id = doc.id ORDER BY e.version DESC LIMIT 1) x ON TRUE
) ev
ORDER BY occurred_at;
