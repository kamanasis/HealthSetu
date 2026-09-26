"""Demo and development in-memory data seeder for HealthSetu.

Populates initial synthetic demo data (Patient Rohan Sharma, Dr. Priya Nair,
active medications, verified allergies, vitals, care plan, consents, and
network hospital facilities) so the application functions out-of-the-box
with full end-to-end frontend/backend fidelity without external database requirements.
"""

from datetime import date, datetime, timedelta, timezone
import uuid

from app.api.deps import (
    _global_allergy_repo,
    _global_authz_service,
    _global_care_plan_repo,
    _global_consent_repo,
    _global_department_repo,
    _global_facility_repo,
    _global_history_repo,
    _global_organization_repo,
    _global_patient_medication_repo,
    _global_patient_repo,
    _global_session_repo,
    _global_user_repo,
    _global_vitals_repo,
)
from app.core.logging import get_logger
from app.core.security import hash_password
from app.repositories.allergy_repository import AllergyRecord
from app.repositories.care_plan_repository import CarePlanRecord
from app.repositories.clinical_history_repository import ClinicalHistoryRecord
from app.repositories.consent_repository import ConsentRecord
from app.repositories.patient_medication_repository import PatientMedicationRecord
from app.repositories.patient_repository import PatientRecord
from app.repositories.user_repository import UserRecord
from app.repositories.vitals_repository import VitalRecord
from app.schemas.allergy import AllergySeverity, AllergyStatus
from app.schemas.auth import AccountStatus, UserRole
from app.schemas.authorization import ConsentStatus
from app.schemas.care_plan import (
    CarePlanGoal,
    CarePlanStatus,
    CarePlanTask,
    CarePlanTaskCategory,
    CarePlanTaskStatus,
    CarePlanWarningSignGuidance,
)
from app.schemas.clinical_history import ClinicalDataSource, ConditionStatus
from app.schemas.department import DepartmentRecord, DepartmentStatus
from app.schemas.facility import FacilityRecord, FacilityStatus, FacilityType
from app.schemas.medication import (
    MedicationSource,
    PatientMedicationStatus,
    VerificationStatus,
)
from app.schemas.organization import (
    OrganizationRecord,
    OrganizationStatus,
    OrganizationType,
)
from app.schemas.patient import BiologicalSex, PatientStatus
from app.schemas.vital import VitalSource, VitalType

logger = get_logger("app.demo_seed")

DEMO_SEEDED = False


def seed_demo_data(force: bool = False) -> None:
    """Seed comprehensive initial demo state into in-memory repositories."""
    global DEMO_SEEDED
    if DEMO_SEEDED and not force:
        return

    now = datetime.now(timezone.utc)
    today = now.date()

    logger.info("Initializing HealthSetu demo dataset into in-memory repositories...")

    # -------------------------------------------------------------------------
    # 1. Identity & Users (Phase 2)
    # Standard password works for both 'StrongP@ssw0rd123!' and 'password123'
    # -------------------------------------------------------------------------
    pwd_hash = hash_password("StrongP@ssw0rd123!")

    users = [
        UserRecord(
            id="usr-patient-001",
            identifier="patient@healthsetu.org",
            password_hash=pwd_hash,
            role=UserRole.PATIENT,
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        ),
        UserRecord(
            id="usr-doctor-001",
            identifier="doctor@healthsetu.org",
            password_hash=pwd_hash,
            role=UserRole.DOCTOR,
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        ),
        UserRecord(
            id="usr-admin-001",
            identifier="admin@healthsetu.org",
            password_hash=pwd_hash,
            role=UserRole.ADMIN,
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        ),
    ]

    for u in users:
        _global_user_repo.register_in_memory_user(u)

    # Register Unique ID aliases so users can authenticate using their HealthSetu Unique IDs directly
    _global_user_repo._local_users["hs-pat-8921"] = users[0]
    _global_user_repo._local_users["doc-aiims-104"] = users[1]
    _global_user_repo._local_users["hosp-apollo-01"] = users[2]
    _global_user_repo._local_users["hosp-1"] = users[2]
    _global_user_repo._local_users["hospital@healthsetu.org"] = users[2]

    # -------------------------------------------------------------------------
    # 2. Patient Profiles (Phase 4)
    # Primary patient: Rohan Sharma (HS-PAT-8921)
    # -------------------------------------------------------------------------
    primary_patient = PatientRecord(
        id="HS-PAT-8921",
        user_id="usr-patient-001",
        first_name="Rohan",
        last_name="Sharma",
        date_of_birth=date(1984, 4, 12),
        sex=BiologicalSex.MALE,
        status=PatientStatus.ACTIVE,
        preferred_language="en",
        phone="+91 98104 22910",
        email="rohan.sharma@example.com",
        created_at=now - timedelta(days=120),
        updated_at=now,
    )
    _global_patient_repo._patients[primary_patient.id] = primary_patient
    _global_patient_repo._user_to_patient[primary_patient.user_id] = primary_patient.id

    # Secondary alias for backwards-compatible test suites
    alias_patient = PatientRecord(
        id="pat-001",
        user_id="usr-patient-001",
        first_name="Rohan",
        last_name="Sharma",
        date_of_birth=date(1984, 4, 12),
        sex=BiologicalSex.MALE,
        status=PatientStatus.ACTIVE,
        preferred_language="en",
        phone="+91 98104 22910",
        email="rohan.sharma@example.com",
        created_at=now - timedelta(days=120),
        updated_at=now,
    )
    _global_patient_repo._patients[alias_patient.id] = alias_patient

    # -------------------------------------------------------------------------
    # 3. Documented Allergies (Phase 4)
    # -------------------------------------------------------------------------
    allergies = [
        AllergyRecord(
            id="alg-1",
            patient_id="HS-PAT-8921",
            allergen="Penicillin / Amoxicillin",
            reaction="Anaphylactic reaction & severe urticaria",
            severity=AllergySeverity.SEVERE,
            status=AllergyStatus.ACTIVE,
            source=ClinicalDataSource.CLINIC_ENTERED,
            recorded_by="Dr. Rajesh Deshmukh (Apollo Hospital)",
            notes="Confirmed anaphylactic shock requiring epinephrine during childhood treatment.",
            created_at=now - timedelta(days=900),
            updated_at=now - timedelta(days=900),
        ),
        AllergyRecord(
            id="alg-2",
            patient_id="HS-PAT-8921",
            allergen="NSAIDs (Ibuprofen / Diclofenac)",
            reaction="Gastric distress & acute bronchospasm",
            severity=AllergySeverity.MODERATE,
            status=AllergyStatus.ACTIVE,
            source=ClinicalDataSource.CLINIC_ENTERED,
            recorded_by="Dr. Priya Nair (AIIMS)",
            notes="Documented acute wheezing after oral ibuprofen administration.",
            created_at=now - timedelta(days=400),
            updated_at=now - timedelta(days=400),
        ),
    ]
    for a in allergies:
        _global_allergy_repo._records[a.id] = a

    # -------------------------------------------------------------------------
    # 4. Objective Vital Measurements (Phase 4)
    # -------------------------------------------------------------------------
    vitals = [
        VitalRecord(
            id="vit-1",
            patient_id="HS-PAT-8921",
            vital_type=VitalType.BLOOD_PRESSURE_SYSTOLIC,
            value=126.0,
            unit="mmHg",
            measured_at=now - timedelta(days=14),
            source=VitalSource.CLINIC_RECORDED,
            created_at=now - timedelta(days=14),
            recorded_by="Dr. Priya Nair",
        ),
        VitalRecord(
            id="vit-2",
            patient_id="HS-PAT-8921",
            vital_type=VitalType.BLOOD_PRESSURE_DIASTOLIC,
            value=82.0,
            unit="mmHg",
            measured_at=now - timedelta(days=14),
            source=VitalSource.CLINIC_RECORDED,
            created_at=now - timedelta(days=14),
            recorded_by="Dr. Priya Nair",
        ),
        VitalRecord(
            id="vit-3",
            patient_id="HS-PAT-8921",
            vital_type=VitalType.HEART_RATE,
            value=72.0,
            unit="bpm",
            measured_at=now - timedelta(days=14),
            source=VitalSource.CLINIC_RECORDED,
            created_at=now - timedelta(days=14),
            recorded_by="Dr. Priya Nair",
        ),
        VitalRecord(
            id="vit-4",
            patient_id="HS-PAT-8921",
            vital_type=VitalType.OXYGEN_SATURATION,
            value=98.0,
            unit="%",
            measured_at=now - timedelta(days=14),
            source=VitalSource.CLINIC_RECORDED,
            created_at=now - timedelta(days=14),
            recorded_by="Dr. Priya Nair",
        ),
    ]
    for v in vitals:
        _global_vitals_repo._records[v.id] = v

    # -------------------------------------------------------------------------
    # 5. Clinical History & Chronic Conditions (Phase 4)
    # -------------------------------------------------------------------------
    history = [
        ClinicalHistoryRecord(
            id="ch-1",
            patient_id="HS-PAT-8921",
            description="Essential Hypertension (Controlled on ARB)",
            condition_status=ConditionStatus.ACTIVE,
            source=ClinicalDataSource.CLINIC_ENTERED,
            onset_date=date(2021, 6, 10),
            recorded_by="Dr. Priya Nair",
            created_at=now - timedelta(days=500),
            updated_at=now - timedelta(days=14),
        ),
        ClinicalHistoryRecord(
            id="ch-2",
            patient_id="HS-PAT-8921",
            description="Dyslipidemia / Hypercholesterolemia",
            condition_status=ConditionStatus.ACTIVE,
            source=ClinicalDataSource.CLINIC_ENTERED,
            onset_date=date(2022, 2, 18),
            recorded_by="Dr. Rajesh Deshmukh",
            created_at=now - timedelta(days=400),
            updated_at=now - timedelta(days=14),
        ),
        ClinicalHistoryRecord(
            id="ch-3",
            patient_id="HS-PAT-8921",
            description="Type-2 Diabetes Mellitus (Diet & Metformin managed)",
            condition_status=ConditionStatus.ACTIVE,
            source=ClinicalDataSource.CLINIC_ENTERED,
            onset_date=date(2023, 11, 5),
            recorded_by="Dr. Ananya Iyer",
            created_at=now - timedelta(days=300),
            updated_at=now - timedelta(days=14),
        ),
    ]
    for h in history:
        _global_history_repo._records[h.id] = h

    # -------------------------------------------------------------------------
    # 6. Longitudinal Active Patient Medications (Phase 6)
    # -------------------------------------------------------------------------
    meds = [
        PatientMedicationRecord(
            id="med-1",
            patient_id="HS-PAT-8921",
            drug_name_raw="Telmisartan",
            strength_raw="40 mg",
            dosage_form_raw="Tablet",
            route_raw="Oral",
            frequency_raw="Once daily (OD)",
            duration_raw="90 Days",
            instructions_raw="Take in the morning with a glass of water, before or after breakfast",
            status=PatientMedicationStatus.ACTIVE,
            verification_status=VerificationStatus.VERIFIED,
            source=MedicationSource.PRESCRIPTION,
            created_at=now - timedelta(days=14),
            updated_at=now - timedelta(days=14),
        ),
        PatientMedicationRecord(
            id="med-2",
            patient_id="HS-PAT-8921",
            drug_name_raw="Metformin Hydrochloride",
            strength_raw="500 mg",
            dosage_form_raw="Tablet",
            route_raw="Oral",
            frequency_raw="Twice daily (BD)",
            duration_raw="90 Days",
            instructions_raw="Take with food to minimize gastrointestinal discomfort",
            status=PatientMedicationStatus.ACTIVE,
            verification_status=VerificationStatus.VERIFIED,
            source=MedicationSource.PRESCRIPTION,
            created_at=now - timedelta(days=14),
            updated_at=now - timedelta(days=14),
        ),
        PatientMedicationRecord(
            id="med-3",
            patient_id="HS-PAT-8921",
            drug_name_raw="Atorvastatin",
            strength_raw="20 mg",
            dosage_form_raw="Tablet",
            route_raw="Oral",
            frequency_raw="Once daily at bedtime (HS)",
            duration_raw="60 Days",
            instructions_raw="Take strictly at night after dinner",
            status=PatientMedicationStatus.ACTIVE,
            verification_status=VerificationStatus.VERIFIED,
            source=MedicationSource.PRESCRIPTION,
            created_at=now - timedelta(days=28),
            updated_at=now - timedelta(days=28),
        ),
    ]
    for m in meds:
        _global_patient_medication_repo._medications[m.id] = m

    # -------------------------------------------------------------------------
    # 7. Patient Consents & Doctor Relationships (Phase 3)
    # -------------------------------------------------------------------------
    # Active relationship between Dr. Priya Nair and Rohan Sharma
    _global_authz_service.establish_relationship("usr-doctor-001", "usr-patient-001")
    _global_authz_service.establish_relationship("usr-doctor-001", "HS-PAT-8921")
    _global_authz_service.establish_relationship("DOC-AIIMS-104", "HS-PAT-8921")

    # Consent grant: care delivery across all records
    consent_grant = ConsentRecord(
        id="req-1",
        patient_id="usr-patient-001",
        grantee_id="usr-doctor-001",
        purpose="care_delivery",
        scope="all_records",
        status=ConsentStatus.ACTIVE,
        granted_at=now - timedelta(days=2),
        effective_from=now - timedelta(days=2),
        expires_at=now + timedelta(days=30),
        notes="Authorized for continuous cardiovascular and metabolic care coordination.",
    )
    _global_consent_repo._consents[consent_grant.id] = consent_grant

    # -------------------------------------------------------------------------
    # 8. Organizations & Hospital Facilities (Phase 11 & 12)
    # -------------------------------------------------------------------------
    org = OrganizationRecord(
        id="org-delhi",
        name="Delhi Integrated Healthcare Network",
        organization_type=OrganizationType.HEALTHCARE_NETWORK,
        status=OrganizationStatus.ACTIVE,
        description="Coordinated acute and critical emergency care network in NCR",
    )
    _global_organization_repo._organizations[org.id] = org

    facilities = [
        FacilityRecord(
            id="hosp-1",
            organization_id="org-delhi",
            name="Apollo Indraprastha Hospital",
            facility_type=FacilityType.HOSPITAL,
            status=FacilityStatus.ACTIVE,
            phone="+91 11 2692 5858",
            email="emergency@apollo-delhi.org",
            address={
                "city": "New Delhi",
                "line": "Sarita Vihar, Delhi Mathura Road",
                "postal_code": "110076",
                "latitude": 28.5355,
                "longitude": 77.2910,
            },
            operational_metadata={
                "available_beds": {"icu": 7, "emergency": 12, "general": 45},
                "total_beds": 210,
                "emergency_status": "Available",
                "specialties": ["Comprehensive Stroke Center", "24x7 Cath Lab", "Level-1 Trauma", "Pediatric ICU"],
                "distance_km": 3.4,
                "is_network_shared": True,
            },
        ),
        FacilityRecord(
            id="hosp-2",
            organization_id="org-delhi",
            name="Max Super Speciality Hospital",
            facility_type=FacilityType.HOSPITAL,
            status=FacilityStatus.ACTIVE,
            phone="+91 11 2651 5050",
            email="admissions@maxhealthcare.com",
            address={
                "city": "New Delhi",
                "line": "1, 2, Press Enclave Marg, Saket",
                "postal_code": "110017",
                "latitude": 28.5283,
                "longitude": 77.2185,
            },
            operational_metadata={
                "available_beds": {"icu": 2, "emergency": 4, "general": 19},
                "total_beds": 180,
                "emergency_status": "Available",
                "specialties": ["Cardiac Emergency", "Neurosurgery", "Organ Transplant", "Medical Oncology"],
                "distance_km": 5.8,
                "is_network_shared": True,
            },
        ),
        FacilityRecord(
            id="hosp-3",
            organization_id="org-delhi",
            name="Fortis Escorts Heart Institute",
            facility_type=FacilityType.HOSPITAL,
            status=FacilityStatus.ACTIVE,
            phone="+91 11 4713 5000",
            email="info@fortis-escorts.org",
            address={
                "city": "New Delhi",
                "line": "Okhla Road, Sukhdev Vihar Metro Station",
                "postal_code": "110025",
                "latitude": 28.5603,
                "longitude": 77.2845,
            },
            operational_metadata={
                "available_beds": {"icu": 0, "emergency": 2, "general": 8},
                "total_beds": 150,
                "emergency_status": "Critical Capacity",
                "specialties": ["Advanced Heart Failure", "Emergency Angioplasty", "Vascular Intervention"],
                "distance_km": 4.1,
                "is_network_shared": True,
            },
        ),
        FacilityRecord(
            id="hosp-4",
            organization_id="org-delhi",
            name="Holy Family Hospital",
            facility_type=FacilityType.HOSPITAL,
            status=FacilityStatus.ACTIVE,
            phone="+91 11 2684 5201",
            email="helpdesk@holyfamilyhospitaldelhi.org",
            address={
                "city": "New Delhi",
                "line": "Jamia Nagar, Okhla",
                "postal_code": "110025",
                "latitude": 28.5621,
                "longitude": 77.2798,
            },
            operational_metadata={
                "available_beds": {"icu": 4, "emergency": 9, "general": 32},
                "total_beds": 120,
                "emergency_status": "Available",
                "specialties": ["Obstetrics & Gynecology", "General Surgery", "Internal Medicine", "Dialysis"],
                "distance_km": 2.9,
                "is_network_shared": True,
            },
        ),
    ]

    for f in facilities:
        _global_facility_repo._facilities[f.id] = f
        if f.organization_id not in _global_facility_repo._org_facilities:
            _global_facility_repo._org_facilities[f.organization_id] = []
        _global_facility_repo._org_facilities[f.organization_id].append(f.id)

    # -------------------------------------------------------------------------
    # 9. Personalized Care Plan (Phase 9)
    # -------------------------------------------------------------------------
    care_plan = CarePlanRecord(
        id="cp-8921-cardio",
        patient_id="HS-PAT-8921",
        title="30-Day Cardiovascular & Glycemic Recovery Plan",
        status=CarePlanStatus.ACTIVE,
        start_date=today,
        end_date=today + timedelta(days=30),
        goals=[
            CarePlanGoal(
                id="goal-1",
                description="Maintain home resting blood pressure < 130/80 mmHg",
                target_date=today + timedelta(days=30),
                status="IN_PROGRESS",
            ),
            CarePlanGoal(
                id="goal-2",
                description="Achieve stable fasting blood glucose between 90-110 mg/dL",
                target_date=today + timedelta(days=30),
                status="IN_PROGRESS",
            ),
            CarePlanGoal(
                id="goal-3",
                description="Moderate aerobic ambulation (20-30 mins brisk walking daily)",
                target_date=today + timedelta(days=30),
                status="IN_PROGRESS",
            ),
        ],
        tasks=[
            CarePlanTask(
                id="task-1",
                category=CarePlanTaskCategory.MEDICATION,
                title="Morning Antihypertensive Dose",
                instructions="Telmisartan 40mg with a glass of water before breakfast",
                frequency="DAILY",
                day_offset=0,
                due_date=today,
                status=CarePlanTaskStatus.PENDING,
            ),
            CarePlanTask(
                id="task-2",
                category=CarePlanTaskCategory.MEDICATION,
                title="Breakfast Antidiabetic Dose",
                instructions="Metformin 500mg SR immediately after breakfast",
                frequency="DAILY",
                day_offset=0,
                due_date=today,
                status=CarePlanTaskStatus.PENDING,
            ),
            CarePlanTask(
                id="task-3",
                category=CarePlanTaskCategory.VITALS_MONITORING,
                title="Log Morning Resting BP",
                instructions="Record systolic and diastolic reading in seated posture after 5 min rest",
                frequency="DAILY",
                day_offset=0,
                due_date=today,
                status=CarePlanTaskStatus.PENDING,
            ),
            CarePlanTask(
                id="task-4",
                category=CarePlanTaskCategory.MEDICATION,
                title="Night Statin & Glucose Regulation",
                instructions="Metformin 500mg after dinner + Atorvastatin 20mg at bedtime",
                frequency="DAILY",
                day_offset=0,
                due_date=today,
                status=CarePlanTaskStatus.PENDING,
            ),
        ],
        warning_signs=[
            CarePlanWarningSignGuidance(
                red_flag="Sudden acute chest pressure, radiation to left arm or jaw",
                immediate_instruction="Seek immediate Emergency Department care; call 102/108 or nearest trauma center.",
            ),
            CarePlanWarningSignGuidance(
                red_flag="Systolic BP > 170 mmHg or persistent headache/dizziness",
                immediate_instruction="Rest in seated position for 10 minutes, re-check; contact Dr. Priya Nair's clinic if sustained.",
            ),
            CarePlanWarningSignGuidance(
                red_flag="Signs of allergic reaction (facial swelling, urticaria, wheezing)",
                immediate_instruction="Stop suspicious medication immediately and seek emergency medical assistance.",
            ),
        ],
        notes="Synthesized from AIIMS Cardiology consultation and verified clinical history.",
        created_by="Dr. Priya Nair, MD",
        created_at=now,
        updated_at=now,
    )
    _global_care_plan_repo._care_plans[care_plan.id] = care_plan
    _global_care_plan_repo._patient_care_plans[care_plan.patient_id] = [care_plan.id]

    DEMO_SEEDED = True
    logger.info("HealthSetu demo dataset successfully seeded into memory.")
