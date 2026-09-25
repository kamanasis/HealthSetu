import { Medication, Allergy, TimelineEvent, AccessRequest, HospitalFacility, SafetyAlert } from '../types';

export const INITIAL_PATIENT = {
  id: 'HS-PAT-8921',
  name: 'Rohan Sharma',
  age: 42,
  gender: 'Male',
  bloodGroup: 'O Positive',
  phone: '+91 98104 22910',
  city: 'New Delhi',
  emergencyContact: 'Sunita Sharma (Spouse) · +91 98104 22911',
};

export const INITIAL_MEDICATIONS: Medication[] = [
  {
    id: 'med-1',
    name: 'Telmisartan',
    genericName: 'Telmisartan IP',
    strength: '40 mg',
    dosage: '1 Tablet',
    frequency: 'Once daily (OD)',
    route: 'Oral',
    duration: '90 Days',
    instructions: 'Take in the morning with a glass of water, before or after breakfast',
    prescribingDoctor: 'Dr. Priya Nair, MD (Cardiology)',
    hospital: 'AIIMS, New Delhi',
    datePrescribed: '12 Sep 2026',
    trustState: 'verified',
    timeOfDay: ['morning'],
    mealTiming: 'before_food',
    category: 'Antihypertensive',
  },
  {
    id: 'med-2',
    name: 'Metformin Hydrochloride',
    genericName: 'Metformin Sustained Release',
    strength: '500 mg',
    dosage: '1 Tablet',
    frequency: 'Twice daily (BD)',
    route: 'Oral',
    duration: '90 Days',
    instructions: 'Take with food to minimize gastrointestinal discomfort',
    prescribingDoctor: 'Dr. Priya Nair, MD (Cardiology)',
    hospital: 'AIIMS, New Delhi',
    datePrescribed: '12 Sep 2026',
    trustState: 'verified',
    timeOfDay: ['morning', 'evening'],
    mealTiming: 'after_food',
    category: 'Antidiabetic',
  },
  {
    id: 'med-3',
    name: 'Atorvastatin',
    genericName: 'Atorvastatin Calcium IP',
    strength: '20 mg',
    dosage: '1 Tablet',
    frequency: 'Once daily at bedtime (HS)',
    route: 'Oral',
    duration: '60 Days',
    instructions: 'Take strictly at night after dinner',
    prescribingDoctor: 'Dr. Rajesh Deshmukh',
    hospital: 'Apollo Indraprastha, Delhi',
    datePrescribed: '28 Aug 2026',
    trustState: 'verified',
    timeOfDay: ['bedtime'],
    mealTiming: 'after_food',
    category: 'Lipid-lowering agent',
  }
];

export const INITIAL_ALLERGIES: Allergy[] = [
  {
    id: 'alg-1',
    allergen: 'Penicillin / Amoxicillin',
    reaction: 'Anaphylactic reaction & severe urticaria',
    severity: 'severe',
    recordedDate: '14 Jan 2023',
    recordedBy: 'Dr. Rajesh Deshmukh (Apollo Hospital)',
    trustState: 'verified',
  },
  {
    id: 'alg-2',
    allergen: 'NSAIDs (Ibuprofen / Diclofenac)',
    reaction: 'Gastric distress & acute bronchospasm',
    severity: 'moderate',
    recordedDate: '04 May 2025',
    recordedBy: 'Dr. Priya Nair (AIIMS)',
    trustState: 'verified',
  }
];

export const INITIAL_TIMELINE: TimelineEvent[] = [
  {
    id: 'tl-1',
    date: '12 Sep 2026',
    title: 'Hypertension & Lipid Follow-Up Consultation',
    category: 'consultation',
    provider: 'Dr. Priya Nair, MD',
    facility: 'AIIMS, New Delhi',
    description: 'BP normalized to 126/82 mmHg. Blood glucose monitoring maintained. Advised lifestyle modifications and continuation of Telmisartan 40mg.',
    trustState: 'verified',
    details: {
      diagnosis: 'Essential Hypertension (controlled), Dyslipidemia',
      doctorNotes: 'Patient adhering to dietary sodium reduction. Renal function profile tests recommended in 3 months.',
      items: ['Telmisartan 40mg OD', 'Metformin 500mg BD']
    }
  },
  {
    id: 'tl-2',
    date: '02 Sep 2026',
    title: 'Extracted Prescription (Fortis Clinic)',
    category: 'prescription',
    provider: 'Dr. Vikrant Mehta',
    facility: 'Fortis Escorts Heart Institute',
    description: 'Prescription scanned via mobile camera. Awaiting patient verification.',
    trustState: 'extracted',
    details: {
      items: ['Rosuvastatin 10mg (Requires patient confirmation against Atorvastatin 20mg)']
    }
  },
  {
    id: 'tl-3',
    date: '28 Aug 2026',
    title: 'Comprehensive Lipid Panel & HbA1c',
    category: 'lab',
    provider: 'Dr. Meenakshi Sundaram',
    facility: 'Max Super Speciality Hospital, Saket',
    description: 'Total Cholesterol: 198 mg/dL, LDL: 112 mg/dL, HDL: 44 mg/dL. HbA1c: 6.8% (Target < 7.0%).',
    trustState: 'verified',
  },
  {
    id: 'tl-4',
    date: '10 Aug 2026',
    title: 'AI Longitudinal Pattern Analysis',
    category: 'triage',
    provider: 'HealthSetu Intelligence Engine',
    facility: 'HealthSetu Core',
    description: 'Historical cross-consultation correlation detected potential duplicate therapy risk between Atorvastatin and recent Statin refill.',
    trustState: 'ai-analyzed',
    details: {
      diagnosis: 'Pattern observation: Borderline lipid control stability over 180 days with no adverse liver enzyme elevation reported.'
    }
  }
];

export const INITIAL_ACCESS_REQUESTS: AccessRequest[] = [
  {
    id: 'req-1',
    doctorId: 'DOC-AIIMS-104',
    doctorName: 'Dr. Priya Nair',
    doctorRole: 'Senior Consultant Cardiologist',
    hospital: 'AIIMS, New Delhi',
    requestedScope: 'Full Clinical Record',
    purpose: 'Routine 3-month clinical review and prescription management',
    status: 'active',
    requestedAt: '25 Sep 2026, 09:30 AM',
    expiresAt: '25 Sep 2026, 09:30 PM (12 hrs remaining)',
  },
  {
    id: 'req-2',
    doctorId: 'DOC-MAX-582',
    doctorName: 'Dr. Ananya Iyer',
    doctorRole: 'Endocrinologist',
    hospital: 'Max Super Speciality Hospital, Saket',
    requestedScope: 'Prescription History Only',
    purpose: 'Consultation for glycemic control and metabolic syndrome evaluation',
    status: 'pending',
    requestedAt: '25 Sep 2026, 02:15 PM',
    expiresAt: 'Expires in 48 hours',
  }
];

export const INITIAL_HOSPITALS: HospitalFacility[] = [
  {
    id: 'hosp-1',
    name: 'Apollo Indraprastha Hospital',
    city: 'Sarita Vihar, New Delhi',
    distanceKm: 3.4,
    availableBeds: {
      icu: 7,
      emergency: 12,
      general: 45
    },
    totalBeds: 210,
    emergencyStatus: 'Available',
    specialties: ['Comprehensive Stroke Center', '24x7 Cath Lab', 'Level-1 Trauma', 'Pediatric ICU'],
    freshness: 'current',
    lastUpdated: '3 mins ago',
    phone: '+91 11 2692 5858',
    isNetworkShared: true,
  },
  {
    id: 'hosp-2',
    name: 'Max Super Speciality Hospital',
    city: 'Saket, New Delhi',
    distanceKm: 5.8,
    availableBeds: {
      icu: 2,
      emergency: 4,
      general: 19
    },
    totalBeds: 180,
    emergencyStatus: 'Available',
    specialties: ['Cardiac Emergency', 'Neurosurgery', 'Organ Transplant', 'Medical Oncology'],
    freshness: 'current',
    lastUpdated: '12 mins ago',
    phone: '+91 11 2651 5050',
    isNetworkShared: true,
  },
  {
    id: 'hosp-3',
    name: 'Fortis Escorts Heart Institute',
    city: 'Okhla Road, New Delhi',
    distanceKm: 4.1,
    availableBeds: {
      icu: 0,
      emergency: 2,
      general: 8
    },
    totalBeds: 150,
    emergencyStatus: 'Critical Capacity',
    specialties: ['Advanced Heart Failure', 'Emergency Angioplasty', 'Vascular Intervention'],
    freshness: 'stale',
    lastUpdated: '3 hours ago (Pending Verification)',
    phone: '+91 11 4713 5000',
    isNetworkShared: true,
  },
  {
    id: 'hosp-4',
    name: 'Holy Family Hospital',
    city: 'Okhla, New Delhi',
    distanceKm: 2.9,
    availableBeds: {
      icu: 4,
      emergency: 9,
      general: 32
    },
    totalBeds: 120,
    emergencyStatus: 'Available',
    specialties: ['Obstetrics & Gynecology', 'General Surgery', 'Internal Medicine', 'Dialysis'],
    freshness: 'current',
    lastUpdated: '22 mins ago',
    phone: '+91 11 2684 5201',
    isNetworkShared: true,
  }
];

export const SAFETY_DATABASE: Record<string, SafetyAlert[]> = {
  'Ibuprofen': [
    {
      id: 'alert-1',
      type: 'allergy-conflict',
      severity: 'critical',
      title: 'Documented Allergy Conflict: NSAID Sensitivity',
      description: 'Patient Rohan Sharma has a verified allergy to NSAIDs (Ibuprofen / Diclofenac) with recorded history of bronchospasm.',
      drugsInvolved: ['Ibuprofen', 'Recorded Allergy: NSAIDs'],
      source: 'Deterministic Rule'
    },
    {
      id: 'alert-2',
      type: 'drug-interaction',
      severity: 'moderate',
      title: 'Drug Interaction: Telmisartan + NSAID',
      description: 'Concomitant administration of NSAIDs with Angiotensin Receptor Blockers (Telmisartan) may diminish antihypertensive efficacy and increase risk of acute renal impairment.',
      drugsInvolved: ['Telmisartan 40mg', 'Ibuprofen'],
      source: 'Authoritative Safety Rules (RxNorm/OpenFDA)'
    }
  ],
  'Amoxicillin': [
    {
      id: 'alert-3',
      type: 'allergy-conflict',
      severity: 'critical',
      title: 'Severe Anaphylaxis Warning: Penicillin Class Allergy',
      description: 'Patient has confirmed history of anaphylactic urticaria from Penicillin/Amoxicillin documented at Apollo Hospital on 14 Jan 2023.',
      drugsInvolved: ['Amoxicillin', 'Recorded Allergy: Penicillin'],
      source: 'Deterministic Rule'
    }
  ],
  'Rosuvastatin': [
    {
      id: 'alert-4',
      type: 'duplicate-therapy',
      severity: 'critical',
      title: 'Duplicate Statin Therapy Detected',
      description: 'Patient is already actively taking Atorvastatin 20mg daily. Prescribing Rosuvastatin introduces duplicative HMG-CoA reductase inhibition and increases risk of severe rhabdomyolysis.',
      drugsInvolved: ['Atorvastatin 20mg', 'Rosuvastatin'],
      source: 'Authoritative Safety Rules (RxNorm/OpenFDA)'
    }
  ]
};
