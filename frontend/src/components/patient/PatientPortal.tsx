import React, { useState } from 'react';
import { 
  User, 
  UploadCloud, 
  ShieldCheck, 
  ShieldAlert, 
  FileText, 
  Clock, 
  AlertTriangle, 
  Sparkles, 
  CheckCircle2, 
  XCircle, 
  Stethoscope, 
  Calendar, 
  Lock, 
  PhoneCall, 
  ChevronRight,
  Plus
} from 'lucide-react';
import { 
  INITIAL_PATIENT, 
  INITIAL_MEDICATIONS, 
  INITIAL_ALLERGIES, 
  INITIAL_TIMELINE, 
  INITIAL_ACCESS_REQUESTS 
} from '../../data/mockData';
import { Medication, Allergy, TimelineEvent, AccessRequest } from '../../types';
import { TrustBadge, FreshnessBadge } from '../common/Badge';
import { PrescriptionUploadModal } from './PrescriptionUploadModal';
import { CarePlanView } from './CarePlanView';

interface PatientPortalProps {
  onEmergencyClick: () => void;
}

export const PatientPortal: React.FC<PatientPortalProps> = ({ onEmergencyClick }) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'careplan' | 'timeline' | 'consent' | 'allergies'>('overview');
  const [medications, setMedications] = useState<Medication[]>(INITIAL_MEDICATIONS);
  const [timeline, setTimeline] = useState<TimelineEvent[]>(INITIAL_TIMELINE);
  const [accessRequests, setAccessRequests] = useState<AccessRequest[]>(INITIAL_ACCESS_REQUESTS);
  const [isUploadOpen, setIsUploadOpen] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const handleVerifyAndAdd = (newMed: Medication) => {
    setMedications(prev => [newMed, ...prev]);

    const newEvent: TimelineEvent = {
      id: `tl-${Date.now()}`,
      date: 'Today, 25 Sep 2026',
      title: `Patient-Verified: ${newMed.name} ${newMed.strength}`,
      category: 'prescription',
      provider: newMed.prescribingDoctor,
      facility: newMed.hospital,
      description: `${newMed.name} verified by patient Rohan Sharma. Added to active daily medication schedule.`,
      trustState: 'verified',
    };
    setTimeline(prev => [newEvent, ...prev]);
    showToast(`Verified and added ${newMed.name} to your active health record.`);
  };

  const handleRevokeAccess = (id: string, doctorName: string) => {
    setAccessRequests(prev => prev.map(req => req.id === id ? { ...req, status: 'revoked' } : req));
    showToast(`Access revoked for ${doctorName}. Further requests for your record will be rejected.`);
  };

  const handleGrantAccess = (id: string, doctorName: string) => {
    setAccessRequests(prev => prev.map(req => req.id === id ? { ...req, status: 'active' } : req));
    showToast(`Scoped access granted to ${doctorName} for 12 hours.`);
  };

  return (
    <div className="pt-24 pb-20 max-w-6xl mx-auto px-6 space-y-8 animate-in fade-in duration-300">
      
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-20 right-6 z-50 bg-[#1C2B3A] text-white text-xs font-semibold px-4 py-3 rounded-2xl shadow-xl flex items-center gap-2 border border-white/10 animate-in slide-in-from-top-4 duration-200">
          <CheckCircle2 className="w-4 h-4 text-[#3D8B6E]" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Patient Header Profile Card */}
      <div className="bg-white rounded-3xl border border-[#DDD9D1] p-6 sm:p-8 shadow-soft flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-[#EBF4FB] border border-[#D5E8F8] flex items-center justify-center text-[#2B5F8A] font-bold text-xl shadow-inner">
            RS
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="font-serif text-3xl font-bold text-[#1C2B3A]">{INITIAL_PATIENT.name}</h1>
              <span className="text-xs font-mono font-bold bg-[#EBF4FB] text-[#2B5F8A] border border-[#D5E8F8] px-2.5 py-0.5 rounded-lg">
                {INITIAL_PATIENT.id}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-xs text-[#6B7A8D] mt-1.5">
              <span>{INITIAL_PATIENT.age} Years, {INITIAL_PATIENT.gender}</span>
              <span>·</span>
              <span>Blood Group: <strong className="text-[#1C2B3A]">{INITIAL_PATIENT.bloodGroup}</strong></span>
              <span>·</span>
              <span>{INITIAL_PATIENT.city}</span>
            </div>
          </div>
        </div>

        {/* Primary Patient Actions */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => setIsUploadOpen(true)}
            className="bg-[#4A90C4] text-white font-semibold text-xs px-5 py-3 rounded-xl hover:bg-[#3A7DB0] transition-colors duration-200 shadow-sm flex items-center gap-2"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload New Prescription</span>
          </button>

          <button
            onClick={onEmergencyClick}
            className="bg-[#E07B39] text-white font-semibold text-xs px-4 py-3 rounded-xl hover:bg-[#C96A28] transition-colors duration-200 shadow-sm flex items-center gap-2"
          >
            <PhoneCall className="w-4 h-4" />
            <span>Emergency Hospital Search</span>
          </button>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex items-center gap-2 border-b border-[#DDD9D1] pb-2 overflow-x-auto">
        {[
          { id: 'overview', label: 'Health Overview & Meds' },
          { id: 'careplan', label: 'Daily Care Plan (Audio)' },
          { id: 'timeline', label: 'Longitudinal Timeline' },
          { id: 'consent', label: `Consent & Doctor Access (${accessRequests.filter(r => r.status === 'active' || r.status === 'pending').length})` },
          { id: 'allergies', label: `Allergies & Safety (${INITIAL_ALLERGIES.length})` },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-2.5 rounded-xl text-xs font-bold transition-all whitespace-nowrap ${
              activeTab === tab.id
                ? 'bg-white text-[#1C2B3A] border border-[#DDD9D1] shadow-sm'
                : 'text-[#6B7A8D] hover:text-[#1C2B3A] hover:bg-[#FAF8F3]'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content 1: Overview & Medications */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          
          {/* Quick Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-2xl border border-[#DDD9D1] p-4">
              <span className="text-[11px] font-bold text-[#6B7A8D] uppercase">Active Medications</span>
              <div className="text-2xl font-bold font-serif text-[#1C2B3A] mt-1">{medications.length}</div>
              <span className="text-[11px] text-[#3D8B6E] font-semibold flex items-center gap-1 mt-1">
                <CheckCircle2 className="w-3 h-3" /> All verified
              </span>
            </div>

            <div className="bg-white rounded-2xl border border-[#DDD9D1] p-4">
              <span className="text-[11px] font-bold text-[#6B7A8D] uppercase">Known Allergies</span>
              <div className="text-2xl font-bold font-serif text-[#D94F7A] mt-1">{INITIAL_ALLERGIES.length}</div>
              <span className="text-[11px] text-[#D94F7A] font-semibold flex items-center gap-1 mt-1">
                <AlertTriangle className="w-3 h-3" /> Penicillin & NSAIDs
              </span>
            </div>

            <div className="bg-white rounded-2xl border border-[#DDD9D1] p-4">
              <span className="text-[11px] font-bold text-[#6B7A8D] uppercase">Active Doctor Sessions</span>
              <div className="text-2xl font-bold font-serif text-[#3D8B6E] mt-1">
                {accessRequests.filter(r => r.status === 'active').length}
              </div>
              <span className="text-[11px] text-[#2D5A40] font-semibold flex items-center gap-1 mt-1">
                <Lock className="w-3 h-3" /> Consent-controlled
              </span>
            </div>

            <div className="bg-white rounded-2xl border border-[#DDD9D1] p-4">
              <span className="text-[11px] font-bold text-[#6B7A8D] uppercase">Pending Review</span>
              <div className="text-2xl font-bold font-serif text-[#E07B39] mt-1">1</div>
              <span className="text-[11px] text-[#A05520] font-semibold flex items-center gap-1 mt-1">
                <Clock className="w-3 h-3" /> Scanned slip (Fortis)
              </span>
            </div>
          </div>

          {/* Active Verified Medication List */}
          <div className="bg-white rounded-3xl border border-[#DDD9D1] p-6 shadow-soft space-y-5">
            <div className="flex items-center justify-between border-b border-[#DDD9D1] pb-4">
              <div>
                <span className="text-[11px] uppercase tracking-wider font-bold text-[#6B7A8D]">Verified Records</span>
                <h3 className="font-serif text-2xl font-bold text-[#1C2B3A]">Current Medications</h3>
              </div>
              <button
                onClick={() => setIsUploadOpen(true)}
                className="text-xs font-bold text-[#4A90C4] hover:underline flex items-center gap-1"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Upload New Slip</span>
              </button>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {medications.map(med => (
                <div
                  key={med.id}
                  className="bg-[#FAF8F3]/60 rounded-2xl border border-[#DDD9D1] p-4 flex flex-col justify-between space-y-3 hover:shadow-sm transition-all"
                >
                  <div className="space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h4 className="text-sm font-bold text-[#1C2B3A]">{med.name}</h4>
                        <p className="text-[11px] font-semibold text-[#6B7A8D]">{med.genericName}</p>
                      </div>
                      <TrustBadge state={med.trustState} />
                    </div>

                    <div className="bg-white rounded-xl p-2.5 border border-[#DDD9D1] space-y-1 text-xs">
                      <div className="flex justify-between text-[#6B7A8D]">
                        <span>Strength:</span>
                        <strong className="text-[#1C2B3A]">{med.strength}</strong>
                      </div>
                      <div className="flex justify-between text-[#6B7A8D]">
                        <span>Dosage:</span>
                        <strong className="text-[#1C2B3A]">{med.dosage} · {med.frequency}</strong>
                      </div>
                      <div className="flex justify-between text-[#6B7A8D]">
                        <span>Duration:</span>
                        <strong className="text-[#1C2B3A]">{med.duration}</strong>
                      </div>
                    </div>

                    <p className="text-xs text-[#6B7A8D] italic">
                      "{med.instructions}"
                    </p>
                  </div>

                  <div className="pt-2 border-t border-[#DDD9D1]/60 text-[10px] text-[#6B7A8D] space-y-0.5">
                    <div>Prescribed by: <strong className="text-[#1C2B3A]">{med.prescribingDoctor}</strong></div>
                    <div>Facility: {med.hospital} · {med.datePrescribed}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>
      )}

      {/* Tab Content 2: Care Plan */}
      {activeTab === 'careplan' && (
        <CarePlanView medications={medications} />
      )}

      {/* Tab Content 3: Longitudinal Medical Timeline */}
      {activeTab === 'timeline' && (
        <div className="bg-white rounded-3xl border border-[#DDD9D1] p-6 shadow-soft space-y-6">
          <div className="border-b border-[#DDD9D1] pb-4">
            <span className="text-[11px] uppercase tracking-wider font-bold text-[#6B7A8D]">Longitudinal View</span>
            <h3 className="font-serif text-2xl font-bold text-[#1C2B3A]">Complete Healthcare Timeline</h3>
            <p className="text-xs text-[#6B7A8D] mt-1">
              Events are stored chronologically across all treating clinics and hospitals with explicit trust indicators.
            </p>
          </div>

          <div className="space-y-4">
            {timeline.map((event) => (
              <div
                key={event.id}
                className="p-5 rounded-2xl border border-[#DDD9D1] bg-[#FAF8F3]/60 space-y-3 hover:bg-white hover:shadow-sm transition-all"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <span className="text-xs font-bold text-[#1C2B3A]">{event.title}</span>
                    <TrustBadge state={event.trustState} />
                  </div>
                  <span className="text-xs font-semibold text-[#6B7A8D]">{event.date}</span>
                </div>

                <p className="text-xs text-[#6B7A8D] leading-relaxed">
                  {event.description}
                </p>

                {event.details?.diagnosis && (
                  <div className="p-3 bg-white rounded-xl border border-[#DDD9D1] text-xs text-[#1C2B3A]">
                    <span className="font-bold text-[#4A90C4]">Clinical Assessment: </span>
                    {event.details.diagnosis}
                  </div>
                )}

                <div className="flex items-center justify-between pt-2 border-t border-[#DDD9D1]/50 text-[11px] text-[#6B7A8D]">
                  <div className="flex items-center gap-2">
                    <Stethoscope className="w-3.5 h-3.5 text-[#3D8B6E]" />
                    <span>{event.provider}</span>
                    <span>·</span>
                    <span>{event.facility}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab Content 4: Consent & Access Management */}
      {activeTab === 'consent' && (
        <div className="bg-white rounded-3xl border border-[#DDD9D1] p-6 shadow-soft space-y-6">
          <div className="border-b border-[#DDD9D1] pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <span className="text-[11px] uppercase tracking-wider font-bold text-[#6B7A8D]">Patient Sovereignty</span>
              <h3 className="font-serif text-2xl font-bold text-[#1C2B3A]">Doctor Access & Consent Management</h3>
              <p className="text-xs text-[#6B7A8D] mt-1">
                You control who sees your health record. Active sessions expire automatically and can be revoked instantly.
              </p>
            </div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#EBF5EC] text-[#2D5A40]">
              <Lock className="w-3.5 h-3.5" />
              <span>Server-Side Enforced</span>
            </div>
          </div>

          <div className="space-y-4">
            {accessRequests.map(req => (
              <div
                key={req.id}
                className="p-5 rounded-2xl border border-[#DDD9D1] bg-[#FAF8F3]/60 space-y-4"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-white border border-[#DDD9D1] flex items-center justify-center text-[#3D8B6E]">
                      <Stethoscope className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-[#1C2B3A]">{req.doctorName}</h4>
                      <p className="text-xs text-[#6B7A8D]">{req.doctorRole} · {req.hospital}</p>
                    </div>
                  </div>

                  <span className={`text-xs font-bold px-3 py-1 rounded-full ${
                    req.status === 'active'
                      ? 'bg-[#EBF5EC] text-[#2D5A40] border border-[#D3EAD7]'
                      : req.status === 'pending'
                      ? 'bg-[#FEF3E8] text-[#A05520] border border-[#FCDDC1]'
                      : 'bg-[#F0EDE7] text-[#6B7A8D] border border-[#DDD9D1]'
                  }`}>
                    {req.status === 'active' ? 'Active Session' : req.status === 'pending' ? 'Pending Approval' : 'Revoked / Expired'}
                  </span>
                </div>

                <div className="bg-white rounded-xl p-3 border border-[#DDD9D1] text-xs space-y-1">
                  <div className="flex justify-between">
                    <span className="text-[#6B7A8D]">Requested Scope:</span>
                    <strong className="text-[#1C2B3A]">{req.requestedScope}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#6B7A8D]">Purpose of Request:</span>
                    <span className="text-[#1C2B3A] font-medium">{req.purpose}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#6B7A8D]">Session Duration:</span>
                    <span className="text-[#2B5F8A] font-semibold">{req.expiresAt}</span>
                  </div>
                </div>

                {/* Consent Action Buttons */}
                <div className="flex items-center justify-end gap-3 pt-1">
                  {req.status === 'pending' && (
                    <>
                      <button
                        onClick={() => handleRevokeAccess(req.id, req.doctorName)}
                        className="text-xs font-semibold text-[#6B7A8D] hover:text-[#1C2B3A] px-3 py-2"
                      >
                        Decline
                      </button>
                      <button
                        onClick={() => handleGrantAccess(req.id, req.doctorName)}
                        className="bg-[#3D8B6E] text-white font-semibold text-xs px-4 py-2 rounded-xl hover:bg-[#2D5A40] transition-colors shadow-sm"
                      >
                        Grant Scoped Access
                      </button>
                    </>
                  )}

                  {req.status === 'active' && (
                    <button
                      onClick={() => handleRevokeAccess(req.id, req.doctorName)}
                      className="bg-white border border-[#D94F7A] text-[#D94F7A] font-bold text-xs px-4 py-2 rounded-xl hover:bg-[#FDEEF4] transition-colors shadow-sm"
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
        <div className="bg-white rounded-3xl border border-[#DDD9D1] p-6 shadow-soft space-y-6">
          <div className="border-b border-[#DDD9D1] pb-4">
            <span className="text-[11px] uppercase tracking-wider font-bold text-[#6B7A8D]">Clinical Safety Guardrails</span>
            <h3 className="font-serif text-2xl font-bold text-[#1C2B3A]">Recorded Allergies & Adverse Reactions</h3>
            <p className="text-xs text-[#6B7A8D] mt-1">
              Documented allergic sensitivities are verified by attending clinicians and trigger automated alerts during future doctor consultations.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            {INITIAL_ALLERGIES.map(alg => (
              <div
                key={alg.id}
                className="bg-[#FAF8F3]/60 rounded-2xl border border-[#DDD9D1] p-5 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-bold text-[#1C2B3A]">{alg.allergen}</h4>
                  <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-[#FDEEF4] text-[#D94F7A] border border-[#FAD3E2]">
                    {alg.severity} Severity
                  </span>
                </div>

                <div className="bg-white rounded-xl p-3 border border-[#DDD9D1] text-xs">
                  <div className="text-[#6B7A8D]">Reaction Documented:</div>
                  <div className="font-semibold text-[#1C2B3A] mt-0.5">{alg.reaction}</div>
                </div>

                <div className="text-[10px] text-[#6B7A8D] flex justify-between pt-1">
                  <span>Recorded: {alg.recordedDate}</span>
                  <span>By: {alg.recordedBy}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Prescription Upload & Verification Modal */}
      <PrescriptionUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onVerifyAndAdd={handleVerifyAndAdd}
      />

    </div>
  );
};
