#!/usr/bin/env python3
"""
seed.py - builds the Health Setu demo database: a network of 9 fictional West Bengal facilities,
~3,000 shared patients, clinical history, documents, consent, availability reports and an audit log.
Everything is 100% SYNTHETIC.

    python seed.py                        # default size
    python seed.py --patients 6000        # bigger network
    python seed.py --export-csv data/     # also dump every table to CSV

Every run DROPS and recreates the schema. Same --seed + same --anchor-date => identical data.
"""
from __future__ import annotations

import argparse
import hashlib
import math
import os
import random
import sys
import time as clock
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extras import Json, execute_values
    from faker import Faker
except ImportError:
    sys.exit("Missing packages. Run:  pip install -r requirements.txt")

import healthsetu
from reference import *  # noqa: F401,F403  (constants only)

HERE = Path(__file__).resolve().parent


def money(x: float) -> float:
    return round(x + 1e-9, 2)


class Generator:
    def __init__(self, args):
        self.args = args
        self.fake = Faker("en_IN")
        if args.anchor_date:     # reproducible: "now" is noon on the anchor day
            self.today = date.fromisoformat(args.anchor_date)
            self.now = datetime.combine(self.today, time(12, 0))
        else:                    # live demo: "now" is the DATABASE clock, so freshness labels are right on stage
            self.now = args.db_now
            self.today = self.now.date()
        self.start = self.now - timedelta(days=args.history_days)
        self.rows: dict[str, list[dict]] = defaultdict(list)
        self._ids: dict[str, int] = defaultdict(int)
        self.used_emails: set[str] = set()
        self.first_event: dict[int, datetime] = {}
        self.extra_events: list[tuple] = []      # audit events produced by the Health Setu layer

    # ------------------------------------------------------------------ helpers
    def add(self, table: str, **cols) -> int:
        if "id" not in cols:
            self._ids[table] += 1
            cols = {"id": self._ids[table], **cols}
        self.rows[table].append(cols)
        return cols["id"]

    def phone(self) -> str:
        return f"+91 {random.choice('6789')}{random.randint(0, 999_999_999):09d}"

    def email(self, first: str, last: str) -> str:
        base = "".join(ch for ch in f"{first}.{last}".lower() if ch.isalnum() or ch == ".")
        e, n = f"{base}@example.com", 1
        while e in self.used_emails:
            n += 1
            e = f"{base}{n}@example.com"
        self.used_emails.add(e)
        return e

    def name(self, sex: str) -> tuple[str, str]:
        first = self.fake.first_name_male() if sex == "M" else self.fake.first_name_female()
        return first, self.fake.last_name()

    def touch_patient(self, pid: int, when: datetime):
        if pid not in self.first_event or when < self.first_event[pid]:
            self.first_event[pid] = when

    def fid(self, fac_code: str) -> int:
        return self.fac[fac_code]["id"]

    # ------------------------------------------------------------------ 1. reference data
    def build_reference(self):
        self.role_id = {n: self.add("roles", name=n, description=d) for n, d in ROLES}
        self.dept = {}
        for code, name, floor, spec, qual, fee in DEPARTMENTS:
            did = self.add("departments", code=code, name=name, floor=floor, phone_extension=f"{floor}{len(self.dept):02d}")
            self.dept[code] = dict(id=did, spec=spec, qual=qual, fee=fee, name=name)
        self.icd = {}
        for code, desc, dep, amin, amax, sex, chronic in ICD10:
            self.rows["icd10_codes"].append(dict(code=code, description=desc, department_id=self.dept[dep]["id"], is_chronic=chronic))
            self.icd[code] = dict(dept=dep, amin=amin, amax=amax, sex=sex, chronic=chronic, desc=desc)
        self.lab = {}
        for code, name, cat, unit, lo, hi, price, dec, hm, lm in LAB_TESTS:
            tid = self.add("lab_tests", code=code, name=name, category=cat, unit=unit, normal_min=lo, normal_max=hi, price=price)
            self.lab[code] = dict(id=tid, lo=lo, hi=hi, price=price, dec=dec, hm=hm, lm=lm, name=name, unit=unit)
        self.med, self.meds_by_word = {}, defaultdict(list)
        for name, generic, form, strength, price, freq, per_day in MEDICATIONS:
            word = name.split()[0]
            mid = self.add("medications", name=name, generic_name=generic, form=form, strength=strength,
                           drug_classes=MED_CLASSES[word], unit_price=price,
                           requires_prescription=word not in {"Paracetamol", "ORS", "Cetirizine"})
            self.med[name] = dict(id=mid, form=form, price=price, freq=freq, per_day=per_day, name=name)
            self.meds_by_word[word].append(mid)
        self.med_by_id = {m["id"]: m for m in self.med.values()}
        for a, b, sev, desc, rec in DRUG_INTERACTIONS:
            for ma in self.meds_by_word[a]:
                for mb in self.meds_by_word[b]:
                    self.add("drug_interactions", medication_a_id=min(ma, mb), medication_b_id=max(ma, mb),
                             severity=sev, description=desc, recommendation=rec)
        for word, icd_prefix, sev, desc, rec in DRUG_CONDITION_CAUTIONS:
            for mid in self.meds_by_word[word]:
                self.add("drug_condition_cautions", medication_id=mid, icd_prefix=icd_prefix, severity=sev,
                         description=desc, recommendation=rec)
        self.insurer = [(self.add("insurance_providers", name=n, provider_type=t,
                                  helpline=f"1800-{random.randint(100, 999)}-{random.randint(1000, 9999)}"), n, t)
                        for n, t in INSURERS]
        # facilities
        self.fac = {}
        for code, name, ftype, own, profile, loc, city, region, pin, lat, lon, emerg, extra in FACILITIES:
            fid = self.add("facilities", code=code, name=name, facility_type=ftype, ownership=own, locality=loc, city=city,
                           state="West Bengal", pincode=pin, latitude=lat, longitude=lon,
                           phone=f"+91 33 {random.randint(2000, 4999)} {random.randint(1000, 9999)}" if region == "KOL"
                           else f"+91 {'343' if region == 'DGP' else '353'} {random.randint(250, 299)} {random.randint(1000, 9999)}",
                           emergency_24x7=emerg, is_participating=True,
                           joined_network_at=self.now - timedelta(days=random.randint(200, 400)), is_synthetic=True)
            depts = list(dict.fromkeys(PROFILE_DEPTS[profile] + extra))
            self.fac[code] = dict(id=fid, code=code, name=name, profile=profile, region=region, city=city, locality=loc,
                                  pincode=pin, depts=depts, phone=self.rows["facilities"][-1]["phone"])
            services = list(dict.fromkeys(PROFILE_SERVICES[profile] + EXTRA_SERVICES.get(code, [])))
            if not emerg and "24x7 Emergency" in services:
                services.remove("24x7 Emergency")
            for svc in services:
                note = SERVICE_OUTAGES.get((code, svc))
                self.add("facility_services", facility_id=fid, service=svc, is_available=note is None, note=note,
                         updated_at=self.now - timedelta(hours=random.randint(2, 30) if note else random.randint(24, 24 * 20)))

    # ------------------------------------------------------------------ 2. wards & beds
    def build_facility(self):
        self.beds = []
        spec = {w[0]: w for w in WARDS}
        for code, f in self.fac.items():
            names, scale = PROFILE_WARDS[f["profile"]]
            f["beds"] = 0
            for wname in names:
                _, wtype, dep, floor, n, rate, stay, sex, ages, occ, codes = spec[wname]
                if dep and dep not in f["depts"] and dep not in {"GM", "EMR"}:
                    continue
                count = max(4 if wtype == "icu" else 2, round(n * scale))
                rate = round(rate * (0.8 if f["profile"] in {"small", "medium"} else 1.0) * (0.5 if code == "SGH" else 1), -1)
                wid = self.add("wards", facility_id=f["id"], name=wname, ward_type=wtype,
                               department_id=self.dept[dep]["id"] if dep else None, floor=floor, daily_rate=rate)
                tag = "".join(w[0] for w in wname.replace("(", "").split())[:3].upper()
                for k in range(1, count + 1):
                    bid = self.add("beds", ward_id=wid, bed_number=f"{tag}-{k:02d}", is_operational=True)
                    self.beds.append(dict(id=bid, fac=code, ward=wname, type=wtype, rate=rate, stay=stay, sex=sex,
                                          ages=ages, occ=occ, codes=codes))
                    f["beds"] += 1

    # ------------------------------------------------------------------ 3. people
    def build_people(self):
        a = self.args
        self.doctors, self.fac_dept_doctors, self.fac_doctors = {}, defaultdict(list), defaultdict(list)
        self.hero_doc = {}

        def make_doctor(fac, dept, first, last, sex):
            d = self.dept[dept]
            fee = random.randrange(d["fee"][0], d["fee"][1] + 1, 50)
            if self.fac[fac]["profile"] == "small" or fac == "SGH":
                fee = max(200, fee // 2 // 50 * 50)
            n = self._ids["doctors"] + 1
            did = self.add("doctors", employee_code=f"DR-{n:04d}", facility_id=self.fid(fac), first_name=first, last_name=last,
                           gender=sex, department_id=d["id"], specialization=d["spec"], qualification=d["qual"],
                           registration_no=f"WBMC-{random.randint(40000, 99999)}-{n:03d}", phone=self.phone(),
                           email=self.email(first, last), consultation_fee=fee,
                           joined_on=self.today - timedelta(days=random.randint(400, 5500)), left_on=None, is_active=True)
            self.doctors[did] = dict(dept=dept, fac=fac, fee=fee, left=None, name=f"{first} {last}", first=first, last=last)
            self.fac_dept_doctors[(fac, dept)].append(did)
            self.fac_doctors[fac].append(did)
            return did

        for h in healthsetu.HERO_DOCTORS:
            self.hero_doc[h["key"]] = make_doctor(h["fac"], h["dept"], h["first"], h["last"], h["sex"])
        for code, f in self.fac.items():
            for dept in f["depts"]:
                want = 2 if f["profile"] == "large" and dept in {"GM", "CAR", "PED", "OBG"} else 1
                for _ in range(want - len(self.fac_dept_doctors[(code, dept)])):
                    sex = random.choice("MMF")
                    make_doctor(code, dept, *self.name(sex), sex)
        # a Ganga View GM doctor resigned 30 days ago (their account is part of the audit-log story)
        gone = next(d for d in reversed(self.fac_dept_doctors[("GVH", "GM")]) if d not in self.hero_doc.values())
        self.doctors[gone]["left"] = datetime.combine(self.today - timedelta(days=30), time())
        row = self.rows["doctors"][gone - 1]
        row["left_on"], row["is_active"] = self.doctors[gone]["left"].date(), False
        self.resigned_doctor = gone

        # staff per facility
        self.staff, self.staff_info, self.fac_staff = defaultdict(list), {}, defaultdict(lambda: defaultdict(list))
        n = 0
        for code, f in self.fac.items():
            beds = f["beds"]
            if f["profile"] == "diagnostic":
                mix = [("receptionist", 2), ("lab_technician", 5), ("billing", 1), ("admin", 1)]
            else:
                mix = [("nurse", max(4, round(beds * .4))), ("receptionist", 2 + beds // 50), ("lab_technician", 1 + beds // 40),
                       ("pharmacist", 1 + beds // 60), ("billing", 1 + beds // 60), ("admin", 1)]
            clinical = [d for d in f["depts"] if d not in {"DER", "ENT"}] or ["GM"]
            for role, count in mix:
                for k in range(count):
                    n += 1
                    sex = "F" if role == "nurse" and random.random() < .85 else random.choice("MF")
                    first, last = self.name(sex)
                    shift = ["morning", "evening", "night"][k % 3] if role == "nurse" else "general"
                    dept = self.dept[clinical[k % len(clinical)]]["id"] if role == "nurse" else None
                    sid = self.add("staff", employee_code=f"ST-{n:04d}", facility_id=f["id"], first_name=first, last_name=last,
                                   gender=sex, role=role, department_id=dept, shift=shift, phone=self.phone(),
                                   email=self.email(first, last), joined_on=self.today - timedelta(days=random.randint(90, 4000)),
                                   is_active=True)
                    self.staff[role].append(sid)
                    self.fac_staff[code][role].append(sid)
                    self.staff_info[sid] = dict(role=role, shift=shift, fac=code)

        # patients: the scripted "hero" patients first (ids 1, 2), then the crowd
        self.patients = {}
        healthsetu.add_hero_patients(self)
        buckets = [((0, 12), .15), ((13, 17), .05), ((18, 40), .35), ((41, 60), .28), ((61, 90), .17)]
        blood = (["O+", "B+", "A+", "AB+", "O-", "B-", "A-", "AB-"], [32, 32, 21, 8, 2, 2, 2, 1])
        relations = ["Spouse", "Father", "Mother", "Son", "Daughter", "Brother", "Sister"]
        used_abha = set()
        for i in range(len(self.patients) + 1, a.patients + 1):
            lo, hi = random.choices([b[0] for b in buckets], [b[1] for b in buckets])[0]
            age = random.randint(lo, hi)
            dob = self.today - timedelta(days=age * 365 + random.randint(0, 364))
            sex = random.choice("MF")
            first, last = self.name(sex)
            city, region, _, pins = random.choices(CITIES, [c[2] for c in CITIES])[0]
            chronic = {c for c, (min_age, p) in CHRONIC_PREVALENCE.items() if age >= min_age and random.random() < p}
            ec_first, _ = self.name(random.choice("MF"))
            abha = None
            if random.random() < .35:
                base = f"{first}.{last}".lower().replace(" ", "")
                abha = f"{base}{random.randint(10, 99)}@demo"
                while abha in used_abha:
                    abha = f"{base}{random.randint(100, 9999)}@demo"
                used_abha.add(abha)
            pid = self.add("patients", patient_code=f"PT-{i:06d}", first_name=first, last_name=last, gender=sex,
                           date_of_birth=dob, blood_group=random.choices(*blood)[0],
                           phone=self.phone() if age >= 16 else None,
                           email=self.email(first, last) if age >= 18 and random.random() < .6 else None,
                           address=self.fake.street_address(), city=city, state="West Bengal", pincode=random.choice(pins),
                           emergency_contact_name=f"{ec_first} {last}",
                           emergency_contact_relation=random.choice(["Father", "Mother"]) if age < 18 else random.choice(relations),
                           emergency_contact_phone=self.phone(), abha_address=abha,
                           registered_at=self.now - timedelta(days=random.randint(1, 1500), minutes=random.randint(0, 600)))
            self.patients[pid] = dict(age=age, sex=sex, chronic=chronic, busy=[], ins=None, region=region, hero=False,
                                      name=f"{first} {last}", code=f"PT-{i:06d}")
            # drug allergies (~8%)
            if random.random() < .08:
                allergen, cls, reactions, _ = random.choices(DRUG_ALLERGIES, [x[3] for x in DRUG_ALLERGIES])[0]
                self.add("patient_allergies", patient_id=pid, allergen=allergen, allergen_class=cls,
                         reaction=random.choice(reactions), severity=random.choices(["mild", "moderate", "severe"], [4, 4, 2])[0],
                         source=random.choice(["patient_reported", "clinician_recorded"]),
                         recorded_at=self.now - timedelta(days=random.randint(10, 900)))

        # insurance (~40%)
        for pid, p in self.patients.items():
            if p["hero"] or random.random() >= .40:
                continue
            prov_id, pname, _ = random.choice(self.insurer)
            limit = 500000 if "PM-JAY" in pname else random.choice([200000, 300000, 500000, 1000000])
            vf = self.today - timedelta(days=random.randint(30, 1000))
            vt = self.today + timedelta(days=random.randint(-60, 365))
            if vt <= vf:
                vt = vf + timedelta(days=365)
            iid = self.add("patient_insurance", patient_id=pid, provider_id=prov_id,
                           policy_number=f"POL-{prov_id:02d}-{random.randint(10**7, 10**8 - 1)}-{pid}",
                           coverage_limit=limit, valid_from=vf, valid_to=vt)
            p["ins"] = dict(id=iid, limit=limit, vf=vf, vt=vt)

        # who can plausibly have which diagnosis (hero patients are excluded: their history is scripted)
        self.eligible = defaultdict(list)
        for pid, p in self.patients.items():
            if p["hero"]:
                continue
            for code, c in self.icd.items():
                if c["amin"] <= p["age"] <= c["amax"] and (c["sex"] is None or c["sex"] == p["sex"]):
                    if not c["chronic"] or code in p["chronic"]:
                        self.eligible[(code, None)].append(pid)
                        self.eligible[(code, p["region"])].append(pid)

    def pool(self, code: str, region: str) -> list[int]:
        """Patients mostly use facilities in their own region."""
        local = self.eligible[(code, region)]
        return local if local and random.random() < .9 else self.eligible[(code, None)]

    # ------------------------------------------------------------------ clinical building blocks
    def pick_doctor(self, fac: str, dept: str, when: datetime) -> int | None:
        for d in (dept, "GM", "EMR"):
            options = [x for x in self.fac_dept_doctors[(fac, d)] if not self.doctors[x]["left"] or when < self.doctors[x]["left"]]
            if options:
                return random.choice(options)
        options = [x for x in self.fac_doctors[fac] if not self.doctors[x]["left"] or when < self.doctors[x]["left"]]
        return random.choice(options) if options else None

    def add_diagnosis(self, pid, doc, code, when, appt=None, adm=None, severity=None, dtype="primary", notes=None):
        sev = severity or random.choices(["mild", "moderate", "severe"], [.5, .4, .1])[0]
        return self.add("diagnoses", patient_id=pid, doctor_id=doc, icd_code=code, appointment_id=appt, admission_id=adm,
                        diagnosed_at=when, diagnosis_type=dtype, severity=sev, notes=notes)

    def rx_quantity(self, med: dict, days: int) -> int:
        if med["name"].startswith("Insulin"):
            return max(1, math.ceil(days / 30))
        if med["form"] in {"tablet", "capsule", "injection", "iv_fluid", "sachet"}:
            return med["per_day"] * days
        return max(1, math.ceil(days / 15))

    def add_rx(self, pid, doc, when, items, appt=None, adm=None, notes=None) -> tuple[int, float]:
        """items: list of (medication name, days, frequency or None, instructions or None)."""
        rx = self.add("prescriptions", facility_id=self.fid(self.doctors[doc]["fac"]), patient_id=pid, doctor_id=doc,
                      appointment_id=appt, admission_id=adm, prescribed_at=when, notes=notes)
        total = 0.0
        for name, days, freq, instr in items:
            m = self.med[name]
            qty = self.rx_quantity(m, days)
            self.add("prescription_items", prescription_id=rx, medication_id=m["id"], dosage=name.split(" ", 1)[1],
                     frequency=freq or m["freq"], duration_days=days, quantity=qty, instructions=instr)
            total += qty * m["price"]
        return rx, total

    def add_prescription(self, pid, doc, code, when, days, appt=None, adm=None) -> float:
        age = self.patients[pid]["age"]
        wanted = CONDITION_MEDS.get(prefix(code), ["Paracetamol"])
        if appt is None and "Pantoprazole" not in wanted and random.random() < .5:
            wanted = wanted + ["Pantoprazole"]
        names = []
        for w in wanted:
            if age < 12:
                if w in CHILD_SWAP:
                    names.append(CHILD_SWAP[w]); continue
                if w not in CHILD_SAFE:
                    continue
            names.append(M[w])
        if appt is not None:
            names = [n for n in names if self.med[n]["form"] not in {"iv_fluid", "injection"} or n.startswith("Insulin")]
        if not names:
            return 0.0
        instr = lambda: random.choice([None, None, "Take after food", "Avoid alcohol", "Complete the full course"])
        _, total = self.add_rx(pid, doc, when, [(n, max(1, int(days)), None, instr()) for n in dict.fromkeys(names)],
                               appt=appt, adm=adm, notes="Review after course completion" if random.random() < .3 else None)
        return total

    def lab_value(self, code: str, direction: str) -> float:
        t = self.lab[code]
        lo, hi = t["lo"], t["hi"]
        if direction == "high":
            v = hi * random.uniform(*t["hm"])
        elif direction == "low" and t["lm"]:
            v = lo * random.uniform(*t["lm"])
        elif lo == 0:
            v = random.uniform(0, hi * .7)
        else:
            span = hi - lo
            v = random.uniform(lo + .1 * span, hi - .1 * span)
        return round(v, t["dec"])

    def lab_flag(self, code: str, v: float) -> str:
        t = self.lab[code]
        return "high" if v > t["hi"] else "low" if v < t["lo"] else "normal"

    def add_lab_order(self, pid, doc, when, values: dict, appt=None, adm=None, priority="routine", done_after_h=None):
        """values: {test_code: value or None(=pending)}. Returns billable [(name, price)]."""
        fac = self.doctors[doc]["fac"]
        done_at = when + timedelta(hours=done_after_h if done_after_h is not None else
                                   (random.uniform(1, 6) if priority == "urgent" else random.uniform(3, 30)))
        status = "completed" if done_at <= self.now else "pending"
        oid = self.add("lab_orders", facility_id=self.fid(fac), patient_id=pid, doctor_id=doc, appointment_id=appt,
                       admission_id=adm, ordered_at=when, priority=priority, status=status)
        if status == "completed":
            techs = self.fac_staff[fac]["lab_technician"] or self.staff["lab_technician"]
            tech = random.choice(techs)
            for t, v in values.items():
                self.add("lab_results", lab_order_id=oid, lab_test_id=self.lab[t]["id"], result_value=v,
                         flag=self.lab_flag(t, v), resulted_at=done_at, technician_id=tech)
        return [(self.lab[t]["name"], self.lab[t]["price"]) for t in values]

    def add_labs(self, pid, doc, code, dept, when, appt=None, adm=None, priority="routine"):
        bias = LAB_BIAS.get(prefix(code), {})
        tests = list(dict.fromkeys(list(bias) + random.sample(DEPT_PANEL[dept], k=min(len(DEPT_PANEL[dept]), random.randint(1, 3)))))
        if adm is not None:
            tests = list(dict.fromkeys(["HB", "WBC", "PLT"] + tests))
        values = {}
        for t in tests:
            if t in bias and random.random() < .8:
                direction = bias[t]
            elif random.random() < .08:
                direction = "high" if self.lab[t]["lo"] == 0 else random.choice(["high", "low"])
            else:
                direction = "normal"
            values[t] = self.lab_value(t, direction)
        return self.add_lab_order(pid, doc, when, values, appt=appt, adm=adm, priority=priority)

    def add_invoice(self, pid, fac, kind, when, items, appt=None, adm=None) -> tuple[int, float]:
        subtotal = money(sum(i[3] * i[2] for i in items))
        discount = money(subtotal * random.choice([.05, .10, .15])) if random.random() < .08 else 0.0
        total = money(subtotal - discount)
        inv = self.add("invoices", invoice_number=f"INV-{fac}-{when.year}-{self._ids['invoices'] + 1:06d}",
                       facility_id=self.fid(fac), patient_id=pid, appointment_id=appt, admission_id=adm, invoice_type=kind,
                       issued_at=when, subtotal=subtotal, discount=discount, tax=0.0, total_amount=total, status="unpaid")
        for item_type, desc, qty, unit in items:
            self.add("invoice_items", invoice_id=inv, item_type=item_type, description=desc, quantity=qty,
                     unit_price=money(unit), amount=money(qty * unit))
        return inv, total

    def pay(self, inv, when, amount, method=None):
        if amount <= 0.009 or when > self.now:
            return
        method = method or random.choices(["upi", "cash", "card", "netbanking"], [50, 25, 20, 5])[0]
        ref = None if method == "cash" else f"{method.upper()[:3]}{random.randint(10**9, 10**10 - 1)}"
        self.add("payments", invoice_id=inv, paid_at=when, amount=money(amount), method=method, reference_number=ref)

    # ------------------------------------------------------------------ 4. OPD appointments
    def build_appointments(self):
        a = self.args
        doc_ids = list(self.doctors)
        weights = [.3 if self.doctors[d]["dept"] == "EMR" else 1.0 for d in doc_ids]
        taken, specs, tries = set(), [], 0
        while len(specs) < a.appointments and tries < a.appointments * 20:
            tries += 1
            doc = random.choices(doc_ids, weights)[0]
            future = random.random() < .08
            day = (self.today + timedelta(days=random.randint(0, 30))) if future else \
                  (self.start.date() + timedelta(days=random.randint(0, a.history_days)))
            if day.weekday() == 6:
                continue
            when = datetime.combine(day, time(9, 0)) + timedelta(minutes=15 * random.randint(0, 31))
            info = self.doctors[doc]
            if (doc, when) in taken or (info["left"] and when >= info["left"]):
                continue
            codes = [c for c, v in self.icd.items() if v["dept"] == info["dept"] and c not in INPATIENT_ONLY and self.eligible[(c, None)]]
            if not codes:
                continue
            code = random.choices(codes, [3 if self.icd[c]["chronic"] else 1 for c in codes])[0]
            pid = random.choice(self.pool(code, self.fac[info["fac"]]["region"]))
            taken.add((doc, when))
            specs.append((when, doc, pid, code))
        specs.sort()
        self.seen = set()
        for when, doc, pid, code in specs:
            info = self.doctors[doc]
            dept, fac = info["dept"], info["fac"]
            if when > self.now:
                status = random.choices(["scheduled", "cancelled"], [.93, .07])[0]
            else:
                status = random.choices(["completed", "no_show", "cancelled"], [.82, .10, .08])[0]
            visit = "follow_up" if (pid, fac, dept) in self.seen else "new"
            if status == "completed":
                self.seen.add((pid, fac, dept))
            created = min(max(when - timedelta(days=random.randint(0, 14), hours=random.randint(1, 8)),
                              self.start - timedelta(days=14)), when)
            appt = self.add("appointments", facility_id=self.fid(fac), patient_id=pid, doctor_id=doc, scheduled_at=when,
                            status=status, visit_type=visit,
                            reason=self.icd[code]["desc"] if visit == "new" else f"Follow-up: {self.icd[code]['desc']}",
                            created_at=created)
            self.touch_patient(pid, created)
            if status != "completed":
                continue
            seen_at = when + timedelta(minutes=random.randint(5, 25))
            self.add_diagnosis(pid, doc, code, seen_at, appt=appt)
            if random.random() < .80:
                self.add_prescription(pid, doc, code, seen_at, 30 if self.icd[code]["chronic"] else random.randint(3, 7), appt=appt)
            items = [("consultation", f"Consultation - Dr. {info['name']}", 1, info["fee"])]
            if random.random() < (.70 if prefix(code) in LAB_BIAS else .30):
                items += [("lab", n, 1, p) for n, p in self.add_labs(pid, doc, code, dept, seen_at + timedelta(minutes=10), appt=appt)]
            inv, total = self.add_invoice(pid, fac, "opd", seen_at, items, appt=appt)
            if random.random() < .96:
                self.pay(inv, seen_at + timedelta(minutes=random.randint(5, 40)), total)

    # ------------------------------------------------------------------ 5. IPD admissions
    def build_admissions(self):
        far = datetime(3000, 1, 1)
        month = timedelta(days=30)
        specs = []
        for bed in self.beds:
            smin, smax, smode = bed["stay"]
            mean_stay = (smin + smax + smode) / 3
            mean_gap = mean_stay * (1 - bed["occ"]) / bed["occ"]
            region = self.fac[bed["fac"]]["region"]
            t = self.start + timedelta(days=random.uniform(0, mean_gap * 2))
            while t < self.now:
                t = t.replace(minute=random.randint(0, 59))
                end = t + timedelta(days=random.triangular(smin, smax, smode))
                placed = False
                for _ in range(40):
                    code = random.choice(bed["codes"])
                    pool = self.pool(code, region)
                    if not pool:
                        continue
                    pid = random.choice(pool)
                    p = self.patients[pid]
                    if bed["sex"] and p["sex"] != bed["sex"]:
                        continue
                    if not bed["ages"][0] <= p["age"] <= bed["ages"][1]:
                        continue
                    if code in {"O80", "O82"} and any(x[2] in {"O80", "O82"} for x in p["busy"]):
                        continue
                    real_end = end if end <= self.now else far
                    if any(s < real_end and t < e for s, e, _ in p["busy"]):
                        continue
                    if any(t - month < e and s < real_end + month for s, e, _ in p["busy"]) and random.random() < .75:
                        continue   # keeps 30-day readmissions realistic (~8%)
                    p["busy"].append((t, real_end, code))
                    specs.append((t, bed, pid, code, end if end <= self.now else None))
                    placed = True
                    break
                if placed:
                    t = end + timedelta(days=random.expovariate(1 / max(mean_gap, .05))) + timedelta(hours=random.uniform(1, 6))
                else:
                    t += timedelta(hours=random.uniform(4, 12))
        specs.sort(key=lambda s: s[0])
        self.admission_intervals = defaultdict(list)     # (facility, ward_type) -> [(start, end)]
        for admitted, bed, pid, code, discharged in specs:
            c = self.icd[code]
            fac = bed["fac"]
            dept = "EMR" if bed["type"] == "emergency" else c["dept"]
            doc = self.pick_doctor(fac, dept, admitted)
            if bed["type"] in {"icu", "emergency"}:
                atype = random.choices(["emergency", "transfer"], [.85, .15])[0]
            elif bed["type"] == "maternity" or code in {"K80.2", "K40.9", "M17.9"}:
                atype = random.choices(["planned", "emergency"], [.75, .25])[0]
            else:
                atype = random.choices(["emergency", "planned", "transfer"], [.5, .4, .1])[0]
            disp = summary = None
            if discharged:
                disp = random.choices(["recovered", "improved", "referred", "lama", "deceased"],
                                      [.45, .40, .07, .03, .05 if bed["type"] == "icu" else 0])[0]
                proc = PROCEDURES.get(code)
                how = f"underwent {proc[0].lower()}" if proc else "was managed medically"
                summary = {
                    "deceased": f"Admitted with {c['desc'].lower()}. Despite resuscitative measures the patient expired.",
                    "lama": f"Admitted with {c['desc'].lower()}. Left against medical advice; risks explained to family.",
                    "referred": f"Admitted with {c['desc'].lower()}. Referred to a higher centre for specialised care.",
                }.get(disp, f"Admitted with {c['desc'].lower()} and {how}. Condition at discharge: {disp}. "
                            f"Review in {self.dept[c['dept']]['spec']} OPD after {random.choice([5, 7, 10, 14])} days.")
            adm = self.add("admissions", admission_code=f"ADM-{fac}-{self._ids['admissions'] + 1:06d}", facility_id=self.fid(fac),
                           patient_id=pid, attending_doctor_id=doc, bed_id=bed["id"], admission_type=atype, admitted_at=admitted,
                           discharged_at=discharged, status="discharged" if discharged else "admitted",
                           reason=c["desc"], discharge_disposition=disp, discharge_summary=summary)
            self.admission_intervals[(fac, bed["type"])].append((admitted, discharged or datetime(3000, 1, 1)))
            self.touch_patient(pid, admitted)
            end = discharged or self.now
            days = max(1, math.ceil((end - admitted).total_seconds() / 86400))
            self.add_diagnosis(pid, doc, code, admitted + timedelta(minutes=30), adm=adm,
                               severity="severe" if bed["type"] == "icu" else random.choice(["moderate", "moderate", "severe", "mild"]))
            for chronic in self.patients[pid]["chronic"] & {"I10", "E11.9", "J44.9", "N18.9"}:
                self.add_diagnosis(pid, doc, chronic, admitted + timedelta(minutes=35), adm=adm, severity="mild",
                                   dtype="secondary", notes="Known case, on treatment")
            pharmacy = self.add_prescription(pid, doc, code, admitted + timedelta(hours=1), min(days, 14), adm=adm)
            labs = self.add_labs(pid, doc, code, self.doctors[doc]["dept"], admitted + timedelta(minutes=45), adm=adm,
                                 priority="urgent" if atype == "emergency" else "routine")
            if days > 3:
                labs += self.add_labs(pid, doc, code, self.doctors[doc]["dept"], admitted + timedelta(days=3, hours=7), adm=adm)
            self.add_vitals(adm, pid, code, bed, admitted, end, disp)
            if discharged:
                self.bill_admission(adm, pid, code, bed, doc, discharged, days, pharmacy, labs)

    def add_vitals(self, adm, pid, code, bed, start, end, disp):
        step = timedelta(hours=4 if bed["type"] == "icu" else 8)
        times, t = [], start + timedelta(minutes=20)
        while t <= end and t <= self.now:
            times.append(t)
            t += step
        p = prefix(code)
        fever, resp, icu = p in FEVER, p in RESP, bed["type"] == "icu"
        htn = "I10" in self.patients[pid]["chronic"]
        child = self.patients[pid]["age"] < 12
        nurses = self.fac_staff[bed["fac"]]["nurse"] or self.staff["nurse"]
        for k, t in enumerate(times):
            prog = k / max(1, len(times) - 1)
            sev = .6 + .4 * prog if disp == "deceased" else (1 - .5 * prog if disp is None else (1 - prog) ** 1.5)
            temp = random.gauss(36.8, .2) + (sev * random.uniform(1.0, 2.6) if fever else 0)
            pulse = random.gauss(100 if child else 80, 7) + sev * (15 * fever + 25 * icu)
            sys_bp = random.gauss(100 if child else 122, 8) + (25 if htn else 0) + (sev * random.gauss(0, 18) if icu else 0)
            rr = random.gauss(24 if child else 16, 2) + sev * (6 * resp + 6 * icu)
            spo2 = random.gauss(97.5, .8) - ((sev * random.uniform(3, 10)) if (resp or icu) else 0)
            self.add("vitals", admission_id=adm, recorded_by=random.choice(nurses), recorded_at=t,
                     temperature_c=round(temp, 1), pulse_bpm=int(pulse), bp_systolic=int(sys_bp),
                     bp_diastolic=int(sys_bp * .63 + random.gauss(0, 4)), respiratory_rate=int(rr),
                     spo2_percent=int(min(100, max(70, spo2))))

    def bill_admission(self, adm, pid, code, bed, doc, discharged, days, pharmacy, labs):
        items = [("room", f"{bed['ward']} charges", days, bed["rate"]),
                 ("doctor_visit", f"Consultant visits - Dr. {self.doctors[doc]['name']}", days, 600),
                 ("nursing", "Nursing care", days, 400)]
        if bed["type"] == "icu":
            items.append(("icu_charges", "Monitoring / ventilator support", days, 2500))
        if code in PROCEDURES:
            items.append(("procedure", PROCEDURES[code][0], 1, PROCEDURES[code][1]))
        items += [("lab", n, 1, p) for n, p in labs]
        if pharmacy:
            items.append(("pharmacy", "Medicines & consumables", 1, money(pharmacy)))
        inv, total = self.add_invoice(pid, bed["fac"], "ipd", discharged, items, adm=adm)
        ins = self.patients[pid]["ins"]
        paid_later = discharged + timedelta(days=random.randint(1, 20))
        if ins and ins["vf"] <= discharged.date() <= ins["vt"]:
            claimed = money(min(total, ins["limit"]))
            submitted = min(discharged + timedelta(days=random.randint(0, 2)), self.now)
            age = (self.now - submitted).days
            if age < 5:
                status = "submitted"
            elif age < 15:
                status = random.choice(["under_review", "approved"])
            else:
                status = random.choices(["approved", "partially_approved", "rejected"], [.65, .2, .15])[0]
            approved = settled = reason = None
            if status in {"approved", "partially_approved", "rejected"}:
                settled = submitted + timedelta(days=random.randint(3, min(20, max(3, age))))
                if settled > self.now:
                    status, settled = "under_review", None
            if status == "approved":
                approved = claimed
            elif status == "partially_approved":
                approved = money(claimed * random.uniform(.6, .9))
            elif status == "rejected":
                approved, reason = 0.0, random.choice(REJECTION_REASONS)
            self.add("insurance_claims", claim_number=f"CLM-{self._ids['insurance_claims'] + 1:06d}", invoice_id=inv,
                     patient_insurance_id=ins["id"], claimed_amount=claimed, approved_amount=approved, status=status,
                     submitted_at=submitted, settled_at=settled, rejection_reason=reason)
            self.pay(inv, discharged + timedelta(hours=1), total - claimed)
            if approved:
                self.pay(inv, settled, approved, "insurance")
            if settled and approved is not None and approved < claimed and random.random() < .7:
                self.pay(inv, max(settled, paid_later), claimed - approved)
        else:
            r = random.random()
            if r < .85:
                self.pay(inv, discharged + timedelta(hours=1), total)
            elif r < .95:
                self.pay(inv, discharged + timedelta(hours=1), total * random.uniform(.5, .9))

    # ------------------------------------------------------------------ 6. pharmacy stock (per facility)
    def build_inventory(self):
        n = 0
        for code, f in self.fac.items():
            if f["profile"] == "diagnostic":
                continue
            for name, m in self.med.items():
                if f["profile"] == "small" and random.random() < .4:
                    continue
                for _ in range(2 if f["profile"] == "large" and random.random() < .5 else 1):
                    n += 1
                    bulk = m["form"] in {"tablet", "capsule"}
                    reorder = (200 if bulk else 15) // (1 if f["profile"] == "large" else 2)
                    qty = random.randint(0, reorder) if random.random() < .12 else random.randint(reorder + 1, reorder * 12)
                    exp = self.today + timedelta(days=random.randint(-20, 30) if random.random() < .08 else random.randint(31, 720))
                    self.add("pharmacy_inventory", facility_id=f["id"], medication_id=m["id"],
                             batch_number=f"{code}-B{self.today.year % 100}{n:05d}", quantity_on_hand=qty, reorder_level=reorder,
                             expiry_date=exp, supplier=random.choice(SUPPLIERS),
                             received_on=exp - timedelta(days=random.randint(540, 730)))

    # ------------------------------------------------------------------ 7. user accounts
    def build_users(self):
        pw = lambda: (lambda salt: f"sha256${salt}${hashlib.sha256((salt + DEMO_PASSWORD).encode()).hexdigest()}")(f"{random.getrandbits(32):08x}")
        taken = set()
        self.users, self.user_of_doctor, self.user_of_staff, self.user_of_patient = {}, {}, {}, {}
        hero_names = {self.hero_doc[h["key"]]: h["username"] for h in healthsetu.HERO_DOCTORS}

        def username(base):
            base = base.lower().replace(" ", "")
            u, k = base, 1
            while u in taken:
                k += 1
                u = f"{base}{k}"
            taken.add(u)
            return u

        for row in self.rows["doctors"]:
            uname = username(hero_names.get(row["id"], f"{row['first_name']}.{row['last_name']}"))
            fac = self.doctors[row["id"]]["fac"]
            uid = self.add("users", username=uname, password_hash=pw(), role_id=self.role_id["doctor"], doctor_id=row["id"],
                           staff_id=None, patient_id=None, facility_id=row["facility_id"], is_active=row["is_active"],
                           created_at=datetime.combine(row["joined_on"], time(10)), last_login_at=None)
            self.users[uid] = dict(role="doctor", shift="general", fac=fac, name=uname)
            self.user_of_doctor[row["id"]] = uid
        for row in self.rows["staff"]:
            fac = self.staff_info[row["id"]]["fac"]
            base = f"admin.{fac.lower()}" if row["role"] == "admin" else f"{row['first_name']}.{row['last_name']}"
            uid = self.add("users", username=username(base), password_hash=pw(), role_id=self.role_id[row["role"]],
                           doctor_id=None, staff_id=row["id"], patient_id=None, facility_id=row["facility_id"], is_active=True,
                           created_at=datetime.combine(row["joined_on"], time(10)), last_login_at=None)
            self.users[uid] = dict(role=row["role"], shift=row["shift"], fac=fac, name=self.rows["users"][-1]["username"])
            self.user_of_staff[row["id"]] = uid
        # patient accounts: every hero + ~25% of adults
        for row in self.rows["patients"]:
            p = self.patients[row["id"]]
            if not (p["hero"] or (p["age"] >= 18 and random.random() < .25)):
                continue
            uid = self.add("users", username=username(p.get("username") or row["patient_code"]), password_hash=pw(),
                           role_id=self.role_id["patient"], doctor_id=None, staff_id=None, patient_id=row["id"], facility_id=None,
                           is_active=True, created_at=row["registered_at"], last_login_at=None)
            self.users[uid] = dict(role="patient", shift="general", fac=None, name=self.rows["users"][-1]["username"])
            self.user_of_patient[row["id"]] = uid

    def staff_ip(self, uid: int) -> str:
        fac = self.users[uid]["fac"]
        return f"10.{self.fac[fac]['id']}.{uid % 250 + 1}.{(uid * 7) % 250 + 2}"

    def patient_ip(self, uid: int) -> str:
        return f"100.{64 + uid % 60}.{(uid * 13) % 250 + 1}.{(uid * 29) % 250 + 1}"   # carrier-grade NAT range, like mobile data

    # ------------------------------------------------------------------ 8. audit log
    def build_audit(self):
        count = lambda t: len(self.rows[t])
        role_actions = {
            "doctor": [("VIEW", "patients"), ("VIEW", "lab_results"), ("CREATE", "prescriptions"), ("CREATE", "diagnoses"), ("UPDATE", "appointments"), ("VIEW", "timeline_events")],
            "nurse": [("VIEW", "patients"), ("CREATE", "vitals"), ("VIEW", "prescriptions"), ("VIEW", "admissions")],
            "receptionist": [("CREATE", "appointments"), ("UPDATE", "appointments"), ("VIEW", "patients"), ("CREATE", "patients")],
            "lab_technician": [("VIEW", "lab_orders"), ("CREATE", "lab_results"), ("UPDATE", "lab_orders")],
            "pharmacist": [("VIEW", "prescriptions"), ("UPDATE", "pharmacy_inventory")],
            "billing": [("CREATE", "invoices"), ("CREATE", "payments"), ("VIEW", "invoices"), ("UPDATE", "insurance_claims")],
            "admin": [("VIEW", "audit_log"), ("VIEW", "users"), ("UPDATE", "staff"), ("CREATE", "bed_availability_reports")],
        }
        shift_start = {"morning": 7, "evening": 14, "night": 21, "general": 9}
        E = []   # (time, user, attempted, action, table, record, ip, details, patient, grant)
        day = self.start.date()
        while day <= self.today:
            for uid, u in self.users.items():
                if u["role"] == "patient":
                    if random.random() < .03:
                        t = datetime.combine(day, time(random.randint(7, 22), random.randint(0, 59)))
                        if t <= self.now:
                            pid = self.rows["users"][uid - 1]["patient_id"]
                            E.append((t, uid, None, "LOGIN", None, None, self.patient_ip(uid), None, None, None))
                            E.append((t + timedelta(minutes=2), uid, None, "VIEW", "timeline_events", None, self.patient_ip(uid), "Viewed own timeline", pid, None))
                    continue
                if uid == self.user_of_doctor.get(self.resigned_doctor) and datetime.combine(day, time()) >= self.doctors[self.resigned_doctor]["left"]:
                    continue
                if day.weekday() == 6 and u["role"] != "nurse":
                    continue
                if random.random() > .35:
                    continue
                t = datetime.combine(day, time(shift_start[u["shift"]])) + timedelta(minutes=random.randint(-20, 40))
                if t > self.now:
                    continue
                ip = self.staff_ip(uid)
                E.append((t, uid, None, "LOGIN", None, None, ip, None, None, None))
                for _ in range(random.randint(2, 8)):
                    t += timedelta(minutes=random.randint(3, 70))
                    act, table = random.choice(role_actions[u["role"]])
                    E.append((t, uid, None, act, table, random.randint(1, max(1, count(table))), ip, None, None, None))
                E.append((t + timedelta(minutes=random.randint(5, 60)), uid, None, "LOGOUT", None, None, ip, None, None, None))
            day += timedelta(days=1)

        uname = {r["id"]: r["username"] for r in self.rows["users"]}
        gvh = lambda role: next(uid for uid, u in self.users.items() if u["role"] == role and u["fac"] == "GVH"
                                and (role != "nurse" or u["shift"] == "morning"))
        npat = count("patients")
        # Anomaly 1: day-shift nurse mass-viewing patient records at 1 AM from an outside IP, then exporting
        nurse = gvh("nurse")
        t = datetime.combine(self.today - timedelta(days=12), time(1, 7))
        E.append((t, nurse, None, "LOGIN", None, None, "203.0.113.45", "Login from external network", None, None))
        for pid in random.sample(range(3, npat + 1), min(280, npat - 2)):
            t += timedelta(seconds=random.randint(8, 25))
            E.append((t, nurse, None, "VIEW", "patients", pid, "203.0.113.45", None, pid, None))
        E.append((t + timedelta(minutes=2), nurse, None, "EXPORT", "patients", None, "203.0.113.45", "Exported 280 patient records to CSV", None, None))
        # Anomaly 2: brute force on the Ganga View admin, success, privilege change, attempt to wipe logs
        admin = next(uid for uid, u in self.users.items() if u["name"] == "admin.gvh")
        t = datetime.combine(self.today - timedelta(days=5), time(3, 12))
        for _ in range(40):
            t += timedelta(seconds=random.randint(4, 15))
            E.append((t, None, uname[admin], "LOGIN_FAILED", None, None, "198.51.100.23", "Invalid password", None, None))
        t += timedelta(seconds=20)
        E.append((t, admin, None, "LOGIN", None, None, "198.51.100.23", None, None, None))
        victim = gvh("receptionist")
        E.append((t + timedelta(minutes=3), admin, None, "UPDATE", "users", victim, "198.51.100.23",
                  f"Role of user '{uname[victim]}' changed from receptionist to admin", None, None))
        E.append((t + timedelta(minutes=6), admin, None, "DELETE", "audit_log", None, "198.51.100.23",
                  "Attempted bulk delete of audit_log entries (blocked)", None, None))
        # Anomaly 3: that receptionist browsing lab results (outside their role)
        for k in range(60):
            t = datetime.combine(self.today - timedelta(days=3 - k // 20), time(10)) + timedelta(minutes=random.randint(0, 420))
            E.append((t, victim, None, "VIEW", "lab_results", random.randint(1, max(1, count("lab_results"))), self.staff_ip(victim), None, None, None))
        # Anomaly 4: the resigned doctor's deactivated account logs in
        ru = self.user_of_doctor[self.resigned_doctor]
        t = datetime.combine(self.today - timedelta(days=8), time(22, 41))
        E.append((t, ru, None, "LOGIN", None, None, "203.0.113.77", "Login by deactivated account", None, None))
        pid = random.randint(3, npat)
        E.append((t + timedelta(minutes=4), ru, None, "VIEW", "patients", pid, "203.0.113.77", None, pid, None))

        E += self.extra_events
        E.sort(key=lambda e: e[0])
        last_login = {}
        for t, uid, attempted, act, table, rec, ip, details, pid, grant in E:
            self.add("audit_log", user_id=uid, username_attempted=attempted, action=act, table_name=table, record_id=rec,
                     patient_id=pid, consent_grant_id=grant, ip_address=ip, occurred_at=t, details=details)
            if act == "LOGIN" and uid:
                last_login[uid] = t
        for row in self.rows["users"]:
            row["last_login_at"] = last_login.get(row["id"])

    # ------------------------------------------------------------------ finishing touches
    def fix_registration_dates(self):
        for row in self.rows["patients"]:
            first = self.first_event.get(row["id"])
            if first and row["registered_at"] > first:
                row["registered_at"] = first - timedelta(days=random.randint(0, 20), minutes=random.randint(10, 300))
        for row in self.rows["users"]:          # patient accounts can't predate registration
            if row["patient_id"]:
                row["created_at"] = max(row["created_at"], self.rows["patients"][row["patient_id"] - 1]["registered_at"])

    def fix_invoice_status(self):
        paid = defaultdict(float)
        for p in self.rows["payments"]:
            paid[p["invoice_id"]] += p["amount"]
        pending = {c["invoice_id"] for c in self.rows["insurance_claims"] if c["status"] in {"submitted", "under_review"}}
        for inv in self.rows["invoices"]:
            got = paid[inv["id"]]
            inv["status"] = ("paid" if got >= inv["total_amount"] - 0.01 else "insurance_pending" if inv["id"] in pending
                             else "partially_paid" if got > 0 else "unpaid")

    def build(self):
        steps = [("reference data", self.build_reference), ("wards & beds", self.build_facility), ("people", self.build_people),
                 ("appointments", self.build_appointments), ("admissions", self.build_admissions),
                 ("hero patients", lambda: healthsetu.build_hero_records(self)), ("pharmacy stock", self.build_inventory),
                 ("user accounts", self.build_users),
                 ("documents (images)", lambda: healthsetu.build_documents(self)),
                 ("consent", lambda: healthsetu.build_consents(self)),
                 ("bed availability", lambda: healthsetu.build_availability(self)),
                 ("audit log", self.build_audit)]
        for label, fn in steps:
            t0 = clock.time()
            fn()
            print(f"  generated {label:<22} ({clock.time() - t0:.1f}s)")
        self.fix_registration_dates()
        self.fix_invoice_status()
        return self.rows


# =============================================================================
#  LOADING
# =============================================================================
INSERT_ORDER = ["roles", "departments", "facilities", "facility_services", "icd10_codes", "lab_tests", "medications",
                "drug_interactions", "drug_condition_cautions", "insurance_providers", "doctors", "staff", "patients",
                "patient_allergies", "patient_insurance", "wards", "beds", "appointments", "admissions", "diagnoses", "vitals",
                "prescriptions", "prescription_items", "pharmacy_inventory", "lab_orders", "lab_results", "invoices",
                "invoice_items", "payments", "insurance_claims", "users", "documents", "document_extractions",
                "consent_requests", "consent_grants", "bed_availability_reports", "audit_log"]


def clean(v):
    if isinstance(v, datetime):
        return v.replace(microsecond=0)
    if isinstance(v, dict):
        return Json(v)
    return v


def load(rows, args):
    conn = psycopg2.connect(args.database_url)
    try:
        with conn, conn.cursor() as cur:
            cur.execute((HERE / "db" / "schema.sql").read_text())
            for table in INSERT_ORDER:
                data = rows.get(table, [])
                if not data:
                    continue
                cols = list(data[0].keys())
                execute_values(cur, f"INSERT INTO {table} ({', '.join(cols)}) VALUES %s",
                               [tuple(clean(r.get(c)) for c in cols) for r in data], page_size=5000)
                if "id" in cols:
                    cur.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), (SELECT MAX(id) FROM {table}))")
                print(f"  loaded {table:<26} {len(data):>8,} rows")
            cur.execute((HERE / "db" / "timeline_backfill.sql").read_text())
            cur.execute("SELECT count(*) FROM timeline_events")
            print(f"  built  {'timeline_events':<26} {cur.fetchone()[0]:>8,} rows")
            cur.execute((HERE / "db" / "functions.sql").read_text())
            print("  created views & functions")
        if args.export_csv:
            out = Path(args.export_csv)
            out.mkdir(parents=True, exist_ok=True)
            with conn.cursor() as cur:
                for table in INSERT_ORDER + ["timeline_events"]:
                    with open(out / f"{table}.csv", "w", encoding="utf-8", newline="") as f:
                        cur.copy_expert(f"COPY {table} TO STDOUT WITH CSV HEADER", f)
            print(f"  exported CSVs to {out.resolve()}")
        with conn.cursor() as cur:
            cur.execute("SELECT SUM(occupied_beds), SUM(total_beds) FROM v_current_bed_occupancy")
            occ, beds = cur.fetchone()
            print(f"\nDone. Network bed occupancy right now: {occ}/{beds} ({100 * occ / beds:.0f}%).")
    finally:
        conn.close()


def main():
    ap = argparse.ArgumentParser(description="Seed the Health Setu demo database with synthetic data.")
    ap.add_argument("--database-url", default=os.getenv("DATABASE_URL", "postgresql://hospital:hospital@localhost:5432/health_setu"))
    ap.add_argument("--patients", type=int, default=15000)
    ap.add_argument("--appointments", type=int, default=10000)
    ap.add_argument("--history-days", type=int, default=180, help="how far back the data goes")
    ap.add_argument("--documents", type=int, default=40, help="patients who uploaded outside documents (images are generated)")
    ap.add_argument("--storage-dir", default=os.getenv("STORAGE_DIR", str(HERE / "storage")), help="where document images go")
    ap.add_argument("--anchor-date", help="treat this date (YYYY-MM-DD) as 'today' (default: real today)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--export-csv", metavar="DIR", help="also write every table to DIR/<table>.csv")
    args = ap.parse_args()
    random.seed(args.seed)
    Faker.seed(args.seed)
    args.db_now = None
    if not args.anchor_date:     # use the database's clock (the seeder may run in a container with another timezone)
        try:
            with psycopg2.connect(args.database_url) as conn, conn.cursor() as cur:
                cur.execute("SELECT localtimestamp(0)")
                args.db_now = cur.fetchone()[0]
        except psycopg2.OperationalError as e:
            sys.exit(f"Cannot reach the database at {args.database_url}\n{e}")
    print(f"Generating Health Setu synthetic data (seed={args.seed})...")
    rows = Generator(args).build()
    print("Loading into PostgreSQL...")
    load(rows, args)


if __name__ == "__main__":
    main()
