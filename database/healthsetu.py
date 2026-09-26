"""
healthsetu.py - the Health Setu layer on top of the hospital network data:

  * two scripted "hero" patients whose histories match the demo flow
  * patient-uploaded documents (real PNG files) + versioned AI extractions + patient review
  * consent requests / grants / revocations / emergency overrides, with audit events
  * timestamped bed-availability reports from each hospital (some deliberately stale)

All data is synthetic.
"""
from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, time, timedelta
from pathlib import Path

import docgen
from reference import CONDITION_MEDS, CONSENT_SCOPES, M, prefix

EXTRACTOR = "ocr+llm-extractor v0 (demo)"

# ----------------------------------------------------------------------------- cast
HERO_DOCTORS = [
    dict(key="meera", fac="GVH", dept="GM", first="Meera", last="Banerjee", sex="F", username="dr.meera"),
    dict(key="kaushik", fac="GVH", dept="END", first="Kaushik", last="Dey", sex="M", username="dr.kaushik"),
    dict(key="sourav", fac="EHI", dept="CAR", first="Sourav", last="Chatterjee", sex="M", username="dr.sourav"),
    dict(key="arindam", fac="RSH", dept="NEP", first="Arindam", last="Roy", sex="M", username="dr.arindam"),
    dict(key="tanushree", fac="HJH", dept="OBG", first="Tanushree", last="Pal", sex="F", username="dr.tanushree"),
]
HERO_PATIENTS = [
    dict(key="subrata", first="Subrata", last="Mondal", sex="M", age=58, city="Kolkata", region="KOL", pincode="700039",
         address="14/2 Picnic Garden Road, Tiljala", blood="B+", phone="+91 98301 55120", email="subrata.mondal@example.com",
         ec=("Shampa Mondal", "Spouse", "+91 98301 55121"), abha="subrata.mondal@demo", username="subrata",
         chronic={"E11.9", "I10", "N18.9"}, allergies=[("Penicillin", "penicillin", "Skin rash", "moderate", "patient_reported")]),
    dict(key="rupa", first="Rupa", last="Das", sex="F", age=29, city="Howrah", region="KOL", pincode="711102",
         address="32 Dharmatala Lane, Shibpur", blood="O+", phone="+91 90070 33418", email="rupa.das@example.com",
         ec=("Amit Das", "Spouse", "+91 90070 33419"), abha="rupa.das@demo", username="rupa",
         chronic={"E03.9"}, allergies=[]),
]
OUTSIDE_CLINICS = [("Saha Clinic", "Behala"), ("Mitra Medical Centre", "Shibpur, Howrah"), ("Joint Care Clinic", "Kasba"),
                   ("Sunrise Polyclinic", "Dum Dum"), ("Arogya Family Clinic", "Jadavpur"), ("Nirmal Health Point", "Garia"),
                   ("City Care Clinic", "Shyambazar"), ("Lifeline Chamber", "Tollygunge"), ("Seva Clinic", "Salkia, Howrah"),
                   ("Janata Medical Hall", "Bally")]
OUTSIDE_LABS = ["Suraksha Pathology Point", "Bengal Diagnostic Lab", "CarePlus Path Lab"]


def add_hero_patients(g):
    g.heroes = {}
    for i, h in enumerate(HERO_PATIENTS, 1):
        dob = g.today - timedelta(days=h["age"] * 365 + 97 * i)
        pid = g.add("patients", patient_code=f"PT-{i:06d}", first_name=h["first"], last_name=h["last"], gender=h["sex"],
                    date_of_birth=dob, blood_group=h["blood"], phone=h["phone"], email=h["email"], address=h["address"],
                    city=h["city"], state="West Bengal", pincode=h["pincode"], emergency_contact_name=h["ec"][0],
                    emergency_contact_relation=h["ec"][1], emergency_contact_phone=h["ec"][2], abha_address=h["abha"],
                    registered_at=g.now - timedelta(days=420))
        g.used_emails.add(h["email"])
        g.patients[pid] = dict(age=h["age"], sex=h["sex"], chronic=set(h["chronic"]), busy=[], ins=None, region=h["region"],
                               hero=True, name=f"{h['first']} {h['last']}", code=f"PT-{i:06d}", username=h["username"])
        for allergen, cls, reaction, sev, src in h["allergies"]:
            g.add("patient_allergies", patient_id=pid, allergen=allergen, allergen_class=cls, reaction=reaction, severity=sev,
                  source=src, recorded_at=g.now - timedelta(days=150))
        g.heroes[h["key"]] = pid


# ----------------------------------------------------------------------------- scripted histories
def _visit(g, pid, doc_key, days_ago, at, codes, meds=(), labs=None, rx_note=None):
    doc = g.hero_doc[doc_key]
    info = g.doctors[doc]
    fac = info["fac"]
    when = datetime.combine(g.today - timedelta(days=days_ago), at)
    key = (pid, fac, info["dept"])
    visit_type = "follow_up" if key in g.seen else "new"
    g.seen.add(key)
    desc = g.icd[codes[0][0]]["desc"]
    created = when - timedelta(days=4, hours=3)
    appt = g.add("appointments", facility_id=g.fid(fac), patient_id=pid, doctor_id=doc, scheduled_at=when, status="completed",
                 visit_type=visit_type, reason=desc if visit_type == "new" else f"Follow-up: {desc}", created_at=created)
    g.touch_patient(pid, created)
    seen_at = when + timedelta(minutes=10)
    for i, (code, sev, notes) in enumerate(codes):
        g.add_diagnosis(pid, doc, code, seen_at, appt=appt, severity=sev, dtype="primary" if i == 0 else "secondary", notes=notes)
    items = [("consultation", f"Consultation - Dr. {info['name']}", 1, info["fee"])]
    if meds:
        g.add_rx(pid, doc, seen_at + timedelta(minutes=5), [(M[w], d, f, ins) for w, d, f, ins in meds], appt=appt, notes=rx_note)
    if labs:
        items += [("lab", n, 1, p) for n, p in g.add_lab_order(pid, doc, seen_at + timedelta(minutes=15), labs, appt=appt, done_after_h=6)]
    inv, total = g.add_invoice(pid, fac, "opd", seen_at, items, appt=appt)
    g.pay(inv, seen_at + timedelta(minutes=20), total, "upi")


def build_hero_records(g):
    s, r = g.heroes["subrata"], g.heroes["rupa"]
    # Subrata: diabetes at Ganga View, BP at Eastern Heart, CKD found at Rajarhat - nobody sees the whole picture.
    _visit(g, s, "meera", 150, time(10, 15), [("E11.9", "moderate", "Type 2 DM on oral agents. Diet counselling given.")],
           meds=[("Metformin", 30, None, "after food"), ("Glimepiride", 30, None, "before breakfast")],
           labs={"FBS": 168, "HBA1C": 8.1, "CREAT": 1.21})
    _visit(g, s, "sourav", 120, time(11, 30), [("I10", "moderate", "BP 158/96. Started ARB and statin.")],
           meds=[("Telmisartan", 30, None, None), ("Atorvastatin", 30, None, None)], labs={"CHOL": 232, "NA": 139, "K": 4.6})
    _visit(g, s, "meera", 95, time(10, 0), [("E11.9", "mild", "Sugars improving.")],
           meds=[("Metformin", 90, None, "after food"), ("Glimepiride", 90, None, "before breakfast")], labs={"FBS": 142, "HBA1C": 7.8})
    _visit(g, s, "sourav", 75, time(12, 0), [("I10", "mild", "BP 138/88 on treatment.")],
           meds=[("Telmisartan", 90, None, None), ("Atorvastatin", 90, None, None)])
    _visit(g, s, "arindam", 45, time(16, 30),
           [("N18.9", "moderate", "CKD stage 3a (synthetic eGFR ~48), likely diabetic/hypertensive. AVOID NSAIDs. "
                                  "Metformin dose to be reviewed by the treating physician."),
            ("E11.9", "mild", None), ("I10", "mild", None)],
           meds=[("Furosemide", 60, "1-0-0", "for ankle swelling")], labs={"CREAT": 1.62, "UREA": 52, "K": 5.3, "NA": 137},
           rx_note="Avoid painkillers such as diclofenac or ibuprofen.")
    _visit(g, s, "meera", 20, time(9, 45), [("E11.9", "mild", "HbA1c 7.6%. Continue same treatment.")],
           meds=[("Metformin", 90, None, "after food"), ("Glimepiride", 90, None, "before breakfast")],
           labs={"HBA1C": 7.6, "FBS": 138, "CREAT": 1.58})
    # Rupa: hypothyroid (Ganga View), now pregnant (Howrah Janaseva), still on an outside BP prescription.
    _visit(g, r, "kaushik", 200, time(11, 0), [("E03.9", "mild", "Primary hypothyroidism.")],
           meds=[("Levothyroxine", 365, None, "empty stomach, 30 min before breakfast")], labs={"TSH": 6.8})
    _visit(g, r, "tanushree", 40, time(10, 30), [("Z34.9", "mild", "G1P0, about 11 weeks (synthetic). Known hypothyroid on levothyroxine.")],
           meds=[("Ferrous", 90, None, None), ("Calcium", 90, None, None)], labs={"HB": 10.2, "FBS": 92, "TSH": 4.6})
    _visit(g, r, "tanushree", 12, time(10, 45), [("Z34.9", "mild", "About 15 weeks. Mild anaemia improving.")], labs={"HB": 10.6})


# ----------------------------------------------------------------------------- documents
def _date(d) -> str:
    return d.strftime("%d-%m-%Y")


def _rx_truth(g, pid, issuer, doctor, when, complaints, diagnosis, meds, advice, follow_up, in_network=False):
    p = g.patients[pid]
    return {"schema_version": "1.0", "document_type": "prescription",
            "issuer": {"name": issuer[0], "address": issuer[1], "phone": issuer[2], "in_network": in_network},
            "doctor": {"name": doctor[0], "qualification": doctor[1], "department": doctor[2], "registration_no": doctor[3]},
            "patient": {"name": p["name"], "age": p["age"], "sex": p["sex"]},
            "date": _date(when), "document_date": when.isoformat(), "complaints": complaints, "diagnosis": diagnosis,
            "medications": [{"name": M[w], "frequency": f or g.med[M[w]]["freq"], "duration_days": d, "instructions": ins,
                             "matched_medication_id": g.med[M[w]]["id"]} for w, d, f, ins in meds],
            "advice": advice, "follow_up": follow_up}


def _lab_truth(g, pid, issuer, when, values, referred_by="Self", pathologist="Dr. A. Sengupta, MD (Path)"):
    p = g.patients[pid]
    tests = []
    for code, v in values.items():
        t = g.lab[code]
        tests.append({"code": code, "name": t["name"], "value": v, "unit": t["unit"],
                      "reference_range": f"{t['lo']:g} - {t['hi']:g}", "flag": g.lab_flag(code, v), "matched_lab_test_id": t["id"]})
    return {"schema_version": "1.0", "document_type": "lab_report",
            "issuer": {"name": issuer[0], "address": issuer[1], "phone": issuer[2]},
            "patient": {"name": p["name"], "age": p["age"], "sex": p["sex"]}, "referred_by": referred_by,
            "document_date": when.isoformat(), "collected_at": when.strftime("%d-%m-%Y 08:%M"),
            "reported_at": when.strftime("%d-%m-%Y 17:%M"), "tests": tests, "pathologist": pathologist}


def _store(g, subdir: str, name: str, data: bytes) -> Path:
    path = Path(g.args.storage_dir) / subdir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def add_document(g, pid, truth, uploaded_at, review, issuing_fac=None, low_conf=(), error=None, reject_reason=None):
    """Renders the image, stores it, and records document + extraction version(s) + audit events."""
    n = g._ids["documents"] + 1
    code = f"DOC-{n:06d}"
    p = g.patients[pid]
    render = docgen.render_prescription if truth["document_type"] == "prescription" else docgen.render_lab_report
    png = render(truth, seed=n)
    uri = f"documents/{p['code']}/{code}.png"
    _store(g, "", uri, png)
    _store(g, "ground_truth", f"{code}.json", json.dumps(truth, indent=2, ensure_ascii=False).encode())
    uid = g.user_of_patient[pid]
    doc_date = datetime.fromisoformat(truth["document_date"]).date()
    did = g.add("documents", document_code=code, patient_id=pid, document_type=truth["document_type"], source="patient_upload",
                issuing_facility_id=g.fid(issuing_fac) if issuing_fac else None, issuer_name=truth["issuer"]["name"],
                document_date=doc_date, storage_uri=uri,
                original_filename=f"{'IMG' if random.random() < .6 else 'scan'}_{doc_date:%Y%m%d}_{random.randint(1000, 9999)}.png",
                mime_type="image/png", file_size_bytes=len(png), sha256=hashlib.sha256(png).hexdigest(),
                uploaded_by_user_id=uid, uploaded_at=uploaded_at, is_synthetic=True)
    ip = g.patient_ip(uid)
    g.extra_events.append((uploaded_at, uid, None, "UPLOAD", "documents", did, ip, f"Uploaded {truth['document_type'].replace('_', ' ')}", pid, None))
    machine = json.loads(json.dumps(truth))           # what the AI "read"
    if error:                                         # e.g. ("medications[0].frequency", "0-0-1")
        field, wrong = error
        head, leaf = field.rsplit(".", 1)
        lst, idx = head[:-1].split("[")
        machine[lst][int(idx)][leaf] = wrong
    created = uploaded_at + timedelta(seconds=random.randint(20, 90))
    conf = round(random.uniform(.62, .80) if (low_conf or error) else random.uniform(.86, .98), 3)
    low = list(low_conf) + ([error[0]] if error else [])
    reviewed = created + timedelta(minutes=random.randint(3, 180))
    if reviewed > g.now:
        review = "pending_review"
    if review == "pending_review":
        g.add("document_extractions", document_id=did, version=1, extractor=EXTRACTOR, extracted_data=machine, confidence=conf,
              low_confidence_fields=low, status="pending_review", reviewed_by_user_id=None, reviewed_at=None,
              review_note=None, created_at=created)
        return did
    if review == "corrected":
        g.add("document_extractions", document_id=did, version=1, extractor=EXTRACTOR, extracted_data=machine, confidence=conf,
              low_confidence_fields=low, status="corrected", reviewed_by_user_id=uid, reviewed_at=reviewed,
              review_note=f"Patient corrected {error[0]}: '{error[1]}' -> as printed on the document", created_at=created)
        g.add("document_extractions", document_id=did, version=2, extractor="patient_correction", extracted_data=truth,
              confidence=1.0, low_confidence_fields=[], status="verified", reviewed_by_user_id=uid, reviewed_at=reviewed,
              review_note="Verified after correction", created_at=reviewed)
    else:
        g.add("document_extractions", document_id=did, version=1, extractor=EXTRACTOR, extracted_data=machine, confidence=conf,
              low_confidence_fields=low, status=review, reviewed_by_user_id=uid, reviewed_at=reviewed,
              review_note=reject_reason, created_at=created)
    g.extra_events.append((reviewed, uid, None, "VERIFY", "document_extractions", did, ip,
                           f"Extraction {'rejected' if review == 'rejected' else 'verified'}", pid, None))
    return did


def build_documents(g):
    T = g.today
    s, r = g.heroes["subrata"], g.heroes["rupa"]
    at = lambda d, hh=19, mm=0: datetime.combine(T - timedelta(days=d), time(hh, mm))
    spd = g.fac["SPD"]
    spd_issuer = (spd["name"], f"{spd['locality']}, {spd['city']} {spd['pincode']}", spd["phone"])
    # --- hero documents
    add_document(g, s, _rx_truth(g, s, ("Saha Clinic", "12 Diamond Harbour Road, Behala, Kolkata 700034", "+91 98311 45678"),
                                 ("P. K. Saha", "MBBS", "General Practice", "WBMC-31877"), T - timedelta(days=60),
                                 "Right knee pain x 1 week", ["Knee pain, right"],
                                 [("Diclofenac", 10, None, "after food"), ("Pantoprazole", 10, None, "before breakfast")],
                                 "Rest, avoid stairs", "SOS"),
                 at(58, 21, 5), "verified")
    add_document(g, s, _lab_truth(g, s, spd_issuer, T - timedelta(days=6), {"CREAT": 1.71, "UREA": 58, "HBA1C": 7.4, "K": 5.2}),
                 at(5, 20, 40), "pending_review", issuing_fac="SPD", low_conf=["tests[0].value"])
    add_document(g, r, _rx_truth(g, r, ("Mitra Medical Centre", "8 Kalitala Lane, Shibpur, Howrah 711102", "+91 90380 22110"),
                                 ("R. Mitra", "MBBS, MD (Medicine)", "General Medicine", "WBMC-44102"), T - timedelta(days=70),
                                 "Headache, raised BP on two readings", ["Hypertension"], [("Telmisartan", 90, None, None)],
                                 "Low-salt diet", "After 1 month"),
                 at(45, 22, 10), "corrected", error=("medications[0].frequency", "0-0-1"))
    # --- crowd documents
    candidates = [pid for pid in g.user_of_patient if not g.patients[pid]["hero"]]
    for pid in random.sample(candidates, min(g.args.documents, len(candidates))):
        p = g.patients[pid]
        for _ in range(random.choice([1, 1, 2])):
            when = g.now - timedelta(days=random.randint(3, g.args.history_days))
            uploaded = min(g.now - timedelta(hours=1), when + timedelta(days=random.randint(0, 25), hours=random.randint(8, 13)))
            review = random.choices(["verified", "corrected", "pending_review", "rejected"], [65, 15, 12, 8])[0]
            if random.random() < .65:
                codes = sorted(p["chronic"]) or [c for c in g.icd if not g.icd[c]["chronic"] and c not in {"O80", "O82", "P59.9", "Z34.9"}
                                                  and g.icd[c]["amin"] <= p["age"] <= g.icd[c]["amax"]
                                                  and (g.icd[c]["sex"] in (None, p["sex"]))]
                code = random.choice(codes)
                chronic = g.icd[code]["chronic"]
                words = [w for w in CONDITION_MEDS.get(prefix(code), ["Paracetamol"]) if g.med[M[w]]["form"] not in {"injection", "iv_fluid"}]
                words = words or ["Paracetamol"]
                clinic, area = random.choice(OUTSIDE_CLINICS)
                dfirst, dlast = g.name(random.choice("MF"))
                truth = _rx_truth(g, pid, (clinic, f"{random.randint(1, 180)} Main Road, {area}", g.phone()),
                                  (f"{dfirst[0]}. {dlast}", "MBBS", "General Practice", f"WBMC-{random.randint(20000, 69999)}"),
                                  when, None, [g.icd[code]["desc"]],
                                  [(w, 30 if chronic else random.choice([3, 5, 7]), None, None) for w in words[:3]],
                                  "Plenty of fluids" if not chronic else "Regular exercise, diet control", "After 2 weeks")
                err = ("medications[0].frequency", random.choice(["1-1-1", "0-0-1", "1-0-0"])) if review == "corrected" else None
                if err and err[1] == truth["medications"][0]["frequency"]:
                    err = ("medications[0].frequency", "2-0-2")
                add_document(g, pid, truth, uploaded, review, error=err,
                             reject_reason="Not my document / wrong patient" if review == "rejected" else None)
            else:
                in_net = random.random() < .6
                issuer = spd_issuer if in_net else (random.choice(OUTSIDE_LABS), f"{random.choice(OUTSIDE_CLINICS)[1]}, Kolkata", g.phone())
                tests = random.sample(["HB", "WBC", "PLT", "FBS", "HBA1C", "CREAT", "UREA", "SGPT", "TSH", "CHOL"], k=random.randint(2, 5))
                values = {t: g.lab_value(t, random.choices(["normal", "high", "low"], [7, 2, 1])[0]) for t in tests}
                truth = _lab_truth(g, pid, issuer, when, values)
                if review == "corrected":
                    t0 = truth["tests"][0]
                    err = ("tests[0].value", round(t0["value"] * 10, 2))   # classic OCR slip: a missed decimal point
                else:
                    err = None
                add_document(g, pid, truth, uploaded, review, issuing_fac="SPD" if in_net else None, error=err,
                             reject_reason="Image unreadable" if review == "rejected" else None)
    write_demo_uploads(g)


def write_demo_uploads(g):
    """The documents the presenter uploads LIVE during the demo (not in the database)."""
    T = g.today
    s = g.heroes["subrata"]
    truth = _rx_truth(g, s, ("Joint Care Clinic", "22 Rajdanga Main Road, Kasba, Kolkata 700107", "+91 98300 12345"),
                      ("Sanjay Ghoshal", "MBBS, MS (Ortho)", "Orthopaedics", "WBMC-58213"), T - timedelta(days=1),
                      "Right knee pain x 3 weeks", ["Osteoarthritis of right knee"],
                      [("Diclofenac", 14, "1-0-1", "after food"), ("Pantoprazole", 14, None, "before breakfast"), ("Calcium", 30, None, None)],
                      "Hot fomentation, quadriceps exercises", "After 2 weeks")
    out = Path(g.args.storage_dir).parent / "demo_uploads"
    out.mkdir(parents=True, exist_ok=True)
    (out / "subrata_knee_prescription.png").write_bytes(docgen.render_prescription(truth, seed=7))
    (out / "subrata_knee_prescription.truth.json").write_text(json.dumps(truth, indent=2, ensure_ascii=False))


# ----------------------------------------------------------------------------- consent
def _consent(g, pid, doc, requested_at, purpose, scope, hours, outcome, respond_after=timedelta(minutes=40),
             granted_scope=None, revoke_at=None, revoke_reason=None, views=0):
    doc_uid = g.user_of_doctor[doc]
    pat_uid = g.user_of_patient[pid]
    fac = g.doctors[doc]["fac"]
    dip, pip = g.staff_ip(doc_uid), g.patient_ip(pat_uid)
    responded = requested_at + respond_after if outcome in {"approved", "denied", "cancelled"} else None
    status = outcome
    if (responded and responded > g.now) or (status == "expired" and requested_at + timedelta(days=7) > g.now):
        status, responded = "pending", None
    rid = g.add("consent_requests", patient_id=pid, doctor_id=doc, facility_id=g.fid(fac), purpose=purpose,
                requested_scope=scope, requested_hours=hours,
                message=f"Dr. {g.doctors[doc]['name']} ({g.fac[fac]['name']}) requests access for {purpose.replace('_', ' ')}.",
                status=status, requested_at=requested_at, responded_at=responded)
    E = g.extra_events
    E.append((requested_at, doc_uid, None, "CONSENT_REQUEST", "consent_requests", rid, dip, f"Scope: {', '.join(scope)}; {hours}h", pid, None))
    if status == "denied":
        E.append((responded, pat_uid, None, "CONSENT_DENY", "consent_requests", rid, pip, None, pid, None))
    if status == "expired":
        E.append((requested_at + timedelta(days=7), None, None, "CONSENT_EXPIRE", "consent_requests", rid, None,
                  "Request expired without a response", pid, None))
    if status != "approved":
        return None
    gscope = granted_scope or scope
    expires = responded + timedelta(hours=hours)
    if revoke_at:
        revoke_at = max(revoke_at, responded + timedelta(hours=1))
        if revoke_at > g.now or revoke_at >= expires:
            revoke_at = None

    gid = g.add("consent_grants", request_id=rid, patient_id=pid, doctor_id=doc, grant_type="patient_granted", scope=gscope,
                granted_at=responded, expires_at=expires, revoked_at=revoke_at, revoked_by_user_id=pat_uid if revoke_at else None,
                revoke_reason=revoke_reason if revoke_at else None, justification=None)
    E.append((responded, pat_uid, None, "CONSENT_GRANT", "consent_grants", gid, pip,
              f"Granted {', '.join(gscope)} until {expires:%d %b %Y %H:%M}", pid, gid))
    end = min(x for x in [expires, revoke_at, g.now] if x)
    for _ in range(views):
        t = responded + timedelta(seconds=random.randint(60, max(61, int((end - responded).total_seconds()) - 60)))
        E.append((t, doc_uid, None, "VIEW", "timeline_events", None, dip, "Viewed patient timeline under consent", pid, gid))
    if revoke_at:
        E.append((revoke_at, pat_uid, None, "CONSENT_REVOKE", "consent_grants", gid, pip, revoke_reason, pid, gid))
    elif expires <= g.now:
        E.append((expires, None, None, "CONSENT_EXPIRE", "consent_grants", gid, None, "Grant expired", pid, gid))
    return gid


def build_consents(g):
    T = g.now
    s, r = g.heroes["subrata"], g.heroes["rupa"]
    hd = g.hero_doc
    # Subrata: an expired grant (cardiologist) and a revoked one (nephrologist). No active grants: the demo creates one.
    _consent(g, s, hd["sourav"], T - timedelta(days=125, hours=2), "consultation",
             ["encounters", "diagnoses", "prescriptions", "lab_results"], 168, "approved", respond_after=timedelta(hours=1, minutes=45), views=2)
    _consent(g, s, hd["arindam"], T - timedelta(days=46, hours=1), "referral", CONSENT_SCOPES, 720, "approved",
             respond_after=timedelta(minutes=25), revoke_at=T - timedelta(days=30), revoke_reason="Consultation completed", views=3)
    # Rupa: her obstetrician has an ACTIVE 90-day grant covering everything.
    _consent(g, r, hd["tanushree"], T - timedelta(days=41, hours=3), "consultation", CONSENT_SCOPES, 2160, "approved",
             respond_after=timedelta(minutes=12), views=4)
    # crowd
    pids = [pid for pid in g.user_of_patient if not g.patients[pid]["hero"]]
    docs = [d for d, x in g.doctors.items() if not x["left"] and d not in hd.values()]
    for _ in range(min(350, len(pids))):
        pid, doc = random.choice(pids), random.choice(docs)
        req = T - timedelta(days=random.uniform(0.1, g.args.history_days))
        purpose = random.choices(["consultation", "follow_up", "second_opinion", "referral"], [50, 20, 15, 15])[0]
        scope = sorted(random.sample(CONSENT_SCOPES, k=random.randint(2, 5)), key=CONSENT_SCOPES.index)
        hours = random.choice([24, 72, 168, 168, 720])
        if req > T - timedelta(days=2) and random.random() < .5:
            outcome = "pending"
        else:
            outcome = random.choices(["approved", "denied", "cancelled", "expired"], [70, 10, 5, 15])[0]
        narrowed = [x for x in scope if x != "documents"] if outcome == "approved" and "documents" in scope and len(scope) > 2 and random.random() < .2 else None
        revoke = req + timedelta(hours=random.uniform(2, hours)) if random.random() < .12 else None
        _consent(g, pid, doc, req, purpose, scope, hours, outcome, respond_after=timedelta(minutes=random.randint(3, 600)),
                 granted_scope=narrowed, revoke_at=revoke, revoke_reason=random.choice(["No longer needed", "Changed doctor", "Privacy concern"]),
                 views=random.randint(0, 4))
    # emergency "break-glass" overrides: time-boxed, justified, and loudly audited
    emr = [d for d in docs if g.doctors[d]["dept"] == "EMR"]
    reasons = random.sample([
        "Brought in unresponsive after a road accident; allergy and medication history needed before surgery.",
        "Found collapsed at home, not able to give history; checking for anticoagulants and known allergies.",
        "Severe hypoglycaemia, patient confused; need current diabetes medications and kidney function.",
        "Suspected stroke, attendant unaware of medicines; need anticoagulant history before thrombolysis.",
        "Anaphylaxis in the emergency room, patient intubated; need documented drug allergies.",
        "Seizure on arrival, no family present; need previous diagnoses and anti-epileptic prescriptions.",
    ], 6)
    for reason in reasons:
        pid, doc = random.choice(pids), random.choice(emr)
        t = T - timedelta(days=random.uniform(1, g.args.history_days))
        gid = g.add("consent_grants", request_id=None, patient_id=pid, doctor_id=doc, grant_type="emergency_override",
                    scope=["encounters", "diagnoses", "prescriptions", "lab_results"], granted_at=t, expires_at=t + timedelta(hours=24),
                    revoked_at=None, revoked_by_user_id=None, revoke_reason=None,
                    justification=reason)
        uid = g.user_of_doctor[doc]
        g.extra_events.append((t, uid, None, "EMERGENCY_ACCESS", "consent_grants", gid, g.staff_ip(uid),
                               "Break-glass access, 24h. Patient will be notified.", pid, gid))
        g.extra_events.append((t + timedelta(minutes=3), uid, None, "VIEW", "timeline_events", None, g.staff_ip(uid),
                               "Viewed patient timeline under emergency access", pid, gid))


# ----------------------------------------------------------------------------- bed availability
def build_availability(g):
    admin_of = {u["fac"]: uid for uid, u in g.users.items() if u["role"] == "admin"}
    for code, f in g.fac.items():
        totals = {}
        for b in g.beds:
            if b["fac"] == code:
                totals[b["type"]] = totals.get(b["type"], 0) + 1
        if not totals:
            continue
        last_offset = timedelta(hours=31) if code == "SHH" else timedelta(minutes=random.randint(15, 150))
        auto_only = code == "BSN"
        times, t = [], g.now - timedelta(days=7) + timedelta(minutes=random.randint(0, 120))
        last = g.now - last_offset
        while t < last - timedelta(hours=2):
            times.append(t)
            t += timedelta(hours=4, minutes=random.randint(-40, 40))
        times.append(last)
        for t in times:
            for wtype, total in totals.items():
                occupied = sum(1 for s, e in g.admission_intervals[(code, wtype)] if s <= t < e)
                avail = max(0, min(total, total - occupied + (random.choice([-1, 1]) if random.random() < .15 else 0)))
                auto = auto_only or random.random() < .1
                g.add("bed_availability_reports", facility_id=f["id"], ward_type=wtype, total_beds=total, available_beds=avail,
                      reported_at=t, reported_by_user_id=None if auto else admin_of[code],
                      source="auto_computed" if auto else "hospital_confirmed",
                      note="Auto-computed from admissions; not confirmed by hospital staff" if auto else None)
