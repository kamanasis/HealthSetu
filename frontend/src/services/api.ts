/**
 * HealthSetu Complete Backend API Service
 *
 * Full client integration with FastAPI backend:
 * - Phase 1: Health & Readiness probes (/api/v1/health, /api/v1/ready)
 * - Phase 2: Authentication & Token Lifecycle (/api/v1/auth/login, /api/v1/auth/me, /api/v1/auth/logout)
 * - Phase 3: Consent & Access Controls (/api/v1/consents, /api/v1/consents/{id}/revoke)
 * - Phase 4: Patient Profile & Clinical Records (Demographics, Allergies, Vitals, Conditions)
 * - Phase 5: Document Upload & Human-in-the-Loop OCR Extraction (/api/v1/patients/{id}/documents)
 * - Phase 6: Longitudinal Medications & Verification (/api/v1/patients/{id}/medications)
 * - Phase 7: Deterministic & External Medication Safety Check (/api/v1/patients/{id}/medication-safety)
 * - Phase 8: Clinical Triage & SBAR Synthesizer (/api/v1/patients/{id}/triage, /api/v1/patients/{id}/sbar)
 * - Phase 9: Personalized Care Plans & Warning Signs (/api/v1/patients/{id}/care-plans)
 * - Phase 10: Doctor Clinical Workspace (/api/v1/patients/{id}/clinical-workspace)
 * - Phase 11 & 12: Hospital Directory & Emergency Bed Discovery (/api/v1/facilities, /api/v1/facilities/discover)
 */

import type { Medication, Allergy, TimelineEvent, AccessRequest, HospitalFacility, SafetyAlert } from '../types';

// Support VITE_API_BASE_URL, VITE_API_URL, production Railway fallback, relative /api/v1, or localhost:8000
const rawApiUrl = (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL) as string | undefined;
const API_BASE_URL = rawApiUrl
  ? (rawApiUrl.endsWith('/api/v1') ? rawApiUrl : `${rawApiUrl.replace(/\/+$/, '')}/api/v1`)
  : typeof window !== 'undefined' && window.location.hostname.includes('vercel.app')
  ? 'https://healthsetu-production.up.railway.app/api/v1'
  : typeof window !== 'undefined' && window.location.origin
  ? '/api/v1'
  : 'http://localhost:8000/api/v1';

export interface BackendHealthResponse {
  status: 'ok' | 'degraded' | 'error';
  version?: string;
  app?: string;
  timestamp?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface BackendUserSummary {
  id: string;
  role: 'PATIENT' | 'DOCTOR' | 'ADMIN';
  identifier?: string;
}

export interface BackendConsent {
  id: string;
  patient_id: string;
  grantee_id: string;
  purpose: string;
  scope: string;
  status: 'ACTIVE' | 'REVOKED' | 'EXPIRED' | 'PENDING' | 'DENIED';
  granted_at: string;
  effective_from: string;
  expires_at?: string;
  revoked_at?: string;
  revocation_reason?: string;
  notes?: string;
}

export interface BackendPatient {
  id: string;
  user_id?: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  sex: string;
  status: string;
  phone?: string;
  email?: string;
  preferred_language?: string;
}

export interface BackendPatientMedication {
  id: string;
  patient_id: string;
  drug_name_raw: string;
  strength_raw?: string;
  dosage_form_raw?: string;
  route_raw?: string;
  frequency_raw?: string;
  duration_raw?: string;
  instructions_raw?: string;
  status: string;
  verification_status: string;
  source: string;
  created_at?: string;
}

export interface BackendAllergy {
  id: string;
  patient_id: string;
  allergen: string;
  reaction?: string;
  severity: 'MILD' | 'MODERATE' | 'SEVERE';
  status: string;
  recorded_by?: string;
  created_at?: string;
}

export interface BackendVital {
  id: string;
  patient_id: string;
  vital_type: string;
  value: number;
  unit: string;
  measured_at: string;
  source: string;
  recorded_by?: string;
}

export interface BackendCarePlan {
  id?: string;
  care_plan_id?: string;
  patient_id: string;
  title: string;
  status: string;
  start_date: string;
  end_date: string;
  goals: Array<{ id: string; description: string; target_date?: string; status: string }>;
  tasks: Array<{
    id: string;
    category: string;
    title: string;
    instructions: string;
    frequency: string;
    day_offset: number;
    due_date?: string;
    status: string;
  }>;
  warning_signs: Array<{ red_flag: string; immediate_instruction: string }>;
  notes?: string;
}

export interface BackendSafetyEvaluation {
  evaluation_id: string;
  status: 'CLEAR' | 'ALERT' | 'CONTRAINDICATED' | 'EVALUATION_ERROR';
  alerts: Array<{
    alert_id: string;
    severity: string;
    title: string;
    description: string;
    medications_involved: Array<Record<string, string>>;
    source: string;
  }>;
  disclaimer: string;
}

export interface BackendFacilityItem {
  id: string;
  name: string;
  facility_type: string;
  status: string;
  phone?: string;
  email?: string;
  address?: {
    city?: string;
    line?: string;
    latitude?: number;
    longitude?: number;
  };
  operational_metadata?: {
    available_beds?: { icu?: number; emergency?: number; general?: number };
    total_beds?: number;
    emergency_status?: 'Available' | 'Critical Capacity' | 'Diverting';
    specialties?: string[];
    distance_km?: number;
    is_network_shared?: boolean;
  };
}

class HealthSetuApiClient {
  private token: string | null = null;
  private activeRole: 'PATIENT' | 'DOCTOR' | 'ADMIN' | null = null;
  private lastPingMs: number | null = null;
  private isConnected: boolean | null = null;

  constructor() {
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('healthsetu_token');
      this.activeRole = (localStorage.getItem('healthsetu_role') as any) || null;
    }
  }

  setToken(token: string | null, role?: 'PATIENT' | 'DOCTOR' | 'ADMIN') {
    this.token = token;
    if (token) {
      localStorage.setItem('healthsetu_token', token);
      if (role) {
        this.activeRole = role;
        localStorage.setItem('healthsetu_role', role);
      }
    } else {
      localStorage.removeItem('healthsetu_token');
      localStorage.removeItem('healthsetu_role');
      this.activeRole = null;
    }
  }

  getToken(): string | null {
    return this.token;
  }

  getActiveRole(): string | null {
    return this.activeRole;
  }

  getLastPing(): number | null {
    return this.lastPingMs;
  }

  getConnectionStatus(): boolean | null {
    return this.isConnected;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<{ data?: T; error?: string; status?: number }> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...((options.headers as Record<string, string>) || {}),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const t0 = performance.now();
    try {
      // First try relative /api/v1 (proxied by Vite or on production host)
      let res = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers,
      }).catch(async () => {
        // If relative proxy failed (e.g. running standalone), try direct port 8000
        return await fetch(`http://localhost:8000/api/v1${endpoint}`, {
          ...options,
          headers,
        });
      });

      this.lastPingMs = Math.round(performance.now() - t0);
      this.isConnected = res.ok;

      const contentType = res.headers.get('content-type') || '';
      if (contentType.includes('text/html')) {
        this.isConnected = false;
        return { error: 'API service not deployed on this domain', status: 404 };
      }

      const json = await res.json().catch(() => null);

      if (!res.ok) {
        const errorMsg =
          json?.error?.message ||
          json?.detail ||
          (typeof json?.error === 'string' ? json.error : `HTTP ${res.status}: Request failed`);
        return { error: errorMsg, status: res.status };
      }

      return {
        data: (json?.data !== undefined ? json.data : json) as T,
        status: res.status,
      };
    } catch (err: any) {
      this.isConnected = false;
      return {
        error: err.message || 'Unable to connect to HealthSetu backend service on port 8000',
        status: 0,
      };
    }
  }

  // =========================================================================
  // Phase 1: Probes
  // =========================================================================
  async checkHealth(): Promise<{ ok: boolean; data?: BackendHealthResponse; latencyMs?: number }> {
    const t0 = performance.now();
    try {
      const res = await fetch(`${API_BASE_URL}/health`, { method: 'GET' }).catch(() =>
        fetch(`http://localhost:8000/api/v1/health`, { method: 'GET' })
      );
      const latencyMs = Math.round(performance.now() - t0);
      this.lastPingMs = latencyMs;
      this.isConnected = res.ok;

      if (res.ok) {
        const json = await res.json();
        return { ok: true, data: json.data || json, latencyMs };
      }
      return { ok: false, latencyMs };
    } catch {
      this.isConnected = false;
      return { ok: false };
    }
  }

  async checkReadiness(): Promise<{ ready: boolean; details?: any }> {
    try {
      const res = await fetch(`${API_BASE_URL}/ready`, { method: 'GET' }).catch(() =>
        fetch(`http://localhost:8000/api/v1/ready`, { method: 'GET' })
      );
      const json = await res.json().catch(() => null);
      return { ready: res.ok, details: json?.data || json };
    } catch {
      return { ready: false };
    }
  }

  // =========================================================================
  // Phase 2: Authentication
  // =========================================================================
  async login(
    identifier: string,
    password: string
  ): Promise<{ tokens?: AuthTokens; user?: BackendUserSummary; error?: string }> {
    const res = await this.request<{
      access_token: string;
      refresh_token: string;
      token_type: string;
      expires_in: number;
      user: BackendUserSummary;
    }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ identifier, password }),
    });

    if (res.data) {
      this.setToken(res.data.access_token, res.data.user?.role);
      return {
        tokens: res.data,
        user: res.data.user,
      };
    }
    return { error: res.error };
  }

  async logout(): Promise<void> {
    if (this.token) {
      await this.request('/auth/logout', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: this.token }),
      }).catch(() => null);
    }
    this.setToken(null);
  }

  async getCurrentUser(): Promise<any> {
    return this.request('/auth/me', { method: 'GET' });
  }

  /**
   * Ensures an active authenticated session for the specified role.
   * Auto-authenticates using demo credentials if not already logged in with that role.
   */
  async ensureDemoSession(role: 'PATIENT' | 'DOCTOR' | 'ADMIN' = 'PATIENT'): Promise<string | null> {
    if (this.token && this.activeRole === role) {
      return this.token;
    }

    const emailMap: Record<string, string> = {
      PATIENT: 'patient@healthsetu.org',
      DOCTOR: 'doctor@healthsetu.org',
      ADMIN: 'admin@healthsetu.org',
    };

    const res = await this.login(emailMap[role] || 'patient@healthsetu.org', 'StrongP@ssw0rd123!');
    if (res.tokens) {
      return res.tokens.access_token;
    }
    return null;
  }

  // =========================================================================
  // Phase 3: Consent Management
  // =========================================================================
  async listConsents(): Promise<{ consents?: BackendConsent[]; error?: string }> {
    const res = await this.request<{ items: BackendConsent[] }>('/consents', { method: 'GET' });
    if (res.data) {
      return { consents: res.data.items || [] };
    }
    return { error: res.error };
  }

  async createConsent(payload: {
    grantee_id: string;
    purpose: string;
    scope: string;
    notes?: string;
    expires_at?: string;
  }): Promise<{ consent?: BackendConsent; error?: string }> {
    const res = await this.request<BackendConsent>('/consents', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (res.data) {
      return { consent: res.data };
    }
    return { error: res.error };
  }

  async revokeConsent(consentId: string, reason?: string): Promise<{ consent?: BackendConsent; error?: string }> {
    const res = await this.request<BackendConsent>(`/consents/${consentId}/revoke`, {
      method: 'POST',
      body: JSON.stringify({ reason: reason || 'Revoked by patient via HealthSetu portal' }),
    });
    if (res.data) {
      return { consent: res.data };
    }
    return { error: res.error };
  }

  // =========================================================================
  // Phase 4: Patient Clinical Records
  // =========================================================================
  async getPatient(patientId: string): Promise<{ patient?: BackendPatient; error?: string }> {
    const res = await this.request<BackendPatient>(`/patients/${patientId}`, { method: 'GET' });
    return { patient: res.data, error: res.error };
  }

  async getPatientClinicalSummary(patientId: string): Promise<{ summary?: any; error?: string }> {
    const res = await this.request<any>(`/patients/${patientId}/clinical-summary`, { method: 'GET' });
    return { summary: res.data, error: res.error };
  }

  async getPatientMedications(
    patientId: string
  ): Promise<{ medications?: BackendPatientMedication[]; error?: string }> {
    const res = await this.request<{ items: BackendPatientMedication[] }>(
      `/patients/${patientId}/medications`,
      { method: 'GET' }
    );
    return { medications: res.data?.items || [], error: res.error };
  }

  async getPatientAllergies(patientId: string): Promise<{ allergies?: BackendAllergy[]; error?: string }> {
    const res = await this.request<{ items: BackendAllergy[] }>(
      `/patients/${patientId}/allergies`,
      { method: 'GET' }
    );
    return { allergies: res.data?.items || [], error: res.error };
  }

  async getPatientVitals(patientId: string): Promise<{ vitals?: BackendVital[]; error?: string }> {
    const res = await this.request<{ items: BackendVital[] }>(
      `/patients/${patientId}/vitals`,
      { method: 'GET' }
    );
    return { vitals: res.data?.items || [], error: res.error };
  }

  // =========================================================================
  // Phase 5: Document Upload & Extraction
  // =========================================================================
  async uploadMedicalDocument(
    patientId: string,
    file: File | Blob,
    documentType: string = 'PRESCRIPTION'
  ): Promise<{ document?: any; error?: string }> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);

    const headers: Record<string, string> = {};
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    try {
      const res = await fetch(`${API_BASE_URL}/patients/${patientId}/documents`, {
        method: 'POST',
        headers,
        body: formData,
      });

      const json = await res.json().catch(() => null);
      if (!res.ok) {
        return { error: json?.error?.message || `HTTP ${res.status}: Upload failed` };
      }
      return { document: json?.data || json };
    } catch (err: any) {
      return { error: err.message || 'Network error during document upload' };
    }
  }

  // =========================================================================
  // Phase 7: Medication Safety Checking
  // =========================================================================
  async checkProspectiveMedications(
    patientId: string,
    drugNames: Array<{ name: string; strength?: string; route?: string }>
  ): Promise<{ evaluation?: BackendSafetyEvaluation; error?: string }> {
    const payload = {
      medications: drugNames.map(d => ({
        name: d.name,
        strength: d.strength || 'Standard',
        route: d.route || 'Oral',
      })),
      include_current_medications: true,
    };

    const res = await this.request<BackendSafetyEvaluation>(
      `/patients/${patientId}/medication-safety/check-medications`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    );

    return { evaluation: res.data, error: res.error };
  }

  async checkActiveMedicationsSafety(
    patientId: string
  ): Promise<{ evaluation?: BackendSafetyEvaluation; error?: string }> {
    const res = await this.request<BackendSafetyEvaluation>(
      `/patients/${patientId}/medication-safety/check`,
      {
        method: 'POST',
        body: JSON.stringify({ include_all_active: true }),
      }
    );
    return { evaluation: res.data, error: res.error };
  }

  // =========================================================================
  // Phase 9: Personalized Care Plans
  // =========================================================================
  async getPatientCarePlans(patientId: string): Promise<{ carePlans?: BackendCarePlan[]; error?: string }> {
    const res = await this.request<{ items: BackendCarePlan[] }>(
      `/patients/${patientId}/care-plans`,
      { method: 'GET' }
    );
    return { carePlans: res.data?.items || [], error: res.error };
  }

  // =========================================================================
  // Phase 10: Doctor Clinical Workspace
  // =========================================================================
  async getDoctorWorkspace(patientId: string): Promise<{ workspace?: any; error?: string }> {
    const res = await this.request<any>(
      `/patients/${patientId}/clinical-workspace`,
      { method: 'GET' }
    );
    return { workspace: res.data, error: res.error };
  }

  async createPrescription(payload: any): Promise<{ prescription?: any; error?: string }> {
    const res = await this.request<any>('/prescriptions', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return { prescription: res.data, error: res.error };
  }

  // =========================================================================
  // Phase 11 & 12: Facilities & Capacity Discovery
  // =========================================================================
  async searchFacilities(name?: string): Promise<{ facilities?: BackendFacilityItem[]; error?: string }> {
    const q = name ? `?name=${encodeURIComponent(name)}` : '';
    const res = await this.request<{ items: BackendFacilityItem[] }>(
      `/facilities/search${q}`,
      { method: 'GET' }
    );
    return { facilities: res.data?.items || [], error: res.error };
  }

  async discoverFacilities(params?: {
    latitude?: number;
    longitude?: number;
    radius_km?: number;
    facility_type?: string;
  }): Promise<{ discovery?: any; error?: string }> {
    const searchParams = new URLSearchParams();
    if (params?.latitude) searchParams.set('latitude', params.latitude.toString());
    if (params?.longitude) searchParams.set('longitude', params.longitude.toString());
    if (params?.radius_km) searchParams.set('radius_km', params.radius_km.toString());
    if (params?.facility_type) searchParams.set('facility_type', params.facility_type);

    const q = searchParams.toString() ? `?${searchParams.toString()}` : '';
    const res = await this.request<any>(`/facilities/discover${q}`, { method: 'GET' });
    return { discovery: res.data, error: res.error };
  }
}

export const apiClient = new HealthSetuApiClient();
