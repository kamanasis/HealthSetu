/**
 * HealthSetu Backend API Service (Phase 1, 2 & 3 Integration)
 *
 * Implements client contracts for:
 * - Health & Readiness probes (/api/v1/health, /api/v1/ready)
 * - Authentication & Identity (/api/v1/auth/login, /api/v1/auth/me, /api/v1/auth/logout)
 * - Consent Management (/api/v1/consents, /api/v1/consents/{id}/revoke)
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

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

export interface BackendConsent {
  id: string;
  patient_id: string;
  grantee_id: string;
  purpose: 'care_delivery' | 'emergency_access' | 'second_opinion' | 'administrative' | 'research';
  scope: 'clinical_records' | 'prescriptions' | 'medications' | 'care_plan' | 'documents' | 'discharge_summary' | 'all_records';
  status: 'ACTIVE' | 'REVOKED' | 'EXPIRED' | 'PENDING' | 'DENIED';
  granted_at: string;
  effective_from: string;
  expires_at?: string;
  revoked_at?: string;
  revocation_reason?: string;
  notes?: string;
}

class HealthSetuApiClient {
  private token: string | null = null;

  constructor() {
    this.token = typeof window !== 'undefined' ? localStorage.getItem('healthsetu_token') : null;
  }

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem('healthsetu_token', token);
    } else {
      localStorage.removeItem('healthsetu_token');
    }
  }

  getToken(): string | null {
    return this.token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<{ data?: T; error?: string }> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {}),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers,
      });

      const json = await response.json().catch(() => null);

      if (!response.ok) {
        const errorMsg = json?.error?.message || json?.detail || `HTTP ${response.status}: Request failed`;
        return { error: errorMsg };
      }

      return { data: (json?.data !== undefined ? json.data : json) as T };
    } catch (err: any) {
      return { error: err.message || 'Unable to connect to HealthSetu backend service' };
    }
  }

  // Probe Endpoints (Phase 1)
  async checkHealth(): Promise<BackendHealthResponse | null> {
    try {
      const res = await fetch(`${API_BASE_URL}/health`, { method: 'GET' });
      if (res.ok) {
        const json = await res.json();
        return json.data || json;
      }
      return null;
    } catch {
      return null;
    }
  }

  async checkReadiness(): Promise<{ ready: boolean; details?: any } | null> {
    try {
      const res = await fetch(`${API_BASE_URL}/ready`, { method: 'GET' });
      const json = await res.json().catch(() => null);
      return { ready: res.ok, details: json?.data || json };
    } catch {
      return null;
    }
  }

  // Authentication Endpoints (Phase 2)
  async login(identifier: string, password: string): Promise<{ tokens?: AuthTokens; error?: string }> {
    const res = await this.request<AuthTokens>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ identifier, password }),
    });

    if (res.data) {
      this.setToken(res.data.access_token);
      return { tokens: res.data };
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

  // Consent Management Endpoints (Phase 3)
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
}

export const apiClient = new HealthSetuApiClient();
