"""Persistent Profile and Patient Record Synchronization Store.

Provides cross-device persistent storage for sovereign unique IDs, user profiles,
longitudinal patient medications, allergies, and clinical timeline events.
Ensures new users start with clean profiles (zero dummy data) and all uploaded
records (by patient or treating doctor) remain up to date across any computer.
"""

import json
import os
from datetime import datetime, timezone
from typing import Any

STORAGE_DIR = os.path.join(os.getcwd(), "storage")
USERS_FILE = os.path.join(STORAGE_DIR, "registered_users.json")
PATIENT_RECORDS_DIR = os.path.join(STORAGE_DIR, "patient_records")

os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(PATIENT_RECORDS_DIR, exist_ok=True)

# Pre-seeded demo profiles
DEMO_PROFILES: dict[str, dict[str, Any]] = {
    "hs-pat-8921": {
        "id": "HS-PAT-8921",
        "name": "Rohan Sharma",
        "role": "patient",
        "email": "rohan.sharma@example.com",
        "phone": "+91 98104 22910",
        "avatarInitials": "RS",
        "issuedAt": "12 Sep 2026",
        "patientDetails": {
            "age": 42,
            "gender": "Male",
            "bloodGroup": "O Positive",
            "city": "New Delhi",
            "emergencyContact": "Sunita Sharma (Spouse) · +91 98104 22911",
        },
    },
    "doc-aiims-104": {
        "id": "DOC-AIIMS-104",
        "name": "Dr. Priya Nair",
        "role": "doctor",
        "email": "doctor@healthsetu.org",
        "phone": "+91 11 2658 8500",
        "avatarInitials": "PN",
        "issuedAt": "14 Jan 2024",
        "doctorDetails": {
            "degree": "MD, DM (Cardiology)",
            "specialization": "Senior Consultant Cardiologist",
            "hospital": "All India Institute of Medical Sciences (AIIMS), New Delhi",
            "councilReg": "MCI-48291 · Verified Clinician",
        },
    },
    "hosp-apollo-01": {
        "id": "HOSP-APOLLO-01",
        "name": "Apollo Indraprastha Hospital",
        "role": "hospital",
        "email": "emergency@apollo-delhi.org",
        "phone": "+91 11 2692 5858",
        "avatarInitials": "AI",
        "issuedAt": "01 Jan 2023",
        "hospitalDetails": {
            "facilityType": "Super Speciality & Level-1 Trauma",
            "city": "Sarita Vihar, New Delhi",
            "totalBeds": 210,
            "icuBeds": 40,
            "helpline": "+91 11 2692 5858 (24x7 Emergency Desk)",
        },
    },
}

# In-memory stores
_memory_users: dict[str, dict[str, Any]] = {}
_memory_patient_records: dict[str, dict[str, Any]] = {}


def _load_users_from_disk() -> None:
    """Load persisted users from disk."""
    global _memory_users
    # Start with demo profiles
    for k, v in DEMO_PROFILES.items():
        _memory_users[k] = v
        _memory_users[v["id"].lower()] = v
        _memory_users[v["email"].lower()] = v

    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for u in data:
                        if isinstance(u, dict) and "id" in u:
                            uid = u["id"].lower()
                            _memory_users[uid] = u
                            if "email" in u and u["email"]:
                                _memory_users[u["email"].lower()] = u
        except Exception as e:
            print(f"[HealthSetu Storage] Error loading users: {e}")


def _save_users_to_disk() -> None:
    """Save unique user records to disk."""
    try:
        unique_users: dict[str, dict[str, Any]] = {}
        for u in _memory_users.values():
            if "id" in u:
                unique_users[u["id"]] = u
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(unique_users.values()), f, indent=2)
    except Exception as e:
        print(f"[HealthSetu Storage] Error saving users: {e}")


def get_user_profile(identifier: str) -> dict[str, Any] | None:
    """Look up a user profile by unique ID, email, or phone."""
    clean = identifier.strip().lower()
    if not _memory_users:
        _load_users_from_disk()

    if clean in _memory_users:
        return _memory_users[clean]

    # Search through values
    for u in _memory_users.values():
        if u.get("id", "").lower() == clean:
            return u
        if u.get("email", "").lower() == clean:
            return u
        phone = u.get("phone")
        if phone and clean in phone.lower():
            return u
    return None


def save_user_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Save or update user profile across memory and disk."""
    if not _memory_users:
        _load_users_from_disk()

    uid = profile["id"].lower()
    _memory_users[uid] = profile
    if profile.get("email"):
        _memory_users[profile["email"].lower()] = profile

    _save_users_to_disk()

    # If it's a patient, initialize an empty clean record if one doesn't exist
    if profile.get("role") == "patient":
        pid = profile["id"].upper()
        if not get_patient_record(pid):
            pdetails = profile.get("patientDetails") or {}
            init_record = {
                "patient_id": pid,
                "name": profile.get("name", "Registered Patient"),
                "age": pdetails.get("age"),
                "gender": pdetails.get("gender") or "Unspecified",
                "bloodGroup": pdetails.get("bloodGroup") or "Not Specified",
                "city": pdetails.get("city") or "Not Specified",
                "phone": profile.get("phone", ""),
                "emergencyContact": pdetails.get("emergencyContact", ""),
                "medications": [],
                "allergies": [],
                "timeline": [
                    {
                        "id": f"tl-init-{pid}",
                        "date": profile.get("issuedAt", "Today"),
                        "title": "HealthSetu Sovereign ID Minted",
                        "category": "milestone",
                        "provider": "HealthSetu Digital Health Grid",
                        "facility": pdetails.get("city") or "Verified Health Node",
                        "description": f"Sovereign unique credential issued for {profile.get('name')}. Unique ID: {pid}.",
                        "trustState": "verified",
                    }
                ],
                "access_requests": [],
            }
            save_patient_record(pid, init_record)

    return profile


def _get_patient_file_path(patient_id: str) -> str:
    safe_id = patient_id.replace("/", "_").replace("\\", "_").upper()
    return os.path.join(PATIENT_RECORDS_DIR, f"{safe_id}.json")


def get_patient_record(patient_id: str) -> dict[str, Any] | None:
    """Retrieve full longitudinal patient record.
    
    For new patients, returns ONLY their real uploaded data (0 dummy data).
    For demo patient HS-PAT-8921, provides demo fallback if no custom record exists.
    """
    clean_id = patient_id.strip().upper()
    if clean_id in _memory_patient_records:
        return _memory_patient_records[clean_id]

    file_path = _get_patient_file_path(clean_id)
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                record = json.load(f)
                _memory_patient_records[clean_id] = record
                return record
        except Exception as e:
            print(f"[HealthSetu Storage] Error reading patient record {clean_id}: {e}")

    # If it's the demo patient Rohan Sharma, populate initial demo records
    if clean_id == "HS-PAT-8921":
        demo_record = {
            "patient_id": "HS-PAT-8921",
            "name": "Rohan Sharma",
            "age": 42,
            "gender": "Male",
            "bloodGroup": "O Positive",
            "city": "New Delhi",
            "phone": "+91 98104 22910",
            "emergencyContact": "Sunita Sharma (Spouse) · +91 98104 22911",
            "medications": [
                {
                    "id": "med-1",
                    "name": "Telmisartan",
                    "genericName": "Telmisartan",
                    "strength": "40mg",
                    "dosage": "1 Tablet",
                    "frequency": "Once daily (Morning)",
                    "route": "Oral",
                    "duration": "90 Days",
                    "instructions": "Take after breakfast with water",
                    "prescribingDoctor": "Dr. Priya Nair, MD (Cardiology)",
                    "hospital": "AIIMS, New Delhi",
                    "datePrescribed": "12 Sep 2026",
                    "trustState": "verified",
                    "timeOfDay": ["morning"],
                    "mealTiming": "after_food",
                    "category": "Antihypertensive",
                },
                {
                    "id": "med-2",
                    "name": "Metformin",
                    "genericName": "Metformin HCl",
                    "strength": "500mg",
                    "dosage": "1 Tablet",
                    "frequency": "Twice daily with meals",
                    "route": "Oral",
                    "duration": "90 Days",
                    "instructions": "Take with breakfast and dinner",
                    "prescribingDoctor": "Dr. Ananya Iyer, MD (Endocrinology)",
                    "hospital": "Max Super Speciality Hospital, Saket",
                    "datePrescribed": "05 Sep 2026",
                    "trustState": "verified",
                    "timeOfDay": ["morning", "evening"],
                    "mealTiming": "with_food",
                    "category": "Antidiabetic",
                },
                {
                    "id": "med-3",
                    "name": "Atorvastatin",
                    "genericName": "Atorvastatin Calcium",
                    "strength": "20mg",
                    "dosage": "1 Tablet",
                    "frequency": "Once daily at bedtime",
                    "route": "Oral",
                    "duration": "90 Days",
                    "instructions": "Take at night before sleep",
                    "prescribingDoctor": "Dr. Priya Nair, MD (Cardiology)",
                    "hospital": "AIIMS, New Delhi",
                    "datePrescribed": "12 Sep 2026",
                    "trustState": "verified",
                    "timeOfDay": ["bedtime"],
                    "mealTiming": "after_food",
                    "category": "Lipid-lowering agent",
                },
            ],
            "allergies": [
                {
                    "id": "alg-1",
                    "allergen": "Penicillin G",
                    "reaction": "Anaphylaxis & Urticaria",
                    "severity": "severe",
                    "recordedDate": "14 Mar 2021",
                    "recordedBy": "AIIMS Emergency Dept",
                    "trustState": "verified",
                }
            ],
            "timeline": [
                {
                    "id": "tl-1",
                    "date": "12 Sep 2026",
                    "title": "Cardiology Follow-Up Consultation",
                    "category": "consultation",
                    "provider": "Dr. Priya Nair, MD",
                    "facility": "AIIMS, New Delhi",
                    "description": "Quarterly hypertensive evaluation. BP stable at 126/82 mmHg. Telmisartan renewed.",
                    "trustState": "verified",
                }
            ],
            "access_requests": [],
        }
        save_patient_record(clean_id, demo_record)
        return demo_record

    # For ANY other user: check if user profile exists
    u = get_user_profile(clean_id)
    if u and u.get("role") == "patient":
        empty_clean_record = {
            "patient_id": clean_id,
            "name": u.get("name", "Registered Patient"),
            "age": u.get("patientDetails", {}).get("age", 30),
            "gender": u.get("patientDetails", {}).get("gender", "Other"),
            "bloodGroup": u.get("patientDetails", {}).get("bloodGroup", "Not Specified"),
            "city": u.get("patientDetails", {}).get("city", "Not Specified"),
            "phone": u.get("phone", ""),
            "emergencyContact": u.get("patientDetails", {}).get("emergencyContact", ""),
            "medications": [],
            "allergies": [],
            "timeline": [
                {
                    "id": f"tl-init-{clean_id}",
                    "date": u.get("issuedAt", "Today"),
                    "title": "HealthSetu Sovereign Profile Issued",
                    "category": "milestone",
                    "provider": "HealthSetu Digital Health Grid",
                    "facility": u.get("patientDetails", {}).get("city", "Verified Health Node"),
                    "description": f"Sovereign unique credential issued for {u.get('name')}. Unique ID: {clean_id}.",
                    "trustState": "verified",
                }
            ],
            "access_requests": [],
        }
        save_patient_record(clean_id, empty_clean_record)
        return empty_clean_record

    return None


def save_patient_record(patient_id: str, record: dict[str, Any]) -> dict[str, Any]:
    """Persist updated longitudinal patient record to memory and disk."""
    clean_id = patient_id.strip().upper()
    record["patient_id"] = clean_id
    record["updated_at"] = datetime.now(timezone.utc).isoformat()
    _memory_patient_records[clean_id] = record

    file_path = _get_patient_file_path(clean_id)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)
    except Exception as e:
        print(f"[HealthSetu Storage] Error writing patient record {clean_id}: {e}")

    return record


# Initialize on module import
_load_users_from_disk()
