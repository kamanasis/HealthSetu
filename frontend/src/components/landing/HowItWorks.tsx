import React from 'react';
import { ArrowRight, CheckCircle2, ShieldCheck, Sparkles, UploadCloud, Stethoscope, HeartPulse, Clock } from 'lucide-react';
import { TrustBadge } from '../common/Badge';

export const HowItWorks: React.FC = () => {
  const steps = [
    {
      step: '01',
      title: 'Prescription Ingestion & Multimodal Extraction',
      description: 'Patient uploads past physical prescriptions or lab reports. The AI extraction pipeline parses medications, dosages, frequencies, and doctor signatures.',
      actor: 'Patient Action',
      badgeColor: 'bg-[#EBF4FB] text-[#2B5F8A]',
    },
    {
      step: '02',
      title: 'Human-in-the-Loop Verification Gate',
      description: 'Extracted data is held in an unverified state. The patient verifies medication names and instructions before anything becomes part of their official record.',
      actor: 'Data Trust Gate',
      badgeColor: 'bg-[#FEF3E8] text-[#A05520]',
    },
    {
      step: '03',
      title: 'Doctor Lookup & Scoped Consent Request',
      description: 'When visiting a new hospital or clinic, the doctor looks up the patient using their unique identifier and sends a time-scoped access request.',
      actor: 'Consent Enforced',
      badgeColor: 'bg-[#EBF5EC] text-[#2D5A40]',
    },
    {
      step: '04',
      title: 'Clinical Review & Real-Time Safety Engine',
      description: 'Doctor reviews the longitudinal record and evidence-linked AI history. When prescribing, deterministic safety checks catch drug interactions and allergies.',
      actor: 'Doctor Clinical Decision',
      badgeColor: 'bg-[#EBF5EC] text-[#3D8B6E]',
    },
    {
      step: '05',
      title: 'Immediate Care Plan & Continuity Update',
      description: 'Finalized treatments automatically update the patient’s record and generate a localized, audio-enabled daily medication schedule.',
      actor: 'Care Continuity',
      badgeColor: 'bg-[#F5F0FC] text-[#5B3D8A]',
    },
  ];

  return (
    <section className="py-20 max-w-6xl mx-auto px-6 border-b border-[#DDD9D1]">
      <div className="grid lg:grid-cols-12 gap-12 lg:gap-16 items-start">
        
        {/* Left Column: 5-step journey */}
        <div className="lg:col-span-7 space-y-8">
          <div>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#FAF8F3] border border-[#DDD9D1] text-[#6B7A8D]">
              Healthcare Continuity Loop
            </span>
            <h2 className="font-serif text-3xl sm:text-4xl text-[#1C2B3A] mt-3">
              How HealthSetu connects care across visits
            </h2>
            <p className="text-[#6B7A8D] text-base mt-2">
              From fragmented paper prescriptions to verified longitudinal history, every step keeps the patient in control and the clinician fully informed.
            </p>
          </div>

          <div className="space-y-6">
            {steps.map((item, idx) => (
              <div key={idx} className="flex gap-4 group">
                <div className="flex flex-col items-center">
                  <div className="w-8 h-8 rounded-full bg-[#FAF8F3] border border-[#DDD9D1] text-xs font-bold flex items-center justify-center text-[#1C2B3A] group-hover:border-[#4A90C4] group-hover:text-[#4A90C4] transition-colors">
                    {item.step}
                  </div>
                  {idx < steps.length - 1 && (
                    <div className="w-px h-full bg-[#DDD9D1] my-1" />
                  )}
                </div>

                <div className="space-y-1 pb-4">
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${item.badgeColor}`}>
                      {item.actor}
                    </span>
                  </div>
                  <h4 className="text-sm font-bold text-[#1C2B3A]">{item.title}</h4>
                  <p className="text-xs text-[#6B7A8D] leading-relaxed max-w-lg">{item.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: Longitudinal Timeline Card */}
        <div className="lg:col-span-5 lg:sticky lg:top-24">
          <div className="bg-white rounded-3xl border border-[#DDD9D1] p-6 shadow-soft space-y-6">
            
            <div className="flex items-center justify-between border-b border-[#DDD9D1] pb-4">
              <div>
                <span className="text-[11px] uppercase tracking-wider font-bold text-[#6B7A8D]">Longitudinal View</span>
                <h3 className="font-serif text-xl font-bold text-[#1C2B3A]">Patient Timeline</h3>
              </div>
              <span className="text-xs font-mono font-bold text-[#4A90C4] bg-[#EBF4FB] px-2.5 py-1 rounded-lg">
                HS-PAT-8921
              </span>
            </div>

            {/* Timeline Stream Preview */}
            <div className="space-y-4">
              
              {/* Event 1: Verified Consultation */}
              <div className="p-3.5 rounded-2xl border border-[#DDD9D1] bg-[#FAF8F3]/60 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-[#1C2B3A]">Cardiology Follow-Up</span>
                  <TrustBadge state="verified" />
                </div>
                <p className="text-xs text-[#6B7A8D]">
                  BP normalized to 126/82 mmHg. Telmisartan 40mg confirmed.
                </p>
                <div className="text-[11px] text-[#6B7A8D] flex items-center gap-1.5 pt-1">
                  <Stethoscope className="w-3.5 h-3.5 text-[#3D8B6E]" />
                  <span>Dr. Priya Nair · AIIMS New Delhi</span>
                  <span>·</span>
                  <span>12 Sep 2026</span>
                </div>
              </div>

              {/* Event 2: Extracted - Pending Verification */}
              <div className="p-3.5 rounded-2xl border border-[#E07B39]/40 bg-[#FEF3E8]/40 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-[#1C2B3A]">Scanned Prescription (Fortis)</span>
                  <TrustBadge state="extracted" />
                </div>
                <p className="text-xs text-[#6B7A8D]">
                  Rosuvastatin 10mg extracted from handwritten slip. Needs patient review before confirming.
                </p>
                <div className="flex items-center justify-between pt-1">
                  <span className="text-[11px] text-[#A05520] font-semibold">Verification Gate Active</span>
                  <button className="text-[11px] font-bold text-[#4A90C4] hover:underline">
                    Review Fields →
                  </button>
                </div>
              </div>

              {/* Event 3: AI SBAR Summary Insight */}
              <div className="p-3.5 rounded-2xl border border-[#D5E8F8] bg-[#EBF4FB]/50 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-[#1C2B3A] flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-[#4A90C4]" />
                    AI Cross-Consultation Insight
                  </span>
                  <TrustBadge state="ai-analyzed" />
                </div>
                <p className="text-xs text-[#6B7A8D]">
                  Identified potential statin therapy duplication between Apollo and Fortis records. Flagged for clinician review.
                </p>
                <div className="text-[10px] text-[#2B5F8A] font-semibold">
                  Source Records: Apollo (28 Aug) + Fortis (02 Sep)
                </div>
              </div>

            </div>

            <div className="text-center pt-2 border-t border-[#DDD9D1]">
              <p className="text-xs text-[#6B7A8D]">
                Data Trust Hierarchy: <span className="font-semibold text-[#1C2B3A]">Raw → Extracted → Patient Verified → Clinically Recorded → AI Analyzed</span>
              </p>
            </div>

          </div>
        </div>

      </div>
    </section>
  );
};
