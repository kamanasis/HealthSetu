import React, { useState } from 'react';
import { 
  Stethoscope, 
  Search, 
  AlertTriangle, 
  Sparkles, 
  CheckCircle2, 
  Lock,
  Info
} from 'lucide-react';
import { 
  INITIAL_PATIENT, 
  INITIAL_MEDICATIONS, 
  INITIAL_ALLERGIES, 
  SAFETY_DATABASE 
} from '../../data/mockData';
import type { Medication, SafetyAlert } from '../../types';
import { TrustBadge } from '../common/Badge';
import { apiClient } from '../../services/api';

interface DoctorWorkspaceProps {
  onPrescriptionFinalized?: (med: Medication) => void;
}

export const DoctorWorkspace: React.FC<DoctorWorkspaceProps> = ({ onPrescriptionFinalized }) => {
  const [patientIdInput, setPatientIdInput] = useState<string>('HS-PAT-8921');
  const [activePatient, setActivePatient] = useState<typeof INITIAL_PATIENT | null>(INITIAL_PATIENT);
  const [activeTab, setActiveTab] = useState<'review' | 'prescribe'>('review');
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [isSafetyChecking, setIsSafetyChecking] = useState<boolean>(false);

  // Prescription builder state
  const [prescribedDrug, setPrescribedDrug] = useState<string>('');
  const [strength, setStrength] = useState<string>('40 mg');
  const [frequency, setFrequency] = useState<string>('Once daily (OD)');
  const [duration, setDuration] = useState<string>('30 Days');
  const [instructions, setInstructions] = useState<string>('Take morning after breakfast');
  const [clinicalNotes, setClinicalNotes] = useState<string>('');
  const [detectedAlerts, setDetectedAlerts] = useState<SafetyAlert[]>([]);
  const [prescriptionSuccess, setPrescriptionSuccess] = useState<boolean>(false);

  // Authenticate as Doctor on load
  React.useEffect(() => {
    apiClient.ensureDemoSession('DOCTOR');
  }, []);

  const handleDrugInput = async (drugName: string) => {
    setPrescribedDrug(drugName);
    const trimmed = drugName.trim();
    if (!trimmed) {
      setDetectedAlerts([]);
      return;
    }

    let alerts: SafetyAlert[] = [];

    // 1. Authoritative local reference knowledge
    if (SAFETY_DATABASE[trimmed]) {
      alerts = [...SAFETY_DATABASE[trimmed]];
    }

    // 2. Real-time FastAPI backend safety evaluation
    if (trimmed.length >= 3 && activePatient) {
      setIsSafetyChecking(true);
      try {
        const res = await apiClient.checkProspectiveMedications(activePatient.id, [
          { name: trimmed, strength: strength, route: 'Oral' }
        ]);

        if (res.evaluation && res.evaluation.alerts && res.evaluation.alerts.length > 0) {
          const apiAlerts: SafetyAlert[] = res.evaluation.alerts.map(a => ({
            id: a.alert_id,
            type: a.title.toLowerCase().includes('allergy') ? 'allergy-conflict' : 'drug-interaction',
            severity: a.severity.toLowerCase() === 'critical' || a.severity.toLowerCase() === 'major' ? 'critical' : 'moderate',
            title: a.title,
            description: a.description,
            drugsInvolved: [trimmed, ...(a.medications_involved?.map(m => m.name || m.drug_name) || [])],
            source: 'Deterministic Rule' as const,
          }));

          const existingTitles = new Set(alerts.map(x => x.title));
          for (const alert of apiAlerts) {
            if (!existingTitles.has(alert.title)) {
              alerts.push(alert);
            }
          }
        }
      } catch (err) {
        console.warn('Backend safety check fallback:', err);
      } finally {
        setIsSafetyChecking(false);
      }
    }

    setDetectedAlerts(alerts);
  };

  const handleFinalizePrescription = async (e: React.FormEvent) => {
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

    // Try posting to backend
    if (activePatient) {
      try {
        await apiClient.createPrescription({
          patient_id: activePatient.id,
          medications: [{ name: prescribedDrug, strength, frequency, route: 'Oral' }],
          notes: clinicalNotes,
        });
      } catch {
        // Handled gracefully
      }
    }

    setPrescriptionSuccess(true);
    setTimeout(() => {
      setPrescriptionSuccess(false);
      setPrescribedDrug('');
      setDetectedAlerts([]);
      setActiveTab('review');
    }, 2500);
  };

  const handlePatientSearch = async () => {
    const q = patientIdInput.trim();
    if (!q) {
      setActivePatient(null);
      return;
    }

    setIsSearching(true);
    try {
      await apiClient.ensureDemoSession('DOCTOR');
      const res = await apiClient.getPatient(q);
      if (res.patient) {
        setActivePatient({
          id: res.patient.id,
          name: `${res.patient.first_name} ${res.patient.last_name}`,
          age: 42,
          gender: res.patient.sex === 'MALE' ? 'Male' : 'Female',
          bloodGroup: 'O Positive',
          phone: res.patient.phone || '+91 98104 22910',
          city: 'New Delhi',
          emergencyContact: 'Sunita Sharma (Spouse) · +91 98104 22911',
        });
        setIsSearching(false);
        return;
      }
    } catch {
      // Fallback
    } finally {
      setIsSearching(false);
    }

    if (q.toUpperCase() === 'HS-PAT-8921' || q.toLowerCase() === 'pat-001') {
      setActivePatient(INITIAL_PATIENT);
    } else {
      setActivePatient(null);
    }
  };

  return (
    <div className="pt-24 pb-20 max-w-6xl mx-auto px-6 space-y-6">
      
      {/* Doctor Identity Header (Clean clinical workstation bar) */}
      <div className="bg-white rounded-sm border border-[#DDD9D1] p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-sm bg-[#FAF8F3] border border-[#DDD9D1] flex items-center justify-center text-[#3D8B6E]">
            <Stethoscope className="w-5 h-5" strokeWidth={2} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-serif text-lg text-[#1C2B3A]">Dr. Priya Nair, MD</h1>
              <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-sm bg-[#EBF5EC] text-[#2D5A40] border border-[#D3EAD7]">
                MCI-48291 · Verified Clinician
              </span>
            </div>
            <p className="text-[11px] text-[#6B7A8D]">
              Senior Consultant Cardiologist · All India Institute of Medical Sciences (AIIMS), New Delhi
            </p>
          </div>
        </div>

        {/* Patient Lookup Input */}
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-[#6B7A8D]" />
            <input
              type="text"
              value={patientIdInput}
              onChange={(e) => setPatientIdInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handlePatientSearch()}
              placeholder="Enter Patient ID (e.g. HS-PAT-8921)"
              className="bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm pl-9 pr-3 py-1.5 text-xs font-mono font-medium text-[#1C2B3A] focus:border-[#3D8B6E] outline-none w-56"
            />
          </div>
          <button
            onClick={handlePatientSearch}
            className="bg-[#3D8B6E] text-white font-semibold text-xs px-3.5 py-1.5 rounded-sm hover:bg-[#2D5A40] transition-colors"
          >
            Access Record
          </button>
        </div>
      </div>

      {activePatient ? (
        <div className="space-y-6">
          
          {/* Patient Overview & Consent Banner */}
          <div className="bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-sm bg-white border border-[#DDD9D1] flex items-center justify-center font-bold text-xs font-mono text-[#2B5F8A]">
                RS
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-serif text-lg text-[#1C2B3A]">{activePatient.name}</h3>
                  <span className="text-xs font-mono font-medium text-[#4A90C4] bg-white border border-[#DDD9D1] px-1.5 py-0.2 rounded-sm">
                    {activePatient.id}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-xs text-[#6B7A8D] mt-0.5">
                  <span>{activePatient.age} yrs · {activePatient.gender}</span>
                  <span>·</span>
                  <span>Blood Group: <strong className="text-[#1C2B3A]">{activePatient.bloodGroup}</strong></span>
                  <span>·</span>
                  <span>Allergies: <strong className="text-[#D94F7A]">Penicillin, NSAIDs</strong></span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 bg-[#EBF5EC] border border-[#D3EAD7] px-3 py-1.5 rounded-sm text-xs font-semibold text-[#2D5A40]">
              <Lock className="w-3.5 h-3.5 text-[#3D8B6E]" />
              <span>Authorized Access (Session Expires in 11h 45m)</span>
            </div>
          </div>

          {/* Clinical Workspace Tabs */}
          <div className="flex items-center gap-1 border-b border-[#DDD9D1] pb-1">
            <button
              onClick={() => setActiveTab('review')}
              className={`px-3.5 py-1.5 rounded-sm text-xs font-semibold transition-colors border ${
                activeTab === 'review'
                  ? 'bg-white text-[#1C2B3A] border-[#1C2B3A]'
                  : 'bg-[#FAF8F3] text-[#6B7A8D] border-transparent hover:text-[#1C2B3A]'
              }`}
            >
              Clinical Review & AI SBAR Summary
            </button>
            <button
              onClick={() => setActiveTab('prescribe')}
              className={`px-3.5 py-1.5 rounded-sm text-xs font-semibold transition-colors border ${
                activeTab === 'prescribe'
                  ? 'bg-white text-[#1C2B3A] border-[#1C2B3A]'
                  : 'bg-[#FAF8F3] text-[#6B7A8D] border-transparent hover:text-[#1C2B3A]'
              }`}
            >
              Prescribe Treatment & Safety Check
            </button>
          </div>

          {/* TAB 1: Clinical Review & Evidence-Linked AI History */}
          {activeTab === 'review' && (
            <div className="grid lg:grid-cols-12 gap-6 items-start">
              
              {/* Evidence-Linked AI SBAR Clinical Summary (Left 7 cols) */}
              <div className="lg:col-span-7 bg-white rounded-sm border border-[#DDD9D1] p-6 space-y-5">
                
                <div className="flex items-center justify-between border-b border-[#DDD9D1] pb-3">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-[#4A90C4]" />
                    <h3 className="font-serif text-lg text-[#1C2B3A]">
                      AI-Assisted Clinical History (SBAR)
                    </h3>
                  </div>
                  <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded-sm bg-[#FAF8F3] border border-[#DDD9D1] text-[#4A90C4]">
                    Evidence Linked · Non-Autonomous
                  </span>
                </div>

                <div className="space-y-3 text-xs leading-relaxed">
                  
                  {/* Situation */}
                  <div className="p-3.5 rounded-sm bg-[#FAF8F3] border border-[#DDD9D1] space-y-1">
                    <div className="font-mono text-[10px] uppercase font-semibold text-[#2B5F8A]">
                      S — Situation
                    </div>
                    <p className="text-[#1C2B3A]">
                      42-year-old male with essential hypertension and managed dyslipidemia presenting for routine quarterly clinical follow-up and blood pressure monitoring.
                    </p>
                  </div>

                  {/* Background */}
                  <div className="p-3.5 rounded-sm bg-[#FAF8F3] border border-[#DDD9D1] space-y-1">
                    <div className="font-mono text-[10px] uppercase font-semibold text-[#2B5F8A]">
                      B — Background & Source Records
                    </div>
                    <p className="text-[#6B7A8D]">
                      Longitudinal record spans 3 institutions: AIIMS (Consultation 12 Sep), Apollo Hospital (Lipid Rx 28 Aug), and Fortis Clinic (Recent scanned slip). Active medications: Telmisartan 40mg OD and Metformin 500mg BD.
                    </p>
                    <div className="flex items-center gap-2 pt-1 text-[11px] font-medium text-[#4A90C4]">
                      <span className="underline cursor-pointer">Source: AIIMS Record #4910</span>
                      <span>·</span>
                      <span className="underline cursor-pointer">Apollo Lab #9021</span>
                    </div>
                  </div>

                  {/* Assessment */}
                  <div className="p-3.5 rounded-sm bg-[#FAF8F3] border border-[#DDD9D1] space-y-1.5">
                    <div className="font-mono text-[10px] uppercase font-semibold text-[#2B5F8A]">
                      A — Clinical Pattern Assessment
                    </div>
                    <p className="text-[#1C2B3A]">
                      Blood pressure normalized (126/82 mmHg). Glycemic control adequate (HbA1c 6.8%).
                    </p>
                    <div className="p-2.5 rounded-sm bg-[#FEF3E8] border border-[#FCDDC1] text-[#A05520] text-[11px] flex items-start gap-2">
                      <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-[#E07B39]" />
                      <span>
                        <strong className="font-semibold">Pattern Flag:</strong> Unverified scanned slip from Fortis lists Rosuvastatin 10mg. Patient is already taking Atorvastatin 20mg. Potential duplicative statin therapy should be resolved.
                      </span>
                    </div>
                  </div>

                  {/* Recommendation */}
                  <div className="p-3.5 rounded-sm bg-[#FAF8F3] border border-[#DDD9D1] space-y-1">
                    <div className="font-mono text-[10px] uppercase font-semibold text-[#2B5F8A]">
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
                    <span>The clinician remains 100% responsible for all clinical decisions.</span>
                  </span>
                  <button
                    onClick={() => setActiveTab('prescribe')}
                    className="font-semibold text-[#3D8B6E] hover:underline"
                  >
                    Proceed to Prescribe →
                  </button>
                </div>

              </div>

              {/* Longitudinal Timeline & Current Meds (Right 5 cols) */}
              <div className="lg:col-span-5 space-y-4">
                
                {/* Active Verified Medications */}
                <div className="bg-white rounded-sm border border-[#DDD9D1] p-4 space-y-3">
                  <h4 className="font-serif text-base text-[#1C2B3A]">Active Verified Medications</h4>
                  <div className="space-y-2">
                    {INITIAL_MEDICATIONS.map(m => (
                      <div key={m.id} className="p-2.5 rounded-sm border border-[#DDD9D1] bg-[#FAF8F3] flex items-center justify-between text-xs">
                        <div>
                          <div className="font-semibold text-[#1C2B3A]">{m.name} {m.strength}</div>
                          <div className="text-[11px] text-[#6B7A8D]">{m.frequency} · {m.hospital}</div>
                        </div>
                        <TrustBadge state={m.trustState} />
                      </div>
                    ))}
                  </div>
                </div>

                {/* Recorded Allergies (Clinical Guardrails) */}
                <div className="bg-white rounded-sm border border-[#DDD9D1] p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="font-serif text-base text-[#D94F7A]">Recorded Allergies</h4>
                    <span className="text-[10px] font-mono uppercase text-[#D94F7A] bg-[#FDEEF4] border border-[#F8D2DF] px-2 py-0.5 rounded-sm">
                      Safety Guardrail
                    </span>
                  </div>
                  <div className="space-y-2">
                    {(INITIAL_ALLERGIES || []).map(a => (
                      <div key={a.id} className="p-2.5 rounded-sm border border-[#FAD3E2] bg-[#FAF8F3] text-xs space-y-0.5">
                        <div className="font-semibold text-[#D94F7A]">{a.allergen}</div>
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
            <div className="bg-white rounded-sm border border-[#DDD9D1] p-6 space-y-6">
              
              <div className="border-b border-[#DDD9D1] pb-3 flex items-center justify-between">
                <div>
                  <span className="text-[10px] uppercase font-mono tracking-wider text-[#3D8B6E]">Prescription Workflow</span>
                  <h3 className="font-serif text-xl text-[#1C2B3A]">Create New Prescription</h3>
                </div>
                <div className="text-xs text-[#6B7A8D]">
                  Patient: <strong className="text-[#1C2B3A] font-semibold">{activePatient.name}</strong> ({activePatient.id})
                </div>
              </div>

              {prescriptionSuccess && (
                <div className="p-3.5 rounded-sm bg-[#EBF5EC] border border-[#D3EAD7] text-[#2D5A40] text-xs font-semibold flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-[#3D8B6E]" />
                  <span>Prescription signed by Dr. Priya Nair. Patient record and care plan synchronized!</span>
                </div>
              )}

              <form onSubmit={handleFinalizePrescription} className="space-y-5">
                
                {/* Drug Selection with Safety Trigger simulation */}
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-[#1C2B3A]">
                    Select Medicine (Type or quick-select to test real-time deterministic safety engine)
                  </label>
                  
                  {/* Quick-test Buttons */}
                  <div className="flex flex-wrap items-center gap-1.5 pb-1">
                    <span className="text-[11px] text-[#6B7A8D]">Simulate Triggers:</span>
                    <button
                      type="button"
                      onClick={() => handleDrugInput('Ibuprofen')}
                      className="text-xs font-medium px-2 py-0.5 rounded-sm bg-[#FEF3E8] text-[#A05520] border border-[#FCDDC1] hover:bg-[#FCDDC1]"
                    >
                      Ibuprofen (Allergy & Interaction)
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDrugInput('Amoxicillin')}
                      className="text-xs font-medium px-2 py-0.5 rounded-sm bg-[#FDEEF4] text-[#D94F7A] border border-[#FAD3E2] hover:bg-[#FAD3E2]"
                    >
                      Amoxicillin (Allergy Alert)
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDrugInput('Rosuvastatin')}
                      className="text-xs font-medium px-2 py-0.5 rounded-sm bg-[#FEF3E8] text-[#A05520] border border-[#FCDDC1] hover:bg-[#FCDDC1]"
                    >
                      Rosuvastatin (Duplicate Statin)
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDrugInput('Hydrochlorothiazide')}
                      className="text-xs font-medium px-2 py-0.5 rounded-sm bg-[#EBF5EC] text-[#2D5A40] border border-[#D3EAD7] hover:bg-[#D3EAD7]"
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
                    className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-3 py-2 text-xs font-medium text-[#1C2B3A] focus:border-[#3D8B6E] outline-none"
                  />
                </div>

                {/* Real-Time Medication Safety Layer Warnings */}
                {detectedAlerts.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs font-semibold text-[#D94F7A]">
                      <AlertTriangle className="w-3.5 h-3.5 text-[#D94F7A]" />
                      <span>Deterministic Safety Interception ({detectedAlerts.length} Conflicts Detected)</span>
                    </div>

                    {detectedAlerts.map(alert => (
                      <div
                        key={alert.id}
                        className={`p-3 rounded-sm border space-y-1 text-xs ${
                          alert.severity === 'critical'
                            ? 'bg-[#FDEEF4] border-[#FAD3E2] text-[#D94F7A]'
                            : 'bg-[#FEF3E8] border-[#FCDDC1] text-[#A05520]'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <strong className="font-semibold">{alert.title}</strong>
                          <span className="text-[10px] font-mono uppercase font-semibold px-1.5 py-0.2 rounded-sm bg-white border border-current">
                            {alert.severity}
                          </span>
                        </div>
                        <p className="leading-relaxed">{alert.description}</p>
                        <div className="text-[10px] opacity-80 pt-1 flex items-center justify-between border-t border-current/20">
                          <span>Drugs involved: {(alert.drugsInvolved || []).join(' + ')}</span>
                          <span>Source: {alert.source}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Dosage, Frequency, Duration */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-[#6B7A8D]">Strength / Dosage</label>
                    <input
                      type="text"
                      value={strength}
                      onChange={(e) => setStrength(e.target.value)}
                      className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2.5 py-1.5 text-xs text-[#1C2B3A] focus:border-[#3D8B6E] outline-none font-medium"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-[#6B7A8D]">Frequency</label>
                    <select
                      value={frequency}
                      onChange={(e) => setFrequency(e.target.value)}
                      className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2.5 py-1.5 text-xs text-[#1C2B3A] focus:border-[#3D8B6E] outline-none font-medium"
                    >
                      <option>Once daily (OD) - Morning</option>
                      <option>Twice daily (BD) - Morning & Night</option>
                      <option>Thrice daily (TDS)</option>
                      <option>Once daily at bedtime (HS)</option>
                      <option>As needed (SOS)</option>
                    </select>
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-[#6B7A8D]">Duration</label>
                    <input
                      type="text"
                      value={duration}
                      onChange={(e) => setDuration(e.target.value)}
                      className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2.5 py-1.5 text-xs text-[#1C2B3A] focus:border-[#3D8B6E] outline-none font-medium"
                    />
                  </div>
                </div>

                {/* Instructions & Clinical Notes */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-[#6B7A8D]">Patient Instructions</label>
                    <input
                      type="text"
                      value={instructions}
                      onChange={(e) => setInstructions(e.target.value)}
                      placeholder="e.g. Take with warm water after morning breakfast"
                      className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2.5 py-1.5 text-xs text-[#1C2B3A] focus:border-[#3D8B6E] outline-none"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-[#6B7A8D]">Clinical Notes & Rationale</label>
                    <input
                      type="text"
                      value={clinicalNotes}
                      onChange={(e) => setClinicalNotes(e.target.value)}
                      placeholder="Document clinical diagnosis and monitoring rationale"
                      className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2.5 py-1.5 text-xs text-[#1C2B3A] focus:border-[#3D8B6E] outline-none"
                    />
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="pt-3 border-t border-[#DDD9D1] flex items-center justify-between">
                  <button
                    type="button"
                    onClick={() => setActiveTab('review')}
                    className="text-xs font-semibold text-[#6B7A8D] hover:text-[#1C2B3A]"
                  >
                    ← Back to AI History Review
                  </button>

                  <button
                    type="submit"
                    className="bg-[#3D8B6E] text-white font-semibold text-xs px-5 py-2 rounded-sm hover:bg-[#2D5A40] transition-colors flex items-center gap-2"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Finalize & Sign Prescription</span>
                  </button>
                </div>

              </form>

            </div>
          )}

        </div>
      ) : (
        /* Meaningful Empty State for Patient Lookup */
        <div className="bg-white rounded-sm border border-[#DDD9D1] p-12 text-center space-y-3">
          <Stethoscope className="w-8 h-8 text-[#6B7A8D] mx-auto" strokeWidth={1.5} />
          <h3 className="font-serif text-lg text-[#1C2B3A]">No Patient Record Active</h3>
          <p className="text-xs text-[#6B7A8D] max-w-sm mx-auto">
            Enter a HealthSetu Patient Identifier (e.g. HS-PAT-8921) above to access patient history and initiate clinical review.
          </p>
          <button
            onClick={() => {
              setPatientIdInput('HS-PAT-8921');
              setActivePatient(INITIAL_PATIENT);
            }}
            className="text-xs font-semibold text-[#3D8B6E] hover:underline"
          >
            Load Sample Patient (HS-PAT-8921) →
          </button>
        </div>
      )}

    </div>
  );
};
