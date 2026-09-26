"""
reference.py - static reference data for the Health Setu synthetic dataset.

Everything here is DEMO data. The drug-interaction and drug-condition lists are a small,
simplified teaching set so the demo has realistic flags. They are NOT a clinical reference
and must never be used for real prescribing decisions.
"""
from __future__ import annotations

ROLES = [
    ("admin", "Full system access"),
    ("doctor", "Clinical records, prescriptions, lab orders"),
    ("nurse", "Ward care, vitals, medication administration"),
    ("receptionist", "Registration and appointments"),
    ("lab_technician", "Lab orders and results"),
    ("pharmacist", "Dispensing and pharmacy inventory"),
    ("billing", "Invoices, payments, insurance claims"),
    ("patient", "Own records, uploads, consent decisions"),
]

# code, name, floor, doctor specialization, qualification, (fee min, fee max)
DEPARTMENTS = [
    ("GM",  "General Medicine",          1, "General Physician",           "MBBS, MD (Medicine)",              (400, 800)),
    ("CAR", "Cardiology",                2, "Cardiologist",                "MBBS, MD, DM (Cardiology)",        (900, 1500)),
    ("ORT", "Orthopaedics",              4, "Orthopaedic Surgeon",         "MBBS, MS (Orthopaedics)",          (700, 1200)),
    ("PED", "Paediatrics",               3, "Paediatrician",               "MBBS, MD (Paediatrics)",           (500, 900)),
    ("OBG", "Obstetrics & Gynaecology",  3, "Obstetrician & Gynaecologist", "MBBS, MS (OBG)",                  (600, 1000)),
    ("NEU", "Neurology",                 5, "Neurologist",                 "MBBS, MD, DM (Neurology)",         (900, 1500)),
    ("PUL", "Pulmonology",               2, "Pulmonologist",               "MBBS, MD (Pulmonary Medicine)",    (700, 1200)),
    ("NEP", "Nephrology",                5, "Nephrologist",                "MBBS, MD, DM (Nephrology)",        (900, 1500)),
    ("GAS", "Gastroenterology",          2, "Gastroenterologist",          "MBBS, MD, DM (Gastroenterology)",  (900, 1400)),
    ("END", "Endocrinology",             2, "Endocrinologist",             "MBBS, MD, DM (Endocrinology)",     (800, 1300)),
    ("DER", "Dermatology",               1, "Dermatologist",               "MBBS, MD (Dermatology)",           (500, 900)),
    ("ENT", "ENT",                       1, "ENT Surgeon",                 "MBBS, MS (ENT)",                   (500, 900)),
    ("GS",  "General Surgery",           4, "General Surgeon",             "MBBS, MS (General Surgery)",       (600, 1100)),
    ("EMR", "Emergency Medicine",        0, "Emergency Physician",         "MBBS, MD (Emergency Medicine)",    (500, 800)),
]

# code, description, department, min_age, max_age, sex (None = any), chronic
ICD10 = [
    ("I10",   "Essential (primary) hypertension",                         "CAR", 30, 110, None, True),
    ("I21.9", "Acute myocardial infarction, unspecified",                 "CAR", 35, 110, None, False),
    ("I50.9", "Heart failure, unspecified",                               "CAR", 45, 110, None, False),
    ("R07.4", "Chest pain, unspecified",                                  "EMR", 18, 110, None, False),
    ("E11.9", "Type 2 diabetes mellitus without complications",           "END", 25, 110, None, True),
    ("E03.9", "Hypothyroidism, unspecified",                              "END", 12, 110, None, True),
    ("J18.9", "Pneumonia, unspecified organism",                          "PUL",  0, 110, None, False),
    ("J45.9", "Asthma, unspecified",                                      "PUL",  4, 110, None, True),
    ("J44.9", "Chronic obstructive pulmonary disease, unspecified",       "PUL", 40, 110, None, True),
    ("J06.9", "Acute upper respiratory infection, unspecified",           "PED",  0,  12, None, False),
    ("P59.9", "Neonatal jaundice, unspecified",                           "PED",  0,   0, None, False),
    ("A09",   "Infectious gastroenteritis and colitis",                   "GAS",  0, 110, None, False),
    ("K29.7", "Gastritis, unspecified",                                   "GAS", 12, 110, None, False),
    ("K35.8", "Acute appendicitis, other and unspecified",                "GS",   5,  80, None, False),
    ("K80.2", "Calculus of gallbladder without cholecystitis",            "GS",  25,  90, None, False),
    ("K40.9", "Unilateral inguinal hernia, without obstruction or gangrene", "GS", 18, 90, None, False),
    ("A90",   "Dengue fever [classical dengue]",                          "GM",   2, 110, None, False),
    ("A01.0", "Typhoid fever",                                            "GM",   2, 110, None, False),
    ("B54",   "Unspecified malaria",                                      "GM",   1, 110, None, False),
    ("R50.9", "Fever, unspecified",                                       "GM",   0, 110, None, False),
    ("S72.0", "Fracture of neck of femur",                                "ORT", 55, 110, None, False),
    ("S52.5", "Fracture of lower end of radius",                          "ORT",  5, 110, None, False),
    ("M17.9", "Gonarthrosis [arthrosis of knee], unspecified",            "ORT", 45, 110, None, True),
    ("M54.5", "Low back pain",                                            "ORT", 18, 110, None, False),
    ("G43.9", "Migraine, unspecified",                                    "NEU", 12,  70, None, False),
    ("I63.9", "Cerebral infarction, unspecified",                         "NEU", 45, 110, None, False),
    ("G40.9", "Epilepsy, unspecified",                                    "NEU",  2, 110, None, True),
    ("N18.9", "Chronic kidney disease, unspecified",                      "NEP", 35, 110, None, True),
    ("N39.0", "Urinary tract infection, site not specified",              "NEP",  2, 110, None, False),
    ("L20.9", "Atopic dermatitis, unspecified",                           "DER",  0, 110, None, False),
    ("B35.4", "Tinea corporis",                                           "DER",  5, 110, None, False),
    ("H66.9", "Otitis media, unspecified",                                "ENT",  1, 110, None, False),
    ("J03.9", "Acute tonsillitis, unspecified",                           "ENT",  3,  60, None, False),
    ("Z34.9", "Supervision of normal pregnancy, unspecified",             "OBG", 18,  42, "F",  False),
    ("N92.0", "Excessive and frequent menstruation with regular cycle",   "OBG", 13,  50, "F",  False),
    ("O80",   "Single spontaneous delivery",                              "OBG", 18,  42, "F",  False),
    ("O82",   "Single delivery by caesarean section",                     "OBG", 18,  42, "F",  False),
    ("T14.9", "Injury, unspecified",                                      "EMR",  0, 110, None, False),
]
INPATIENT_ONLY = {"O80", "O82", "I21.9", "I63.9", "S72.0", "K35.8"}

# chronic condition prevalence: code -> (min_age, probability)
CHRONIC_PREVALENCE = {"I10": (35, .25), "E11.9": (30, .12), "E03.9": (15, .06), "J45.9": (5, .05),
                      "J44.9": (45, .04), "M17.9": (50, .15), "N18.9": (45, .03), "G40.9": (2, .01)}

# code, name, category, unit, normal_min, normal_max, price, decimals, (high mult range), (low mult range)
LAB_TESTS = [
    ("HB",    "Haemoglobin",               "Haematology", "g/dL",      12.0, 17.0,  100, 1, (1.05, 1.15), (0.50, 0.90)),
    ("WBC",   "Total leucocyte count",     "Haematology", "10^3/uL",    4.0, 11.0,  120, 1, (1.10, 2.50), (0.40, 0.90)),
    ("PLT",   "Platelet count",            "Haematology", "10^3/uL",  150.0, 450.0, 150, 0, (1.05, 1.30), (0.10, 0.80)),
    ("FBS",   "Fasting blood sugar",       "Biochemistry", "mg/dL",    70.0, 100.0,  80, 0, (1.20, 3.00), (0.60, 0.90)),
    ("HBA1C", "HbA1c",                     "Biochemistry", "%",         4.0,   5.6, 450, 1, (1.15, 2.00), (0.90, 0.98)),
    ("CREAT", "Serum creatinine",          "Renal",       "mg/dL",      0.6,   1.3, 180, 2, (1.30, 6.00), (0.60, 0.95)),
    ("UREA",  "Blood urea",                "Renal",       "mg/dL",     15.0,  40.0, 150, 0, (1.20, 4.00), (0.60, 0.95)),
    ("NA",    "Serum sodium",              "Electrolytes", "mmol/L",  135.0, 145.0, 200, 0, (1.02, 1.06), (0.85, 0.97)),
    ("K",     "Serum potassium",           "Electrolytes", "mmol/L",    3.5,   5.1, 200, 1, (1.05, 1.35), (0.75, 0.95)),
    ("SGPT",  "SGPT (ALT)",                "Liver",       "U/L",        7.0,  56.0, 200, 0, (1.20, 4.00), (0.50, 0.90)),
    ("BILI",  "Total bilirubin",           "Liver",       "mg/dL",      0.1,   1.2, 180, 1, (1.30, 8.00), (0.50, 0.90)),
    ("TSH",   "Thyroid stimulating hormone", "Endocrine", "mIU/L",      0.4,   4.0, 350, 2, (1.30, 5.00), (0.20, 0.90)),
    ("CHOL",  "Total cholesterol",         "Lipid",       "mg/dL",    125.0, 200.0, 250, 0, (1.05, 1.50), (0.80, 0.95)),
    ("CRP",   "C-reactive protein",        "Immunology",  "mg/L",       0.0,  10.0, 400, 1, (1.50, 15.0), None),
    ("TROP",  "Troponin I",                "Cardiac",     "ng/mL",      0.0,  0.04, 900, 3, (2.00, 80.0), None),
]
# which tests a department orders by default
DEPT_PANEL = {"GM": ["HB", "WBC", "PLT", "FBS"], "CAR": ["CHOL", "TROP", "NA", "K"], "END": ["FBS", "HBA1C", "TSH"],
              "NEP": ["CREAT", "UREA", "NA", "K"], "GAS": ["SGPT", "BILI", "HB"], "PUL": ["WBC", "CRP", "HB"],
              "NEU": ["NA", "FBS", "CHOL"], "ORT": ["HB", "CRP"], "PED": ["HB", "WBC", "PLT"], "OBG": ["HB", "PLT", "FBS"],
              "GS": ["HB", "WBC", "CRP"], "EMR": ["HB", "WBC", "TROP", "FBS"], "DER": ["HB"], "ENT": ["WBC", "CRP"]}
# condition -> tests that will usually be abnormal (so the data "makes sense" to an AI / analyst)
LAB_BIAS = {"E11": {"FBS": "high", "HBA1C": "high"}, "N18": {"CREAT": "high", "UREA": "high", "K": "high"},
            "A90": {"PLT": "low", "WBC": "low"}, "I21": {"TROP": "high", "CHOL": "high"}, "E03": {"TSH": "high"},
            "J18": {"WBC": "high", "CRP": "high"}, "N39": {"WBC": "high", "CRP": "high"}, "A01": {"CRP": "high"},
            "B54": {"PLT": "low", "HB": "low"}, "K80": {"BILI": "high", "SGPT": "high"}, "K35": {"WBC": "high", "CRP": "high"},
            "I63": {"CHOL": "high"}, "N92": {"HB": "low"}, "P59": {"BILI": "high"}, "I50": {"NA": "low"}}

# name, generic, form, strength, unit price (INR), frequency, doses/day
MEDICATIONS = [
    ("Paracetamol 650 mg Tablet",              "Paracetamol",               "tablet",    "650 mg",         2.0, "1-1-1", 3),
    ("Paracetamol 120 mg/5 mL Syrup",          "Paracetamol",               "syrup",     "120 mg/5 mL",   40.0, "5 mL TDS", 3),
    ("Pantoprazole 40 mg Tablet",              "Pantoprazole",              "tablet",    "40 mg",          6.0, "1-0-0 (before breakfast)", 1),
    ("Amoxicillin-Clavulanate 625 mg Tablet",  "Amoxicillin + Clavulanic acid", "tablet", "625 mg",       18.0, "1-0-1", 2),
    ("Amoxicillin 250 mg/5 mL Syrup",          "Amoxicillin",               "syrup",     "250 mg/5 mL",   70.0, "5 mL TDS", 3),
    ("Azithromycin 500 mg Tablet",             "Azithromycin",              "tablet",    "500 mg",        22.0, "1-0-0", 1),
    ("Ceftriaxone 1 g Injection",              "Ceftriaxone",               "injection", "1 g",           55.0, "IV BD", 2),
    ("Metformin 500 mg Tablet",                "Metformin",                 "tablet",    "500 mg",         2.5, "1-0-1 (after food)", 2),
    ("Glimepiride 2 mg Tablet",                "Glimepiride",               "tablet",    "2 mg",           5.0, "1-0-0", 1),
    ("Insulin Glargine 100 IU/mL Injection",   "Insulin glargine",          "injection", "100 IU/mL",    650.0, "10 IU SC at night", 1),
    ("Amlodipine 5 mg Tablet",                 "Amlodipine",                "tablet",    "5 mg",           3.0, "1-0-0", 1),
    ("Telmisartan 40 mg Tablet",               "Telmisartan",               "tablet",    "40 mg",          6.0, "1-0-0", 1),
    ("Atorvastatin 20 mg Tablet",              "Atorvastatin",              "tablet",    "20 mg",          8.0, "0-0-1", 1),
    ("Aspirin 75 mg Tablet",                   "Aspirin",                   "tablet",    "75 mg",          1.5, "0-1-0 (after lunch)", 1),
    ("Clopidogrel 75 mg Tablet",               "Clopidogrel",               "tablet",    "75 mg",          7.0, "0-1-0", 1),
    ("Furosemide 40 mg Tablet",                "Furosemide",                "tablet",    "40 mg",          2.0, "1-0-0", 1),
    ("Levothyroxine 50 mcg Tablet",            "Levothyroxine",             "tablet",    "50 mcg",         1.8, "1-0-0 (empty stomach)", 1),
    ("Salbutamol 100 mcg Inhaler",             "Salbutamol",                "inhaler",   "100 mcg/dose", 180.0, "2 puffs SOS", 1),
    ("Budesonide-Formoterol Inhaler",          "Budesonide + Formoterol",   "inhaler",   "200/6 mcg",    450.0, "2 puffs BD", 2),
    ("Montelukast 10 mg Tablet",               "Montelukast",               "tablet",    "10 mg",         12.0, "0-0-1", 1),
    ("Ondansetron 4 mg Tablet",                "Ondansetron",               "tablet",    "4 mg",           5.0, "1-0-1 (SOS vomiting)", 2),
    ("ORS Sachet",                             "Oral rehydration salts",    "sachet",    "21 g",          20.0, "after each loose stool", 3),
    ("Metronidazole 400 mg Tablet",            "Metronidazole",             "tablet",    "400 mg",         2.0, "1-1-1", 3),
    ("Ofloxacin 200 mg Tablet",                "Ofloxacin",                 "tablet",    "200 mg",         6.0, "1-0-1", 2),
    ("Nitrofurantoin 100 mg Capsule",          "Nitrofurantoin",            "capsule",   "100 mg",         9.0, "1-0-1", 2),
    ("Artemether-Lumefantrine 80/480 Tablet",  "Artemether + Lumefantrine", "tablet",    "80/480 mg",     30.0, "1-0-1", 2),
    ("Levetiracetam 500 mg Tablet",            "Levetiracetam",             "tablet",    "500 mg",        14.0, "1-0-1", 2),
    ("Sumatriptan 50 mg Tablet",               "Sumatriptan",               "tablet",    "50 mg",         45.0, "SOS (max 2/day)", 1),
    ("Diclofenac 50 mg Tablet",                "Diclofenac",                "tablet",    "50 mg",          2.0, "1-0-1 (after food)", 2),
    ("Calcium + Vitamin D3 Tablet",            "Calcium carbonate + Cholecalciferol", "tablet", "500 mg/250 IU", 6.0, "0-1-0", 1),
    ("Tramadol 50 mg Tablet",                  "Tramadol",                  "tablet",    "50 mg",          8.0, "1-0-1 (SOS pain)", 2),
    ("Cetirizine 10 mg Tablet",                "Cetirizine",                "tablet",    "10 mg",          2.0, "0-0-1", 1),
    ("Clotrimazole 1% Cream",                  "Clotrimazole",              "cream",     "1% w/w",        65.0, "apply BD", 2),
    ("Mometasone 0.1% Cream",                  "Mometasone",                "cream",     "0.1% w/w",     120.0, "apply OD", 1),
    ("Ferrous Sulphate + Folic Acid Tablet",   "Ferrous sulphate + Folic acid", "tablet", "100 mg/0.5 mg", 1.5, "0-1-0", 1),
    ("Oxytocin 5 IU Injection",                "Oxytocin",                  "injection", "5 IU/mL",       30.0, "as per protocol", 1),
    ("Tranexamic Acid 500 mg Tablet",          "Tranexamic acid",           "tablet",    "500 mg",        15.0, "1-1-1 (during bleeding)", 3),
    ("Normal Saline 0.9% 500 mL",              "Sodium chloride 0.9%",      "iv_fluid",  "500 mL",        35.0, "IV 8-hourly", 3),
]
M: dict[str, str] = {}                                # quick aliases, e.g. M["Metformin"]; first listed form wins
for _m in MEDICATIONS:
    M.setdefault(_m[0].split()[0], _m[0])
CONDITION_MEDS = {
    "I10": ["Amlodipine", "Telmisartan"], "I21": ["Aspirin", "Clopidogrel", "Atorvastatin"],
    "I50": ["Furosemide", "Telmisartan"], "E11": ["Metformin", "Glimepiride", "Insulin"], "E03": ["Levothyroxine"],
    "J18": ["Amoxicillin-Clavulanate", "Azithromycin", "Ceftriaxone", "Paracetamol"],
    "J45": ["Salbutamol", "Budesonide-Formoterol", "Montelukast"], "J44": ["Budesonide-Formoterol", "Salbutamol"],
    "A09": ["ORS", "Ondansetron", "Metronidazole"], "K29": ["Pantoprazole", "Ondansetron"],
    "K35": ["Ceftriaxone", "Metronidazole", "Tramadol", "Pantoprazole"], "K80": ["Ceftriaxone", "Tramadol", "Pantoprazole"],
    "K40": ["Tramadol", "Pantoprazole", "Amoxicillin-Clavulanate"], "A90": ["Paracetamol", "Normal", "ORS"],
    "A01": ["Ceftriaxone", "Ofloxacin", "Paracetamol"], "B54": ["Artemether-Lumefantrine", "Paracetamol"],
    "R50": ["Paracetamol"], "S72": ["Tramadol", "Calcium", "Pantoprazole"], "S52": ["Diclofenac", "Calcium"],
    "M17": ["Diclofenac", "Calcium", "Pantoprazole"], "M54": ["Diclofenac", "Pantoprazole"],
    "G43": ["Sumatriptan", "Paracetamol"], "I63": ["Aspirin", "Atorvastatin", "Clopidogrel"], "G40": ["Levetiracetam"],
    "N18": ["Furosemide", "Ferrous"], "N39": ["Nitrofurantoin", "Paracetamol"], "L20": ["Mometasone", "Cetirizine"],
    "B35": ["Clotrimazole", "Cetirizine"], "H66": ["Amoxicillin-Clavulanate", "Paracetamol"],
    "J03": ["Amoxicillin-Clavulanate", "Paracetamol"], "J06": ["Paracetamol", "Cetirizine"],
    "O80": ["Oxytocin", "Ferrous", "Paracetamol"], "O82": ["Ceftriaxone", "Tramadol", "Ferrous"],
    "N92": ["Tranexamic", "Ferrous"], "Z34": ["Ferrous", "Calcium"], "T14": ["Tramadol", "Diclofenac"],
    "R07": ["Aspirin", "Pantoprazole"], "P59": [],
}
CHILD_SWAP = {"Paracetamol": "Paracetamol 120 mg/5 mL Syrup", "Amoxicillin-Clavulanate": "Amoxicillin 250 mg/5 mL Syrup"}
CHILD_SAFE = {"ORS", "Ondansetron", "Cetirizine", "Salbutamol", "Budesonide-Formoterol", "Montelukast", "Ceftriaxone",
              "Normal", "Artemether-Lumefantrine", "Levetiracetam", "Mometasone", "Clotrimazole", "Metronidazole", "Azithromycin"}

PROCEDURES = {"K35.8": ("Laparoscopic appendectomy", 55000), "K80.2": ("Laparoscopic cholecystectomy", 65000),
              "K40.9": ("Inguinal hernia repair with mesh", 45000), "S72.0": ("Hip hemiarthroplasty", 160000),
              "S52.5": ("Closed reduction and cast application", 12000), "M17.9": ("Total knee replacement", 220000),
              "O80": ("Normal vaginal delivery", 25000), "O82": ("Caesarean section", 55000),
              "I21.9": ("Coronary angioplasty (PTCA) with stent", 185000)}

INSURERS = [("Star Health", "private"), ("HDFC ERGO", "private"), ("ICICI Lombard", "private"), ("Niva Bupa", "private"),
            ("Care Health", "private"), ("New India Assurance", "public"), ("Ayushman Bharat PM-JAY", "public"),
            ("CGHS", "public")]
SUPPLIERS = ["MedLine Distributors", "Bengal Pharma Traders", "Eastern Surgicals & Drugs", "CureWell Wholesale",
             "Apex Healthcare Supply"]

GENERAL = ["J18.9", "A90", "A01.0", "B54", "A09", "N39.0", "G40.9", "I63.9", "E11.9", "N18.9", "J44.9", "J45.9", "I50.9", "K29.7"]
# name, type, dept, floor, beds, daily rate, (stay min, max, mode days), sex, (age min, max), target occupancy, allowed codes
WARDS = [
    ("General Ward (Male)",        "general",   "GM",  2, 20,  800, (2, 8, 3),     "M",  (13, 110), .82, GENERAL),
    ("General Ward (Female)",      "general",   "GM",  2, 20,  800, (2, 8, 3),     "F",  (13, 110), .80, GENERAL),
    ("Paediatric Ward",            "pediatric", "PED", 3, 10, 1200, (1, 6, 3),     None, (0, 12),   .70, ["P59.9", "J06.9", "A09", "J18.9", "A90", "B54", "R50.9", "J45.9"]),
    ("Maternity Ward",             "maternity", "OBG", 3,  6, 1500, (2, 5, 3),     "F",  (18, 42),  .60, ["O80", "O80", "O82"]),
    ("Surgical Ward",              "general",   "GS",  4, 12, 1000, (2, 9, 4),     None, (13, 110), .78, ["K35.8", "K80.2", "K40.9"]),
    ("Orthopaedic Ward",           "general",   "ORT", 4,  8, 1000, (3, 12, 5),    None, (5, 110),  .75, ["S72.0", "S52.5", "M17.9"]),
    ("Intensive Care Unit (ICU)",  "icu",       "GM",  5,  8, 6000, (2, 12, 4),    None, (13, 110), .88, ["I63.9", "J18.9", "J44.9", "N18.9", "A90", "T14.9"]),
    ("Cardiac Care Unit (CCU)",    "icu",       "CAR", 5,  6, 6500, (2, 9, 4),     None, (35, 110), .85, ["I21.9", "I21.9", "I50.9"]),
    ("Emergency Observation",      "emergency", "EMR", 0,  6, 1500, (0.3, 2, 0.8), None, (0, 110),  .70, ["R07.4", "T14.9", "A09", "R50.9"]),
    ("Private Rooms",              "private",   None,  6,  8, 3500, (2, 9, 4),     None, (18, 110), .60, GENERAL + ["K35.8", "K80.2", "M17.9", "I50.9"]),
]

FEVER = {"A90", "A01", "B54", "R50", "J18", "N39"}
RESP = {"J18", "J44", "J45"}
REJECTION_REASONS = ["Pre-existing condition not disclosed at policy purchase", "Initial waiting period not completed",
                     "Treatment not covered under policy terms", "Incomplete documentation submitted"]
DEMO_PASSWORD = "demo@123"




def prefix(code: str) -> str:
    return code.split(".")[0]


# =============================================================================
#  HEALTH SETU NETWORK
# =============================================================================
# Fictional facilities. Any resemblance to a real hospital name is unintended.
# code, name, facility_type, ownership, profile, locality, city, region, pincode, lat, lon, 24x7 emergency, extra departments
FACILITIES = [
    ("GVH", "Ganga View Multispeciality Hospital",    "multispeciality_hospital", "private",    "large",      "Park Circus",            "Kolkata",     "KOL", "700017", 22.5390, 88.3700, True,  []),
    ("EHI", "Eastern Heart & Multispeciality Institute", "multispeciality_hospital", "private", "medium",     "EM Bypass, Mukundapur",  "Kolkata",     "KOL", "700099", 22.4960, 88.4010, True,  ["NEU", "NEP"]),
    ("RSH", "Rajarhat Sanjeevani Hospital",           "multispeciality_hospital", "private",    "medium",     "Action Area II, New Town", "New Town",  "KOL", "700156", 22.5810, 88.4730, True,  ["NEP", "GAS", "END"]),
    ("HJH", "Howrah Janaseva Hospital",               "general_hospital",         "trust",      "medium",     "Shibpur",                "Howrah",      "KOL", "711102", 22.5700, 88.3150, True,  ["END"]),
    ("BSN", "Barasat Suraksha Nursing Home",          "nursing_home",             "private",    "small",      "Champadali More",        "Barasat",     "KOL", "700124", 22.7230, 88.4810, False, []),
    ("SGH", "Sundarban Gateway Government Hospital",  "government_hospital",      "government", "medium",     "Station Road",           "Baruipur",    "KOL", "700144", 22.3570, 88.4320, True,  []),
    ("DSH", "Durgapur Steel City Hospital",           "multispeciality_hospital", "private",    "medium",     "City Centre",            "Durgapur",    "DGP", "713216", 23.5370, 87.3050, True,  ["NEU"]),
    ("SHH", "Siliguri Hillview Hospital",             "multispeciality_hospital", "private",    "medium",     "Sevoke Road",            "Siliguri",    "SLG", "734001", 26.7270, 88.4280, True,  ["END"]),
    ("SPD", "Salt Lake Precision Diagnostics",        "diagnostic_centre",        "private",    "diagnostic", "Sector V, Salt Lake",    "Bidhannagar", "KOL", "700091", 22.5760, 88.4330, False, []),
]

PROFILE_DEPTS = {
    "large": [d[0] for d in DEPARTMENTS],
    "medium": ["GM", "CAR", "ORT", "PED", "OBG", "GS", "EMR", "PUL"],
    "small": ["GM", "OBG", "PED", "GS"],
    "diagnostic": [],
}
# ward names (from WARDS) per profile, and a bed-count scale factor
PROFILE_WARDS = {
    "large": ([w[0] for w in WARDS], 1.0),
    "medium": (["General Ward (Male)", "General Ward (Female)", "Paediatric Ward", "Maternity Ward", "Surgical Ward",
                "Intensive Care Unit (ICU)", "Cardiac Care Unit (CCU)", "Emergency Observation", "Private Rooms"], .35),
    "small": (["General Ward (Male)", "General Ward (Female)", "Maternity Ward"], .3),
    "diagnostic": ([], 0),
}

SERVICES = ["24x7 Emergency", "ICU", "NICU", "Cath Lab", "Dialysis", "CT Scan", "MRI", "X-Ray", "Ultrasound",
            "Blood Bank", "Ambulance", "Pharmacy (24x7)", "Pathology Lab", "Labour Room", "Operation Theatre"]
PROFILE_SERVICES = {
    "large": SERVICES,
    "medium": ["24x7 Emergency", "ICU", "CT Scan", "X-Ray", "Ultrasound", "Blood Bank", "Ambulance", "Pharmacy (24x7)",
               "Pathology Lab", "Labour Room", "Operation Theatre"],
    "small": ["X-Ray", "Ultrasound", "Ambulance", "Pharmacy (24x7)", "Pathology Lab", "Labour Room", "Operation Theatre"],
    "diagnostic": ["CT Scan", "MRI", "X-Ray", "Ultrasound", "Pathology Lab"],
}
EXTRA_SERVICES = {"EHI": ["Cath Lab", "MRI", "Dialysis"], "RSH": ["Dialysis", "MRI"], "DSH": ["MRI", "Cath Lab"],
                  "SGH": ["NICU"], "HJH": ["NICU"]}
# a few services that are temporarily down, to make the directory honest
SERVICE_OUTAGES = {("SGH", "CT Scan"): "Under maintenance", ("HJH", "Blood Bank"): "Low stock - call before referral",
                   ("SHH", "MRI"): "Machine down, expected back in 3 days"}

# patient home cities: city, region, weight, pincodes
CITIES = [("Kolkata", "KOL", 40, [f"7000{n:02d}" for n in range(1, 100)]),
          ("Howrah", "KOL", 12, [f"7111{n:02d}" for n in range(1, 16)]),
          ("Bidhannagar", "KOL", 7, ["700064", "700091", "700097", "700106"]),
          ("New Town", "KOL", 6, ["700135", "700156", "700157"]),
          ("Barasat", "KOL", 8, ["700124", "700125", "700126"]),
          ("Baruipur", "KOL", 7, ["700144", "700145"]),
          ("Durgapur", "DGP", 10, [f"7132{n:02d}" for n in range(1, 17)]),
          ("Siliguri", "SLG", 10, [f"7340{n:02d}" for n in range(1, 13)])]

# drug classes, used for allergy checks  (keyed by the first word of the medication name)
MED_CLASSES = {
    "Paracetamol": ["analgesic"], "Pantoprazole": ["ppi"], "Amoxicillin-Clavulanate": ["penicillin"],
    "Amoxicillin": ["penicillin"], "Azithromycin": ["macrolide"], "Ceftriaxone": ["cephalosporin"],
    "Metformin": ["biguanide"], "Glimepiride": ["sulfonylurea"], "Insulin": ["insulin"], "Amlodipine": ["calcium_channel_blocker"],
    "Telmisartan": ["arb"], "Atorvastatin": ["statin"], "Aspirin": ["nsaid", "antiplatelet"], "Clopidogrel": ["antiplatelet"],
    "Furosemide": ["loop_diuretic", "sulfonamide"], "Levothyroxine": ["thyroid_hormone"], "Salbutamol": ["beta2_agonist"],
    "Budesonide-Formoterol": ["inhaled_corticosteroid", "beta2_agonist"], "Montelukast": ["leukotriene_antagonist"],
    "Ondansetron": ["antiemetic"], "ORS": ["electrolyte"], "Metronidazole": ["nitroimidazole"], "Ofloxacin": ["fluoroquinolone"],
    "Nitrofurantoin": ["nitrofuran"], "Artemether-Lumefantrine": ["antimalarial"], "Levetiracetam": ["antiepileptic"],
    "Sumatriptan": ["triptan"], "Diclofenac": ["nsaid"], "Calcium": ["calcium_supplement"], "Tramadol": ["opioid"],
    "Cetirizine": ["antihistamine"], "Clotrimazole": ["azole_antifungal"], "Mometasone": ["topical_corticosteroid"],
    "Ferrous": ["iron_supplement"], "Oxytocin": ["uterotonic"], "Tranexamic": ["antifibrinolytic"], "Normal": ["iv_fluid"],
}

# allergen, class it maps to, typical reactions, relative frequency
DRUG_ALLERGIES = [("Penicillin", "penicillin", ["Skin rash", "Hives", "Anaphylaxis"], 45),
                  ("NSAIDs", "nsaid", ["Bronchospasm", "Angioedema", "Hives"], 20),
                  ("Sulfa drugs", "sulfonamide", ["Skin rash", "Fever"], 15),
                  ("Cephalosporins", "cephalosporin", ["Skin rash", "Hives"], 10),
                  ("Fluoroquinolones", "fluoroquinolone", ["Tendon pain", "Skin rash"], 10)]

# DEMO drug-drug interactions (keyed by the first word of the medication name). Not a clinical reference.
DRUG_INTERACTIONS = [
    ("Aspirin", "Clopidogrel", "moderate", "Additive bleeding risk.", "Often intentional (dual antiplatelet therapy) - confirm indication and watch for bleeding."),
    ("Aspirin", "Diclofenac", "major", "Two NSAIDs together: high risk of stomach bleeding; may reduce aspirin's heart protection.", "Avoid the combination; use paracetamol for pain."),
    ("Clopidogrel", "Diclofenac", "major", "NSAID plus antiplatelet: increased bleeding risk.", "Avoid, or add stomach protection and monitor closely."),
    ("Telmisartan", "Diclofenac", "moderate", "NSAIDs reduce the blood-pressure effect of ARBs and can harm the kidneys.", "Prefer paracetamol; if unavoidable, monitor BP and creatinine."),
    ("Furosemide", "Diclofenac", "moderate", "NSAIDs blunt the diuretic effect and raise kidney-injury risk.", "Avoid where possible; monitor kidney function."),
    ("Tramadol", "Ondansetron", "moderate", "Risk of serotonin syndrome; ondansetron may also reduce tramadol's pain relief.", "Use the lowest doses and monitor, or choose another antiemetic."),
    ("Tramadol", "Sumatriptan", "major", "Both are serotonergic: risk of serotonin syndrome.", "Avoid the combination."),
    ("Azithromycin", "Ondansetron", "moderate", "Both can prolong the QT interval.", "Check ECG in patients with heart disease or low potassium."),
    ("Ofloxacin", "Ondansetron", "moderate", "Both can prolong the QT interval.", "Check ECG in patients at risk."),
    ("Artemether-Lumefantrine", "Ondansetron", "moderate", "Both can prolong the QT interval.", "Monitor ECG if used together."),
    ("Levothyroxine", "Ferrous", "moderate", "Iron binds levothyroxine in the gut and reduces absorption.", "Take them at least 4 hours apart."),
    ("Levothyroxine", "Calcium", "moderate", "Calcium reduces levothyroxine absorption.", "Take them at least 4 hours apart."),
    ("Ofloxacin", "Ferrous", "moderate", "Iron reduces absorption of the antibiotic.", "Take the antibiotic 2 hours before or 6 hours after iron."),
    ("Ofloxacin", "Calcium", "moderate", "Calcium reduces absorption of the antibiotic.", "Separate the doses by several hours."),
    ("Glimepiride", "Insulin", "moderate", "Additive risk of low blood sugar.", "Monitor glucose; adjust doses."),
]

# DEMO drug-condition cautions (medication first word, ICD-10 prefix). Not a clinical reference.
DRUG_CONDITION_CAUTIONS = [
    ("Metformin", "N18", "major", "Metformin can build up when kidney function is reduced (lactic acidosis risk).", "Check eGFR; reduce the dose or stop if eGFR is below 30."),
    ("Diclofenac", "N18", "major", "NSAIDs can worsen chronic kidney disease.", "Avoid NSAIDs; use paracetamol for pain."),
    ("Aspirin", "N18", "moderate", "Regular NSAID-dose aspirin can affect kidney function.", "Low-dose aspirin is usually acceptable; avoid pain-relief doses."),
    ("Nitrofurantoin", "N18", "major", "Less effective and more toxic when kidney function is reduced.", "Choose another antibiotic."),
    ("Glimepiride", "N18", "moderate", "Higher risk of low blood sugar in kidney disease.", "Start low and monitor glucose."),
    ("Diclofenac", "I50", "major", "NSAIDs cause fluid retention and can worsen heart failure.", "Avoid; use paracetamol."),
    ("Diclofenac", "A90", "contraindicated", "NSAIDs increase bleeding risk in dengue.", "Do not use; paracetamol only."),
    ("Aspirin", "A90", "contraindicated", "Aspirin increases bleeding risk in dengue.", "Do not use; paracetamol only."),
    ("Tramadol", "G40", "major", "Tramadol lowers the seizure threshold.", "Avoid in epilepsy; choose another analgesic."),
    ("Telmisartan", "Z34", "contraindicated", "ARBs can harm the developing baby.", "Stop and switch to a pregnancy-safe antihypertensive."),
    ("Atorvastatin", "Z34", "contraindicated", "Statins are not recommended in pregnancy.", "Stop during pregnancy."),
    ("Diclofenac", "Z34", "major", "NSAIDs are best avoided in pregnancy, especially the third trimester.", "Use paracetamol."),
    ("Salbutamol", "I21", "moderate", "Beta-agonists can raise heart rate after a heart attack.", "Use with caution and monitor."),
]

CONSENT_SCOPES = ["encounters", "diagnoses", "prescriptions", "lab_results", "documents"]
