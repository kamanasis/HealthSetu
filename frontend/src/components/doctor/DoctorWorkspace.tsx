import React, { useState } from 'react';
import { 
  Stethoscope, 
  Search, 
  ShieldCheck, 
  AlertTriangle, 
  Sparkles, 
  Plus, 
  CheckCircle2, 
  FileText, 
  Clock, 
  HeartPulse, 
  Building2, 
  Lock,
  ExternalLink,
  Info
} from 'lucide-react';
import { 
  INITIAL_PATIENT, 
  INITIAL_MEDICATIONS, 
  INITIAL_ALLERGIES, 
  INITIAL_TIMELINE, 
  SAFETY_DATABASE 
} from '../../data/mockData';
import { Medication, SafetyAlert, TimelineEvent } from '../../types';
import { TrustBadge } from '../common/Badge';

interface DoctorWorkspaceProps {
  onPrescriptionFinalized?: (med: Medication) => void;
}

export const DoctorWorkspace: React.FC<DoctorWorkspaceProps> = ({ onPrescriptionFinalized }) => {
  const [patientIdInput, setPatientIdInput] = useState<string>('HS-PAT-8921');
  const [activePatient, setActivePatient] = useState<typeof INITIAL_PATIENT | null>(INITIAL_PATIENT);
  const [activeTab, setActiveTab] = useState<'review' | 'prescribe'>('review');

  // Prescription builder state
  const [prescribedDrug, setPrescribedDrug] = useState<string>('');
  const [strength, setStrength] = useState<string>('40 mg');
  const [frequency, setFrequency] = useState<string>('Once daily (OD)');
  const [duration, setDuration] = useState<string>('30 Days');
  const [instructions, setInstructions] = useState<string>('Take morning after breakfast');
  const [clinicalNotes, setClinicalNotes] = useState<string>('');
  const [detectedAlerts, setDetectedAlerts] = useState<SafetyAlert[]>([]);
  const [prescriptionSuccess, setPrescriptionSuccess] = useState<boolean>(false);

  const handleDrugInput = (drugName: string) => {
    setPrescribedDrug(drugName);
    // Real-time deterministic check against known safety database
    if (SAFETY_DATABASE[drugName]) {
      setDetectedAlerts(SAFETY_DATABASE[drugName]);
    } else {
      setDetectedAlerts([]);
    }
  };

  const handleFinalizePrescription = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prescribedDrug) return;

    const newMed: Medication = {
      id: `med-doc-${Date.now()}`,
      name: prescribedDrug,
      genericName: prescribedDrug,
      strength: strength,
      dosage: '1 Tablet',
      frequency: frequency,
      route: 'Oral',
      duration: duration,
      instructions: instructions,
      prescribingDoctor: 'Dr. Priya Nair, MD (Cardiology)',
      hospital: 'AIIMS, New Delhi',
      datePrescribed: '25 Sep 2026',
      trustState: 'verified',
      timeOfDay: ['morning'],
      mealTiming: 'after_food',
      category: 'Doctor-Prescribed Treatment',
    };

    if (onPrescriptionFinalized) {
      onPrescriptionFinalized(newMed);
    }

    setPrescriptionSuccess(true);
    setTimeout(() => {
      setPrescriptionSuccess(false);
      setPrescribedDrug('');
      setDetectedAlerts([]);
      setActiveTab('review');
    }, 2500);
  };

  return (
    <div className="pt-24 pb-20 max-w-6xl mx-auto px-6 space-y-8 animate-in fade-in duration-300">
      
      {/* Doctor Identity Header */}
      <div className="bg-white rounded-3xl border border-[#DDD9D1] p-6 shadow-soft flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-[#EBF5EC] border border-[#D3EAD7] flex items-center justify-center text-[#3D8B6E]">
            <Stethoscope className="w-7 h-7" strokeWidth={1.8} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-serif text-2xl font-bold text-[#1C2B3A]">Dr. Priya Nair, MD</h1>
              <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-[#EBF5EC] text-[#2D5A40]">
                MCI-48291 · Verified Clinician
              </span>
            </div>
            <p className="text-xs text-[#6B7A8D] mt-0.5">
              Senior Consultant Cardiologist · All India Institute of Medical Sciences (AIIMS), New Delhi
            </p>
          </div>
        </div>

        {/* Patient Lookup Input */}
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-3 text-[#6B7A8D]" />
            <input
              type="text"
              value={patientIdInput}
              onChange={(e) => setPatientIdInput(e.target.value)}
              placeholder="Enter Patient ID (e.g. HS-PAT-8921)"
              className="bg-[#FAF8F3] border border-[#DDD9D1] rounded-xl pl-9 pr-3 py-2 text-xs font-mono font-bold text-[#1C2B3A] focus:ring-1 focus:ring-[#3D8B6E] outline-none w-56"
            />
          </div>
          <button
            onClick={() => setActivePatient(INITIAL_PATIENT)}
            className="bg-[#3D8B6E] text-white font-semibold text-xs px-4 py-2 rounded-xl hover:bg-[#2D5A40] transition-colors"
          >
            Access Record
          </button>
        </div>
      </div>

      {activePatient ? (
        <div className="space-y-6">
          
          {/* Patient Overview & Consent Banner */}
          <div className="bg-[#FAF8F3] border border-[#DDD9D1] rounded-2xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-white border border-[#DDD9D1] flex items-center justify-center font-bold text-[#2B5F8A]">
                RS
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-serif text-xl font-bold text-[#1C2B3A]">{activePatient.name}</h3>
                  <span className="text-xs font-mono font-bold text-[#4A90C4] bg-white border border-[#DDD9D1] px-2 py-0.5 rounded">
                    {activePatient.id}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-xs text-[#6B7A8D] mt-1">
                  <span>{activePatient.age} yrs · {activePatient.gender}</span>
                  <span>·</span>
                  <span>Blood Group: <strong className="text-[#1C2B3A]">{activePatient.bloodGroup}</strong></span>
                  <span>·</span>
                  <span>Known Allergies: <strong className="text-[#D94F7A]">Penicillin, NSAIDs</strong></span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 bg-[#EBF5EC] border border-[#D3EAD7] px-3.5 py-1.5 rounded-xl text-xs font-bold text-[#2D5A40]">
              <Lock className="w-3.5 h-3.5 text-[#3D8B6E]" />
              <span>Authorized Access (Session Expires in 11h 45m)</span>
            </div>
          </div>

          {/* Clinical Workspace Tabs */}
          <div className="flex items-center gap-2 border-b border-[#DDD9D1] pb-2">
            <button
              onClick={() => setActiveTab('review')}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                activeTab === 'review'
                  ? 'bg-white text-[#1C2B3A] border border-[#DDD9D1] shadow-sm'
                  : 'text-[#6B7A8D] hover:text-[#1C2B3A]'
              }`}
            >
              Clinical Review & AI SBAR Summary
            </button>
            <button
              onClick={() => setActiveTab('prescribe')}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                activeTab === 'prescribe'
                  ? 'bg-white text-[#1C2B3A] border border-[#DDD9D1] shadow-sm'
                  : 'text-[#6B7A8D] hover:text-[#1C2B3A]'
              }`}
            >
              Prescribe Treatment & Safety Check
            </button>
          </div>

          {/* TAB 1: Clinical Review & Evidence-Linked AI History */}
          {activeTab === 'review' && (
            <div className="grid lg:grid-cols-12 gap-6 items-start">
              
              {/* Evidence-Linked AI SBAR Clinical Summary (Left 7 cols) */}
              <div className="lg:col-span-7 bg-white rounded-3xl border border-[#DDD9D1] p-6 shadow-soft space-y-6">
                
                <div className="flex items-center justify-between border-b border-[#DDD9D1] pb-4">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-[#4A90C4]" />
                    <h3 className="font-serif text-xl font-bold text-[#1C2B3A]">
                      AI-Assisted Clinical History (SBAR)
                    </h3>
                  </div>
                  <span className="text-[11px] font-bold px-3 py-1 rounded-full bg-white border border-[#DDD9D1] text-[#4A90C4] shadow-sm">
                    AI Decision Support · Non-Autonomous
                  </span>
                </div>

                <div className="space-y-4 text-xs leading-relaxed">
                  
                  {/* Situation */}
                  <div className="p-3.5 rounded-xl bg-[#FAF8F3] border border-[#DDD9D1] space-y-1">
                    <div className="font-bold text-[#2B5F8A] uppercase tracking-wider text-[10px]">
                      S — Situation
                    </div>
                    <p className="text-[#1C2B3A]">
                      42-year-old male with primary essential hypertension and managed dyslipidemia presenting for routine quarterly clinical follow-up and blood pressure monitoring.
                    </p>
                  </div>

                  {/* Background */}
                  <div className="p-3.5 rounded-xl bg-[#FAF8F3] border border-[#DDD9D1] space-y-1">
                    <div className="font-bold text-[#2B5F8A] uppercase tracking-wider text-[10px]">
                      B — Background & Source Records
                    </div>
                    <p className="text-[#6B7A8D]">
                      Longitudinal record spans 3 institutions: AIIMS (Consultation 12 Sep), Apollo Hospital (Lipid Rx 28 Aug), and Fortis Clinic (Recent scanned slip). Active medications: Telmisartan 40mg OD and Metformin 500mg BD.
                    </p>
                    <div className="flex items-center gap-2 pt-1 text-[11px] font-semibold text-[#4A90C4]">
                      <span className="underline cursor-pointer">Source: AIIMS Record #4910</span>
                      <span>·</span>
                      <span className="underline cursor-pointer">Apollo Lab #9021</span>
                    </div>
                  </div>

                  {/* Assessment */}
                  <div className="p-3.5 rounded-xl bg-[#FAF8F3] border border-[#DDD9D1] space-y-1.5">
                    <div className="font-bold text-[#2B5F8A] uppercase tracking-wider text-[10px]">
                      A — Clinical Pattern Assessment
                    </div>
                    <p className="text-[#1C2B3A]">
                      Blood pressure normalized (126/82 mmHg). Glycemic control adequate (HbA1c 6.8%).
                    </p>
                    <div className="p-2.5 rounded-lg bg-[#FEF3E8] border border-[#FCDDC1] text-[#A05520] font-medium text-[11px] flex items-start gap-2">
                      <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-[#E07B39]" />
                      <span>
                        <strong>Pattern Flag:</strong> Unverified scanned slip from Fortis lists Rosuvastatin 10mg. Patient is already taking Atorvastatin 20mg. Potential duplicative statin therapy should be resolved.
                      </span>
                    </div>
                  </div>

                  {/* Recommendation */}
                  <div className="p-3.5 rounded-xl bg-[#FAF8F3] border border-[#DDD9D1] space-y-1">
                    <div className="font-bold text-[#2B5F8A] uppercase tracking-wider text-[10px]">
                      R — Recommendation For Treating Clinician
                    </div>
                    <p className="text-[#1C2B3A]">
                      1. Maintain Telmisartan 40mg OD. 2. Clarify statin refill (discontinue duplicate statin). 3. Schedule serum creatinine & renal function tests in 3 months.
                    </p>
                  </div>

                </div>

                <div className="pt-2 border-t border-[#DDD9D1] flex items-center justify-between text-[11px] text-[#6B7A8D]">
                  <span className="flex items-center gap-1.5">
                    <Info className="w-3.5 h-3.5 text-[#3D8B6E]" />
                    <span>The doctor remains 100% responsible for all clinical decisions.</span>
                  </span>
                  <button
                    onClick={() => setActiveTab('prescribe')}
                    className="font-bold text-[#3D8B6E] hover:underline"
                  >
                    Proceed to Prescribe →
                  </button>
                </div>

              </div>

              {/* Longitudinal Timeline & Current Meds (Right 5 cols) */}
              <div className="lg:col-span-5 space-y-5">
                
                {/* Active Verified Medications */}
                <div className="bg-white rounded-3xl border border-[#DDD9D1] p-5 shadow-soft space-y-3">
                  <h4 className="font-serif text-lg font-bold text-[#1C2B3A]">Active Verified Medications</h4>
                  <div className="space-y-2">
                    {INITIAL_MEDICATIONS.map(m => (
                      <div key={m.id} className="p-3 rounded-xl border border-[#DDD9D1] bg-[#FAF8F3]/60 flex items-center justify-between text-xs">
                        <div>
                          <strong className="text-[#1C2B3A]">{m.name} {m.strength}</strong>
                          <div className="text-[11px] text-[#6B7A8D]">{m.frequency} · {m.hospital}</div>
                        </div>
                        <TrustBadge state={m.trustState} />
                      </div>
                    ))}
                  </div>
                </div>

                {/* Recorded Allergies (Clinical Guardrails) */}
                <div className="bg-white rounded-3xl border border-[#DDD9D1] p-5 shadow-soft space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="font-serif text-lg font-bold text-[#D94F7A]">Recorded Allergies</h4>
                    <span className="text-[10px] font-bold text-[#D94F7A] bg-[#FDEEF4] px-2 py-0.5 rounded-full">
                      Hard Safety Rules
                    </span>
                  </div>
                  <div className="space-y-2">
                    {INITIAL_ALLERGIES.map(a => (
                      <div key={a.id} className="p-3 rounded-xl border border-[#FAD3E2] bg-[#FDEEF4]/40 text-xs space-y-1">
                        <div className="font-bold text-[#D94F7A]">{a.allergen}</div>
                        <div className="text-[#6B7A8D] text-[11px]">{a.reaction}</div>
                      </div>
                    ))}
                  </div>
                </div>

              </div>

            </div>
          )}

          {/* TAB 2: Prescription Builder with Real-Time Safety Engine */}
          {activeTab === 'prescribe' && (
            <div className="bg-white rounded-3xl border border-[#DDD9D1] p-6 sm:p-8 shadow-soft space-y-6">
              
              <div className="border-b border-[#DDD9D1] pb-4 flex items-center justify-between">
                <div>
                  <span className="text-[11px] uppercase tracking-wider font-bold text-[#3D8B6E]">Clinical Prescription Workflow</span>
                  <h3 className="font-serif text-2xl font-bold text-[#1C2B3A]">Create New Prescription</h3>
                </div>
                <div className="text-xs text-[#6B7A8D]">
                  Patient: <strong className="text-[#1C2B3A]">{activePatient.name}</strong> ({activePatient.id})
                </div>
              </div>

              {prescriptionSuccess && (
                <div className="p-4 rounded-2xl bg-[#EBF5EC] border border-[#D3EAD7] text-[#2D5A40] text-xs font-bold flex items-center gap-2 animate-in zoom-in-95 duration-200">
                  <CheckCircle2 className="w-5 h-5 text-[#3D8B6E]" />
                  <span>Prescription finalized and signed by Dr. Priya Nair. Patient record and care plan updated in real time!</span>
                </div>
              )}

              <form onSubmit={handleFinalizePrescription} className="space-y-6">
                
                {/* Drug Selection with Safety Trigger simulation */}
                <div className="space-y-2">
                  <label className="text-xs font-bold text-[#1C2B3A]">
                    Select Medicine (Type or click quick-select to test real-time safety checks)
                  </label>
                  
                  {/* Quick-test Pills */}
                  <div className="flex flex-wrap items-center gap-2 pb-1">
                    <span className="text-[11px] text-[#6B7A8D]">Test Safety Triggers:</span>
                    <button
                      type="button"
                      onClick={() => handleDrugInput('Ibuprofen')}
                      className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-[#FEF3E8] text-[#A05520] border border-[#FCDDC1] hover:bg-[#FCDDC1]"
                    >
                      Ibuprofen (Triggers Allergy & Interaction)
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDrugInput('Amoxicillin')}
                      className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-[#FDEEF4] text-[#D94F7A] border border-[#FAD3E2] hover:bg-[#FAD3E2]"
                    >
                      Amoxicillin (Triggers Anaphylaxis Alert)
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDrugInput('Rosuvastatin')}
                      className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-[#FEF3E8] text-[#A05520] border border-[#FCDDC1] hover:bg-[#FCDDC1]"
                    >
                      Rosuvastatin (Triggers Duplicate Statin)
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDrugInput('Hydrochlorothiazide')}
                      className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-[#EBF5EC] text-[#2D5A40] border border-[#D3EAD7] hover:bg-[#D3EAD7]"
                    >
                      Hydrochlorothiazide (Safe Add-on)
                    </button>
                  </div>

                  <input
                    type="text"
                    required
                    value={prescribedDrug}
                    onChange={(e) => handleDrugInput(e.target.value)}
                    placeholder="Enter medicine name (e.g. Hydrochlorothiazide 12.5mg, Telmisartan 40mg)"
                    className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-xl px-4 py-3 text-sm font-semibold text-[#1C2B3A] focus:ring-1 focus:ring-[#3D8B6E] outline-none"
                  />
                </div>

                {/* Real-Time Medication Safety Layer Warnings */}
                {detectedAlerts.length > 0 && (
                  <div className="space-y-3 animate-in slide-in-from-top-2 duration-200">
                    <div className="flex items-center gap-2 text-xs font-bold text-[#D94F7A]">
                      <AlertTriangle className="w-4 h-4 text-[#D94F7A]" />
                      <span>Medication Safety Engine Warnings ({detectedAlerts.length} Conflicts Detected)</span>
                    </div>

                    {detectedAlerts.map(alert => (
                      <div
                        key={alert.id}
                        className={`p-4 rounded-2xl border space-y-1.5 ${
                          alert.severity === 'critical'
                            ? 'bg-[#FDEEF4] border-[#FAD3E2] text-[#D94F7A]'
                            : 'bg-[#FEF3E8] border-[#FCDDC1] text-[#A05520]'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <strong className="text-xs font-bold">{alert.title}</strong>
                          <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-white/80">
                            {alert.severity}
                          </span>
                        </div>
                        <p className="text-xs leading-relaxed">{alert.description}</p>
                        <div className="text-[10px] opacity-80 pt-1 flex items-center justify-between">
                          <span>Drugs involved: {alert.drugsInvolved.join(' + ')}</span>
                          <span>Source: {alert.source}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Dosage, Frequency, Duration */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="space-y-1">
                    <label className="text-xs font-bold text-[#6B7A8D]">Strength / Dosage</label>
                    <input
                      type="text"
                      value={strength}
                      onChange={(e) => setStrength(e.target.value)}
                      className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-xl px-3 py-2 text-xs text-[#1C2B3A] focus:ring-1 focus:ring-[#3D8B6E] outline-none font-semibold"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-bold text-[#6B7A8D]">Frequency</label>
                    <select
                      value={frequency}
                      onChange={(e) => setFrequency(e.target.value)}
                      className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-xl px-3 py-2 text-xs text-[#1C2B3A] focus:ring-1 focus:ring-[#3D8B6E] outline-none font-semibold"
                    >
                      <option>Once daily (OD) - Morning</option>
                      <option>Twice daily (BD) - Morning & Night</option>
                      <option>Thrice daily (TDS)</option>
                      <option>Once daily at bedtime (HS)</option>
                      <option>As needed (SOS)</option>
                    </select>
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-bold text-[#6B7A8D]">Duration</label>
                    <input
                      type="text"
                      value={duration}
                      onChange={(e) => setDuration(e.target.value)}
                      className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-xl px-3 py-2 text-xs text-[#1C2B3A] focus:ring-1 focus:ring-[#3D8B6E] outline-none font-semibold"
                    />
                  </div>
                </div>

                {/* Instructions & Clinical Notes */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className="text-xs font-bold text-[#6B7A8D]">Patient Care Instructions</label>
                    <input
                      type="text"
                      value={instructions}
                      onChange={(e) => setInstructions(e.target.value)}
                      placeholder="e.g. Take with warm water after morning breakfast"
                      className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-xl px-3 py-2 text-xs text-[#1C2B3A] focus:ring-1 focus:ring-[#3D8B6E] outline-none"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-bold text-[#6B7A8D]">Clinical Notes & Rationale</label>
                    <input
                      type="text"
                      value={clinicalNotes}
                      onChange={(e) => setClinicalNotes(e.target.value)}
                      placeholder="Document clinical diagnosis and monitoring rationale"
                      className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-xl px-3 py-2 text-xs text-[#1C2B3A] focus:ring-1 focus:ring-[#3D8B6E] outline-none"
                    />
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="pt-4 border-t border-[#DDD9D1] flex items-center justify-between">
                  <button
                    type="button"
                    onClick={() => setActiveTab('review')}
                    className="text-xs font-semibold text-[#6B7A8D] hover:text-[#1C2B3A]"
                  >
                    ← Back to AI History Review
                  </button>

                  <button
                    type="submit"
                    className="bg-[#3D8B6E] text-white font-semibold text-xs px-6 py-3 rounded-xl hover:bg-[#2D5A40] transition-colors shadow-sm flex items-center gap-2"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Finalize & Sign Prescription</span>
                  </button>
                </div>

              </form>

            </div>
          )}

        </div>
      ) : (
        <div className="bg-white rounded-3xl border border-[#DDD9D1] p-12 text-center space-y-3">
          <Stethoscope className="w-10 h-10 text-[#6B7A8D] mx-auto" />
          <h3 className="font-serif text-xl font-bold text-[#1C2B3A]">No Patient Selected</h3>
          <p className="text-xs text-[#6B7A8D]">
            Enter a unique HealthSetu Patient Identifier above to lookup records and request clinical access.
          </p>
        </div>
      )}

    </div>
  );
};
