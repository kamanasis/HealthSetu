export type Role = 'landing' | 'patient' | 'doctor' | 'hospital';

export type TrustState = 'verified' | 'extracted' | 'ai-analyzed' | 'raw';
export type FreshnessState = 'current' | 'stale' | 'unknown';

export interface Medication {
  id: string;
  name: string;
  genericName: string;
  strength: string;
  dosage: string;
  frequency: string;
  route: string;
  duration: string;
  instructions: string;
  prescribingDoctor: string;
  hospital: string;
  datePrescribed: string;
  trustState: TrustState;
  timeOfDay: ('morning' | 'afternoon' | 'evening' | 'bedtime')[];
  mealTiming: 'before_food' | 'after_food' | 'with_food' | 'empty_stomach';
  category: string;
}

export interface Allergy {
  id: string;
  allergen: string;
  reaction: string;
  severity: 'mild' | 'moderate' | 'severe';
  recordedDate: string;
  recordedBy: string;
  trustState: TrustState;
}

export interface TimelineEvent {
  id: string;
  date: string;
  title: string;
  category: 'prescription' | 'consultation' | 'triage' | 'lab' | 'discharge';
  provider: string;
  facility: string;
  description: string;
  trustState: TrustState;
  details?: {
    diagnosis?: string;
    doctorNotes?: string;
    items?: string[];
  };
}

export interface AccessRequest {
  id: string;
  doctorId: string;
  doctorName: string;
  doctorRole: string;
  hospital: string;
  requestedScope: 'Full Clinical Record' | 'Prescription History Only' | 'Emergency Access';
  purpose: string;
  status: 'pending' | 'active' | 'revoked' | 'expired';
  requestedAt: string;
  expiresAt: string;
}

export interface HospitalFacility {
  id: string;
  name: string;
  city: string;
  distanceKm: number;
  availableBeds: {
    icu: number;
    emergency: number;
    general: number;
  };
  totalBeds: number;
  emergencyStatus: 'Available' | 'Critical Capacity' | 'Diverting';
  specialties: string[];
  freshness: FreshnessState;
  lastUpdated: string;
  phone: string;
  isNetworkShared: boolean;
}

export interface SafetyAlert {
  id: string;
  type: 'drug-interaction' | 'allergy-conflict' | 'duplicate-therapy' | 'food-precaution';
  severity: 'critical' | 'moderate' | 'advisory';
  title: string;
  description: string;
  drugsInvolved: string[];
  source: 'Authoritative Safety Rules (RxNorm/OpenFDA)' | 'Deterministic Rule' | 'AI-Observed Pattern';
}
