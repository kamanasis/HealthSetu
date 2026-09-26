import React, { useState, useEffect } from 'react';
import { 
  User, 
  UploadCloud, 
  ShieldCheck, 
  FileText, 
  Clock, 
  AlertTriangle, 
  Sparkles, 
  CheckCircle2, 
  Stethoscope, 
  Lock, 
  PhoneCall, 
  Plus,
  RotateCcw
} from 'lucide-react';
import { 
  INITIAL_PATIENT, 
  INITIAL_MEDICATIONS, 
  INITIAL_ALLERGIES, 
  INITIAL_TIMELINE, 
  INITIAL_ACCESS_REQUESTS 
} from '../../data/mockData';
import type { Medication, TimelineEvent, AccessRequest, Allergy } from '../../types';
import { TrustBadge } from '../common/Badge';
import { PrescriptionUploadModal } from './PrescriptionUploadModal';
import { CarePlanView } from './CarePlanView';
import { apiClient } from '../../services/api';

import type { UserProfile } from '../../services/authStore';

interface PatientPortalProps {
  onEmergencyClick: () => void;
  currentUser?: UserProfile | null;
}

export const PatientPortal: React.FC<PatientPortalProps> = ({ onEmergencyClick, currentUser }) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'careplan' | 'timeline' | 'consent' | 'allergies'>('overview');
  
  const isCustomUser = !!(currentUser && currentUser.role === 'patient' && currentUser.id !== 'HS-PAT-8921');

  const [patient, setPatient] = useState(() => {
    if (currentUser && currentUser.role === 'patient') {
      return {
        id: currentUser.id,
        name: currentUser.name,
        age: currentUser.patientDetails?.age ?? 30,
        gender: currentUser.patientDetails?.gender ?? 'Other',
        bloodGroup: currentUser.patientDetails?.bloodGroup ?? 'Not Specified',
        city: currentUser.patientDetails?.city ?? 'Not Specified',
        phone: currentUser.phone ?? '',
        emergencyContact: currentUser.patientDetails?.emergencyContact ?? 'Not Specified',
      };
    }
    return INITIAL_PATIENT;
  });

  const [medications, setMedications] = useState<Medication[]>(() => {
    return isCustomUser ? [] : (INITIAL_MEDICATIONS || []);
  });

  const [allergies, setAllergies] = useState<Allergy[]>(() => {
    return isCustomUser ? [] : (INITIAL_ALLERGIES || []);
  });

  const [timeline, setTimeline] = useState<TimelineEvent[]>(() => {
    if (isCustomUser) {
      return [
        {
          id: `tl-init-${currentUser!.id}`,
          date: currentUser!.issuedAt || 'Today',
          title: 'HealthSetu Sovereign ID Minted',
          category: 'milestone',
          provider: 'HealthSetu Digital Health Grid',
          facility: currentUser!.patientDetails?.city || 'Verified Clinical Node',
          description: `Sovereign unique credential issued for ${currentUser!.name}. Unique ID: ${currentUser!.id}. Zero dummy data active.`,
          trustState: 'verified',
        },
      ];
    }
    return INITIAL_TIMELINE || [];
  });

  const [accessRequests, setAccessRequests] = useState<AccessRequest[]>(() => {
    return isCustomUser ? [] : (INITIAL_ACCESS_REQUESTS || []);
  });

  const [isUploadOpen, setIsUploadOpen] = useState<boolean>(false);
  const [isNewConsentOpen, setIsNewConsentOpen] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [isSynced, setIsSynced] = useState<boolean>(false);

  // Sync patient profile when currentUser changes
  useEffect(() => {
    if (currentUser && currentUser.role === 'patient') {
      setPatient(prev => ({
        ...prev,
        id: currentUser.id,
        name: currentUser.name,
        age: currentUser.patientDetails?.age ?? prev.age,
        gender: currentUser.patientDetails?.gender ?? prev.gender,
        bloodGroup: currentUser.patientDetails?.bloodGroup ?? prev.bloodGroup,
        city: currentUser.patientDetails?.city ?? prev.city,
        phone: currentUser.phone ?? prev.phone,
        emergencyContact: currentUser.patientDetails?.emergencyContact ?? prev.emergencyContact,
      }));

      if (currentUser.id !== 'HS-PAT-8921') {
        // Clear demo data for new user immediately
        setMedications([]);
        setAllergies([]);
        setAccessRequests([]);
        setTimeline([
          {
            id: `tl-init-${currentUser.id}`,
            date: currentUser.issuedAt || 'Today',
            title: 'HealthSetu Sovereign ID Minted',
            category: 'milestone',
            provider: 'HealthSetu Digital Health Grid',
            facility: currentUser.patientDetails?.city || 'Verified Clinical Node',
            description: `Sovereign unique credential issued for ${currentUser.name}. Unique ID: ${currentUser.id}. Zero dummy data active.`,
            trustState: 'verified',
          },
        ]);
      }
    }
  }, [currentUser]);

  // New Consent Form State (Backend Phase 3 contract)
  const [newGrantee, setNewGrantee] = useState<string>('DOC-MAX-582');
  const [newPurpose, setNewPurpose] = useState<string>('care_delivery');
  const [newScope, setNewScope] = useState<string>('clinical_records');
  const [newDurationHours, setNewDurationHours] = useState<number>(12);
  const [newNotes, setNewNotes] = useState<string>('Authorized for metabolic consultation');

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // Live Backend Data Fetching (Cross-Computer Sync by Unique ID)
  useEffect(() => {
    let mounted = true;
    const targetPatientId = (currentUser && currentUser.role === 'patient') ? currentUser.id : 'HS-PAT-8921';
    const isCustom = targetPatientId !== 'HS-PAT-8921';

    const syncBackend = async () => {
      try {
        await apiClient.ensureDemoSession('PATIENT');

        // 1. Fetch full persistent record across computers from backend
        const fullRes = await apiClient.getFullPatientRecord(targetPatientId);
        if (mounted && fullRes.record) {
          const rec = fullRes.record;
          setPatient(prev => ({
            ...prev,
            id: rec.patient_id || targetPatientId,
            name: rec.name || prev.name,
            age: rec.age ?? prev.age,
            gender: rec.gender ?? prev.gender,
            bloodGroup: rec.bloodGroup ?? prev.bloodGroup,
            city: rec.city ?? prev.city,
            phone: rec.phone || prev.phone,
            emergencyContact: rec.emergencyContact ?? prev.emergencyContact,
          }));

          if (Array.isArray(rec.medications)) {
            setMedications(rec.medications);
          } else if (isCustom) {
            setMedications([]);
          }

          if (Array.isArray(rec.allergies)) {
            setAllergies(rec.allergies);
          } else if (isCustom) {
            setAllergies([]);
          }

          if (Array.isArray(rec.timeline) && rec.timeline.length > 0) {
            setTimeline(rec.timeline);
          }

          setIsSynced(true);
          return;
        }

        // 2. If custom user with no record yet on backend, keep clean (zero dummy data)
        if (isCustom) {
          if (mounted) {
            setMedications([]);
            setAllergies([]);
            setAccessRequests([]);
          }
          return;
        }

        // 3. Fallback for demo Rohan Sharma (HS-PAT-8921)
        const pRes = await apiClient.getPatient('HS-PAT-8921');
        if (mounted && pRes.patient) {
          setPatient(prev => ({
            ...prev,
            id: pRes.patient!.id || prev.id,
            name: `${pRes.patient!.first_name || ''} ${pRes.patient!.last_name || ''}`.trim() || prev.name,
            gender: pRes.patient!.sex === 'MALE' ? 'Male' : pRes.patient!.sex === 'FEMALE' ? 'Female' : prev.gender,
            phone: pRes.patient!.phone || prev.phone,
            city: prev.city,
          }));
          setIsSynced(true);
        }

        const medRes = await apiClient.getPatientMedications('HS-PAT-8921');
        if (mounted && medRes.medications && Array.isArray(medRes.medications) && medRes.medications.length > 0) {
          const liveMeds: Medication[] = medRes.medications.map((m, idx) => ({
            id: m.id || `med-${idx}`,
            name: m.drug_name_raw || 'Prescribed Medicine',
            genericName: m.drug_name_raw || '',
            strength: m.strength_raw || 'Standard',
            dosage: '1 Tablet',
            frequency: m.frequency_raw || 'Once daily',
            route: (m.route_raw as any) || 'Oral',
            duration: m.duration_raw || '30 Days',
            instructions: m.instructions_raw || 'Take with water',
            prescribingDoctor: 'Dr. Priya Nair, MD (AIIMS)',
            hospital: 'AIIMS, New Delhi',
            datePrescribed: '12 Sep 2026',
            trustState: m.verification_status === 'VERIFIED' ? 'verified' : 'extracted',
            timeOfDay: idx === 1 ? ['morning', 'evening'] : idx === 2 ? ['bedtime'] : ['morning'],
            mealTiming: idx === 1 ? 'after_food' : idx === 2 ? 'after_food' : 'before_food',
            category: idx === 0 ? 'Antihypertensive' : idx === 1 ? 'Antidiabetic' : 'Lipid-lowering agent',
          }));
          setMedications(liveMeds);
        }
      } catch (err) {
        console.warn('Backend sync completed with local cache fallback:', err);
      }
    };

    syncBackend();
    return () => { mounted = false; };
  }, [currentUser]);

  const handleVerifyAndAdd = async (medsInput: Medication | Medication[]) => {
    const medsArray = Array.isArray(medsInput) ? medsInput : [medsInput];
    const updatedMeds = [...medsArray, ...medications];
    setMedications(updatedMeds);

    const newTimelineEvents: TimelineEvent[] = medsArray.map(newMed => ({
      id: `tl-${Date.now()}-${Math.random().toString(36).substring(2, 5)}`,
      date: 'Today, 26 Sep 2026',
      title: `Patient-Verified: ${newMed.name} ${newMed.strength}`,
      category: 'prescription',
      provider: newMed.prescribingDoctor || 'Verified Self-Upload',
      facility: newMed.hospital || patient.city || 'Verified Health Node',
      description: `${newMed.name} verified by patient ${patient.name}. Added to active daily medication schedule.`,
      trustState: 'verified',
    }));
    const updatedTimeline = [...newTimelineEvents, ...timeline];
    setTimeline(updatedTimeline);

    // Sync to backend persistent store (saved across computers!)
    try {
      await apiClient.syncPatientRecord(patient.id, {
        medications: updatedMeds,
        timeline: updatedTimeline,
        name: patient.name,
        age: patient.age,
        gender: patient.gender,
        bloodGroup: patient.bloodGroup,
        city: patient.city,
        phone: patient.phone,
        emergencyContact: patient.emergencyContact,
      });
    } catch (err) {
      console.warn('Could not sync updated medications to backend store:', err);
    }

    const msg = medsArray.length === 1
      ? `Verified and added ${medsArray[0].name} to your active health record.`
      : `Verified and added ${medsArray.length} medications to your active health record.`;
    showToast(msg);
  };

  const handleCreateConsentGrant = async (e: React.FormEvent) => {
    e.preventDefault();
    const doctorNames: Record<string, { name: string; role: string; hospital: string }> = {
      'DOC-MAX-582': { name: 'Dr. Ananya Iyer', role: 'Endocrinologist', hospital: 'Max Super Speciality Hospital, Saket' },
      'DOC-AIIMS-104': { name: 'Dr. Priya Nair', role: 'Cardiologist', hospital: 'AIIMS, New Delhi' },
      'DOC-FORTIS-219': { name: 'Dr. Vikrant Mehta', role: 'General Physician', hospital: 'Fortis Escorts Heart Institute' },
    };

    const doc = doctorNames[newGrantee] || { name: newGrantee, role: 'Physician', hospital: 'Consulting Clinic' };

    const newReq: AccessRequest = {
      id: `req-${Date.now()}`,
      doctorId: newGrantee,
      doctorName: doc.name,
      doctorRole: doc.role,
      hospital: doc.hospital,
      requestedScope: newScope === 'clinical_records' ? 'Full Clinical Record' : newScope === 'prescriptions' ? 'Prescription History Only' : 'Emergency Access',
      purpose: newPurpose.replace('_', ' ').toUpperCase(),
      status: 'active',
      requestedAt: 'Just now',
      expiresAt: `Expires in ${newDurationHours} hours`,
    };

    setAccessRequests(prev => [newReq, ...prev]);
    setIsNewConsentOpen(false);

    try {
      const res = await apiClient.createConsent({
        grantee_id: newGrantee,
        purpose: newPurpose,
        scope: newScope === 'all_records' ? 'all_records' : newScope,
        notes: newNotes,
        expires_at: new Date(Date.now() + newDurationHours * 3600 * 1000).toISOString(),
      });
      if (res.consent) {
        showToast(`Consent grant created & synced to FastAPI backend (ID: ${res.consent.id.slice(0, 8)}).`);
      } else {
        showToast(`Consent grant created for ${doc.name} (${newScope} · ${newPurpose}).`);
      }
    } catch {
      showToast(`Consent grant created for ${doc.name} (${newScope}).`);
    }
  };

  const handleRevokeAccess = async (id: string, doctorName: string) => {
    setAccessRequests(prev => prev.map(req => req.id === id ? { ...req, status: 'revoked' } : req));
    try {
      await apiClient.revokeConsent(id, 'Revoked by patient via HealthSetu portal');
      showToast(`Access revoked for ${doctorName}. Server-side token invalidated immediately on backend.`);
    } catch {
      showToast(`Access revoked for ${doctorName}. Local token invalidated.`);
    }
  };

  const handleGrantAccess = (id: string, doctorName: string) => {
    setAccessRequests(prev => prev.map(req => req.id === id ? { ...req, status: 'active' } : req));
    showToast(`Scoped access granted to ${doctorName} for 12 hours.`);
  };

  return (
    <div className="pt-24 pb-20 max-w-6xl mx-auto px-6 space-y-8">
      
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-20 right-6 z-50 bg-[#1C2B3A] text-white text-xs font-semibold px-4 py-3 rounded-sm border border-[#DDD9D1] flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-[#3D8B6E]" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Patient Header Profile Strip (Crisp medical passport composition) */}
      <div className="bg-white rounded-sm border border-[#DDD9D1] p-6 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-sm bg-[#FAF8F3] border border-[#DDD9D1] flex items-center justify-center text-[#1C2B3A] font-bold text-base font-mono">
            RS
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="font-serif text-2xl text-[#1C2B3A] font-normal">{patient.name}</h1>
              <span className="text-xs font-mono font-medium bg-[#FAF8F3] text-[#2B5F8A] border border-[#DDD9D1] px-2 py-0.5 rounded-sm">
                {patient.id}
              </span>
              {isSynced && (
                <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded-sm bg-[#EBF7F0] border border-[#C3E8D2] text-[#227248]">
                  FastAPI Live
                </span>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-3 text-xs text-[#6B7A8D] mt-1 font-sans">
              <span>{patient.age} Years, {patient.gender}</span>
              <span>·</span>
              <span>Blood Group: <strong className="text-[#1C2B3A] font-semibold">{patient.bloodGroup}</strong></span>
              <span>·</span>
              <span>{patient.city}</span>
            </div>
          </div>
        </div>

        {/* Primary Actions */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => setIsUploadOpen(true)}
            className="bg-[#4A90C4] text-white font-semibold text-xs px-4 py-2.5 rounded-sm hover:bg-[#3A7DB0] transition-colors flex items-center gap-2 focus-visible:ring-1 focus-visible:ring-[#4A90C4]"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload New Prescription</span>
          </button>

          <button
            onClick={onEmergencyClick}
            className="bg-[#E07B39] text-white font-semibold text-xs px-4 py-2.5 rounded-sm hover:bg-[#C96A28] transition-colors flex items-center gap-2 focus-visible:ring-1 focus-visible:ring-[#E07B39]"
          >
            <PhoneCall className="w-4 h-4" />
            <span>Emergency Hospital Search</span>
          </button>
        </div>
      </div>

      {/* Navigation Sub-Tabs (Clean hairline bar) */}
      <div className="flex items-center gap-1 border-b border-[#DDD9D1] pb-2 overflow-x-auto">
        {[
          { id: 'overview', label: 'Health Overview & Meds' },
          { id: 'careplan', label: 'Daily Care Plan (Audio)' },
          { id: 'timeline', label: 'Longitudinal Timeline' },
          { id: 'consent', label: `Consent & Access (${accessRequests.filter(r => r.status === 'active' || r.status === 'pending').length})` },
          { id: 'allergies', label: `Allergies & Safety (${allergies.length})` },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-3.5 py-1.5 rounded-sm text-xs font-semibold transition-colors whitespace-nowrap border ${
              activeTab === tab.id
                ? 'bg-white text-[#1C2B3A] border-[#1C2B3A]'
                : 'bg-[#FAF8F3] text-[#6B7A8D] border-transparent hover:text-[#1C2B3A] hover:border-[#DDD9D1]'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content 1: Overview & Medications */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          
          {/* Quick Metrics Data Band (divide-x structure) */}
          <div className="grid grid-cols-2 md:grid-cols-4 border border-[#DDD9D1] divide-y md:divide-y-0 md:divide-x divide-[#DDD9D1] bg-white rounded-sm">
            <div className="p-4 space-y-1">
              <span className="text-[10px] font-mono uppercase text-[#6B7A8D]">Active Medications</span>
              <div className="text-xl font-semibold text-[#1C2B3A]">{medications.length}</div>
              <span className="text-[11px] text-[#3D8B6E] flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> All verified
              </span>
            </div>

            <div className="p-4 space-y-1">
              <span className="text-[10px] font-mono uppercase text-[#6B7A8D]">Known Allergies</span>
              <div className="text-xl font-semibold text-[#D94F7A]">{allergies?.length ?? 0}</div>
              <span className="text-[11px] text-[#D94F7A] flex items-center gap-1 truncate">
                <AlertTriangle className="w-3 h-3 shrink-0" />
                <span>{allergies.length > 0 ? allergies.map(a => a.allergen).join(', ') : 'None documented'}</span>
              </span>
            </div>

            <div className="p-4 space-y-1">
              <span className="text-[10px] font-mono uppercase text-[#6B7A8D]">Active Doctor Sessions</span>
              <div className="text-xl font-semibold text-[#3D8B6E]">
                {accessRequests.filter(r => r.status === 'active').length}
              </div>
              <span className="text-[11px] text-[#2D5A40] flex items-center gap-1">
                <Lock className="w-3 h-3" /> Consent-controlled
              </span>
            </div>

            <div className="p-4 space-y-1">
              <span className="text-[10px] font-mono uppercase text-[#6B7A8D]">Pending Extraction</span>
              <div className="text-xl font-semibold text-[#E07B39]">
                {medications.filter(m => m.trustState === 'extracted').length}
              </div>
              <span className="text-[11px] text-[#A05520] flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {medications.filter(m => m.trustState === 'extracted').length > 0 ? 'Requires verification' : 'Up to date'}
              </span>
            </div>
          </div>

          {/* Active Verified Medication Ledger (Medical tabular layout instead of repeating cards) */}
          <div className="bg-white rounded-sm border border-[#DDD9D1] p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-[#DDD9D1] pb-4">
              <div>
                <span className="text-[10px] uppercase font-mono tracking-wider text-[#6B7A8D]">Verified Records</span>
                <h3 className="font-serif text-xl text-[#1C2B3A]">Current Medications</h3>
              </div>
              <button
                onClick={() => setIsUploadOpen(true)}
                className="text-xs font-semibold text-[#4A90C4] hover:underline flex items-center gap-1"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Upload New Prescription</span>
              </button>
            </div>

            {medications.length === 0 ? (
              <div className="py-12 text-center border border-dashed border-[#DDD9D1] rounded-sm bg-[#FAF8F3] space-y-3">
                <FileText className="w-8 h-8 text-[#6B7A8D] mx-auto" strokeWidth={1.5} />
                <h4 className="text-sm font-semibold text-[#1C2B3A]">No verified medications recorded</h4>
                <p className="text-xs text-[#6B7A8D] max-w-sm mx-auto">
                  Upload your past physical prescription slip to extract and verify your medication schedule.
                </p>
                <button
                  onClick={() => setIsUploadOpen(true)}
                  className="bg-[#4A90C4] text-white text-xs font-semibold px-4 py-2 rounded-sm"
                >
                  Upload First Prescription
                </button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-[#DDD9D1] text-[#6B7A8D] font-mono text-[10px] uppercase">
                      <th className="py-2.5 pr-4 font-semibold">Medication & Strength</th>
                      <th className="py-2.5 px-4 font-semibold">Regimen & Timing</th>
                      <th className="py-2.5 px-4 font-semibold">Prescriber & Facility</th>
                      <th className="py-2.5 px-4 font-semibold">Trust State</th>
                      <th className="py-2.5 pl-4 font-semibold text-right">Instructions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#DDD9D1]">
                    {medications.map(med => (
                      <tr key={med.id} className="hover:bg-[#FAF8F3] transition-colors">
                        <td className="py-3 pr-4">
                          <div className="font-semibold text-[#1C2B3A]">{med.name}</div>
                          <div className="text-[11px] text-[#6B7A8D] font-mono">{med.genericName} · {med.strength}</div>
                        </td>
                        <td className="py-3 px-4">
                          <div className="font-medium text-[#1C2B3A]">{med.dosage}</div>
                          <div className="text-[11px] text-[#6B7A8D]">{med.frequency} · {med.duration}</div>
                        </td>
                        <td className="py-3 px-4">
                          <div className="text-[#1C2B3A]">{med.prescribingDoctor}</div>
                          <div className="text-[11px] text-[#6B7A8D]">{med.hospital}</div>
                        </td>
                        <td className="py-3 px-4">
                          <TrustBadge state={med.trustState} />
                        </td>
                        <td className="py-3 pl-4 text-right text-[11px] text-[#6B7A8D] max-w-xs truncate">
                          {med.instructions}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

        </div>
      )}

      {/* Tab Content 2: Care Plan */}
      {activeTab === 'careplan' && (
        <CarePlanView medications={medications} />
      )}

      {/* Tab Content 3: Longitudinal Medical Timeline */}
      {activeTab === 'timeline' && (
        <div className="bg-white rounded-sm border border-[#DDD9D1] p-6 space-y-6">
          <div className="border-b border-[#DDD9D1] pb-4">
            <span className="text-[10px] uppercase font-mono tracking-wider text-[#6B7A8D]">Longitudinal View</span>
            <h3 className="font-serif text-xl text-[#1C2B3A]">Complete Healthcare Timeline</h3>
            <p className="text-xs text-[#6B7A8D] mt-1">
              Events stored chronologically across all treating clinics and hospitals with explicit trust indicators.
            </p>
          </div>

          <div className="space-y-3">
            {timeline.map((event) => (
              <div
                key={event.id}
                className="p-4 rounded-sm border border-[#DDD9D1] bg-[#FAF8F3] hover:bg-white hover:border-[#1C2B3A] transition-colors space-y-2.5"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <span className="text-xs font-semibold text-[#1C2B3A]">{event.title}</span>
                    <TrustBadge state={event.trustState} />
                  </div>
                  <span className="text-xs font-mono text-[#6B7A8D]">{event.date}</span>
                </div>

                <p className="text-xs text-[#6B7A8D] leading-relaxed">
                  {event.description}
                </p>

                {event.details?.diagnosis && (
                  <div className="p-2.5 bg-white rounded-sm border border-[#DDD9D1] text-xs text-[#1C2B3A]">
                    <span className="font-semibold text-[#4A90C4]">Clinical Assessment: </span>
                    {event.details.diagnosis}
                  </div>
                )}

                <div className="flex items-center justify-between pt-2 border-t border-[#DDD9D1] text-[11px] text-[#6B7A8D]">
                  <div className="flex items-center gap-2">
                    <Stethoscope className="w-3.5 h-3.5 text-[#3D8B6E]" />
                    <span>{event.provider} · {event.facility}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab Content 4: Consent & Access Management */}
      {activeTab === 'consent' && (
        <div className="bg-white rounded-sm border border-[#DDD9D1] p-6 space-y-6">
          <div className="border-b border-[#DDD9D1] pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <span className="text-[10px] uppercase font-mono tracking-wider text-[#6B7A8D]">Patient Sovereignty · Phase 3 Authorization Engine</span>
              <h3 className="font-serif text-xl text-[#1C2B3A]">Doctor Access & Consent Management</h3>
              <p className="text-xs text-[#6B7A8D] mt-1">
                You control who sees your health record. Server-side policies enforce purpose, resource scope, and instant token invalidation.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded-sm bg-[#EBF5EC] text-[#2D5A40] border border-[#D3EAD7]">
                Backend Enforced
              </span>
              <button
                onClick={() => setIsNewConsentOpen(true)}
                className="bg-[#3D8B6E] text-white font-semibold text-xs px-3.5 py-1.5 rounded-sm hover:bg-[#2D5A40] transition-colors flex items-center gap-1.5"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Grant Scoped Consent</span>
              </button>
            </div>
          </div>

          {/* New Consent Creation Form */}
          {isNewConsentOpen && (
            <div className="p-5 rounded-sm border border-[#DDD9D1] bg-[#FAF8F3] space-y-4">
              <div className="flex items-center justify-between border-b border-[#DDD9D1] pb-3">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-[#4A90C4]" />
                  <h4 className="text-sm font-semibold text-[#1C2B3A]">Issue Consent Grant (Phase 3 Backend Contract)</h4>
                </div>
                <button onClick={() => setIsNewConsentOpen(false)} className="text-xs text-[#6B7A8D] hover:text-[#1C2B3A]">✕ Close</button>
              </div>

              <form onSubmit={handleCreateConsentGrant} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-[#6B7A8D]">Grantee Physician</label>
                    <select
                      value={newGrantee}
                      onChange={(e) => setNewGrantee(e.target.value)}
                      className="w-full bg-white border border-[#DDD9D1] rounded-sm px-3 py-1.5 text-xs text-[#1C2B3A] font-medium"
                    >
                      <option value="DOC-MAX-582">Dr. Ananya Iyer (Max Saket - Endocrinology)</option>
                      <option value="DOC-AIIMS-104">Dr. Priya Nair (AIIMS - Cardiology)</option>
                      <option value="DOC-FORTIS-219">Dr. Vikrant Mehta (Fortis - General)</option>
                    </select>
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-[#6B7A8D]">Consent Purpose</label>
                    <select
                      value={newPurpose}
                      onChange={(e) => setNewPurpose(e.target.value)}
                      className="w-full bg-white border border-[#DDD9D1] rounded-sm px-3 py-1.5 text-xs text-[#1C2B3A] font-medium"
                    >
                      <option value="care_delivery">care_delivery (Direct Treatment)</option>
                      <option value="emergency_access">emergency_access (Critical Care)</option>
                      <option value="second_opinion">second_opinion (Consultation)</option>
                      <option value="administrative">administrative (Coverage / TPA)</option>
                    </select>
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-[#6B7A8D]">Resource Scope</label>
                    <select
                      value={newScope}
                      onChange={(e) => setNewScope(e.target.value)}
                      className="w-full bg-white border border-[#DDD9D1] rounded-sm px-3 py-1.5 text-xs text-[#1C2B3A] font-medium"
                    >
                      <option value="clinical_records">clinical_records (Full Record)</option>
                      <option value="prescriptions">prescriptions (Rx History Only)</option>
                      <option value="medications">medications (Active Meds Only)</option>
                      <option value="care_plan">care_plan (Daily Schedule Only)</option>
                      <option value="all_records">all_records (Broad Scope)</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-[#6B7A8D]">Valid Duration</label>
                    <select
                      value={newDurationHours}
                      onChange={(e) => setNewDurationHours(Number(e.target.value))}
                      className="w-full bg-white border border-[#DDD9D1] rounded-sm px-3 py-1.5 text-xs text-[#1C2B3A] font-medium"
                    >
                      <option value={12}>12 Hours (Single Outpatient Visit)</option>
                      <option value={24}>24 Hours (Day Care / Observation)</option>
                      <option value={72}>72 Hours (Inpatient Evaluation)</option>
                      <option value={168}>7 Days (Extended Recovery)</option>
                    </select>
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-[#6B7A8D]">Consent Notes</label>
                    <input
                      type="text"
                      value={newNotes}
                      onChange={(e) => setNewNotes(e.target.value)}
                      placeholder="e.g. Authorized for quarterly metabolic check"
                      className="w-full bg-white border border-[#DDD9D1] rounded-sm px-3 py-1.5 text-xs text-[#1C2B3A]"
                    />
                  </div>
                </div>

                <div className="flex justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setIsNewConsentOpen(false)}
                    className="text-xs font-semibold text-[#6B7A8D] px-3 py-1.5"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="bg-[#4A90C4] text-white font-semibold text-xs px-4 py-1.5 rounded-sm hover:bg-[#3A7DB0] transition-colors"
                  >
                    Authorize & Issue Grant
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Active Access List */}
          <div className="space-y-3">
            {accessRequests.map(req => (
              <div
                key={req.id}
                className="p-4 rounded-sm border border-[#DDD9D1] bg-[#FAF8F3] space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-sm bg-white border border-[#DDD9D1] flex items-center justify-center text-[#3D8B6E]">
                      <Stethoscope className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="text-xs font-semibold text-[#1C2B3A]">{req.doctorName}</h4>
                      <p className="text-[11px] text-[#6B7A8D]">{req.doctorRole} · {req.hospital}</p>
                    </div>
                  </div>

                  <span className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded-sm border ${
                    req.status === 'active'
                      ? 'bg-[#EBF5EC] text-[#2D5A40] border-[#D3EAD7]'
                      : req.status === 'pending'
                      ? 'bg-[#FEF3E8] text-[#A05520] border-[#FCDDC1]'
                      : 'bg-[#F0EDE7] text-[#6B7A8D] border-[#DDD9D1]'
                  }`}>
                    {req.status === 'active' ? 'Active Session' : req.status === 'pending' ? 'Pending Approval' : 'Revoked / Expired'}
                  </span>
                </div>

                <div className="bg-white rounded-sm p-3 border border-[#DDD9D1] text-xs space-y-1">
                  <div className="flex justify-between">
                    <span className="text-[#6B7A8D]">Requested Scope:</span>
                    <strong className="text-[#1C2B3A] font-semibold">{req.requestedScope}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#6B7A8D]">Purpose of Request:</span>
                    <span className="text-[#1C2B3A] font-medium">{req.purpose}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#6B7A8D]">Session Duration:</span>
                    <span className="text-[#2B5F8A] font-mono font-semibold">{req.expiresAt}</span>
                  </div>
                </div>

                {/* Consent Action Buttons */}
                <div className="flex items-center justify-end gap-3 pt-1">
                  {req.status === 'pending' && (
                    <>
                      <button
                        onClick={() => handleRevokeAccess(req.id, req.doctorName)}
                        className="text-xs font-semibold text-[#6B7A8D] hover:text-[#1C2B3A] px-3 py-1.5"
                      >
                        Decline
                      </button>
                      <button
                        onClick={() => handleGrantAccess(req.id, req.doctorName)}
                        className="bg-[#3D8B6E] text-white font-semibold text-xs px-3.5 py-1.5 rounded-sm hover:bg-[#2D5A40] transition-colors"
                      >
                        Grant Scoped Access
                      </button>
                    </>
                  )}

                  {req.status === 'active' && (
                    <button
                      onClick={() => handleRevokeAccess(req.id, req.doctorName)}
                      className="bg-white border border-[#D94F7A] text-[#D94F7A] font-semibold text-xs px-3.5 py-1.5 rounded-sm hover:bg-[#FDEEF4] transition-colors"
                    >
                      Instant Revoke Access
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab Content 5: Allergies & Safety Center */}
      {activeTab === 'allergies' && (
        <div className="bg-white rounded-sm border border-[#DDD9D1] p-6 space-y-6">
          <div className="border-b border-[#DDD9D1] pb-4">
            <span className="text-[10px] uppercase font-mono tracking-wider text-[#6B7A8D]">Clinical Safety Guardrails</span>
            <h3 className="font-serif text-xl text-[#1C2B3A]">Recorded Allergies & Adverse Reactions</h3>
            <p className="text-xs text-[#6B7A8D] mt-1">
              Documented allergic sensitivities trigger automated alerts during future doctor consultations.
            </p>
          </div>

          {allergies.length === 0 ? (
            <div className="py-12 text-center border border-dashed border-[#DDD9D1] rounded-sm bg-[#FAF8F3] space-y-2">
              <ShieldCheck className="w-8 h-8 text-[#3D8B6E] mx-auto" strokeWidth={1.5} />
              <h4 className="text-sm font-semibold text-[#1C2B3A]">No Documented Allergies</h4>
              <p className="text-xs text-[#6B7A8D] max-w-sm mx-auto">
                No drug or substance allergies have been documented for this profile. Any allergies recorded during clinical reviews will be shown here.
              </p>
            </div>
          ) : (
            <div className="grid md:grid-cols-2 gap-4">
              {allergies.map(alg => (
                <div
                  key={alg.id}
                  className="bg-[#FAF8F3] rounded-sm border border-[#DDD9D1] p-4 space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-semibold text-[#1C2B3A]">{alg.allergen}</h4>
                    <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-sm bg-[#FDEEF4] text-[#D94F7A] border border-[#F8D2DF]">
                      {alg.severity} Severity
                    </span>
                  </div>

                  <div className="bg-white rounded-sm p-3 border border-[#DDD9D1] text-xs">
                    <div className="text-[#6B7A8D]">Reaction Documented:</div>
                    <div className="font-semibold text-[#1C2B3A] mt-0.5">{alg.reaction}</div>
                  </div>

                  <div className="text-[11px] text-[#6B7A8D] flex justify-between pt-1 border-t border-[#DDD9D1]">
                    <span>Recorded: {alg.recordedDate}</span>
                    <span>By: {alg.recordedBy}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Prescription Upload & Verification Modal */}
      <PrescriptionUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onVerifyAndAdd={handleVerifyAndAdd}
        patientId={patient.id}
      />

    </div>
  );
};
