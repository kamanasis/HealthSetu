import React from 'react';
import { Stethoscope, Sparkles } from 'lucide-react';
import { TrustBadge } from '../common/Badge';
import { TextReveal, SectionReveal } from '../common/TextReveal';

export const HowItWorks: React.FC = () => {
  const steps = [
    {
      step: '01',
      title: 'Prescription Ingestion & Multimodal Extraction',
      description: 'Patient uploads past physical prescriptions or lab reports. The extraction pipeline parses medications, dosages, frequencies, and doctor signatures.',
      actor: 'Patient Action',
      actorStyle: 'text-[#2B5F8A] bg-[#EBF4FB] border-[#D5E8F8]',
    },
    {
      step: '02',
      title: 'Human-in-the-Loop Verification Gate',
      description: 'Extracted data is held in an unverified state. The patient verifies medication names and instructions before anything enters their official health record.',
      actor: 'Data Trust Gate',
      actorStyle: 'text-[#A05520] bg-[#FEF3E8] border-[#FCDDC1]',
    },
    {
      step: '03',
      title: 'Doctor Lookup & Scoped Consent Request',
      description: 'When visiting a new clinic, the doctor looks up the patient using their unique identifier and issues a time-scoped access request.',
      actor: 'Consent Enforced',
      actorStyle: 'text-[#2D5A40] bg-[#EBF5EC] border-[#D3EAD7]',
    },
    {
      step: '04',
      title: 'Clinical Review & Deterministic Safety Engine',
      description: 'Doctor reviews the longitudinal record and evidence-linked SBAR history. When prescribing, deterministic checks verify interactions and known allergies.',
      actor: 'Doctor Clinical Decision',
      actorStyle: 'text-[#2D5A40] bg-[#EBF5EC] border-[#D3EAD7]',
    },
    {
      step: '05',
      title: 'Immediate Care Plan & Continuity Synchronization',
      description: 'Finalized treatments update the patient’s record in real time and generate a localized, audio-enabled daily medication schedule.',
      actor: 'Care Continuity',
      actorStyle: 'text-[#5B3D8A] bg-[#F5F0FC] border-[#E9DCF8]',
    },
  ];

  return (
    <section className="py-20 max-w-6xl mx-auto px-6 border-b border-[#DDD9D1]">
      <div className="grid lg:grid-cols-12 gap-8 lg:gap-12 items-start">
        
        {/* Left Column: 5-step Protocol Pipeline */}
        <div className="lg:col-span-7 space-y-8">
          <div>
            <SectionReveal>
              <span className="text-[11px] uppercase tracking-wider font-semibold text-[#6B7A8D]">
                Continuity Architecture
              </span>
            </SectionReveal>
            <h2 className="font-serif text-3xl sm:text-4xl text-[#1C2B3A] font-normal mt-2">
              <TextReveal text="How HealthSetu connects care across visits" stagger={0.02} yOffset={24} />
            </h2>
            <SectionReveal delay={0.2}>
              <p className="text-[#6B7A8D] text-sm sm:text-base mt-2 leading-relaxed">
                From fragmented paper slips to verified longitudinal history, every step keeps the patient in control and the clinician fully informed.
              </p>
            </SectionReveal>
          </div>

          <div className="space-y-6">
            {steps.map((item, idx) => (
              <SectionReveal key={idx} delay={idx * 0.08} yOffset={20}>
                <div className="flex gap-4 group">
                  <div className="flex flex-col items-center">
                    <div className="w-7 h-7 rounded-sm bg-[#FAF8F3] border border-[#DDD9D1] text-xs font-mono font-semibold flex items-center justify-center text-[#1C2B3A] group-hover:border-[#1C2B3A] transition-colors">
                      {item.step}
                    </div>
                    {idx < steps.length - 1 && (
                      <div className="w-px h-full bg-[#DDD9D1] my-2" />
                    )}
                  </div>

                  <div className="space-y-1.5 pb-4">
                    <span className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded-sm border ${item.actorStyle}`}>
                      {item.actor}
                    </span>
                    <h4 className="text-sm font-semibold text-[#1C2B3A]">{item.title}</h4>
                    <p className="text-xs text-[#6B7A8D] leading-relaxed max-w-lg">{item.description}</p>
                  </div>
                </div>
              </SectionReveal>
            ))}
          </div>
        </div>

        {/* Right Column: Longitudinal Timeline Specimen */}
        <SectionReveal className="lg:col-span-5 lg:sticky lg:top-24" delay={0.2} yOffset={40}>
          <div className="bg-white rounded-sm border border-[#DDD9D1] p-6 space-y-6">
            
            <div className="flex items-center justify-between border-b border-[#DDD9D1] pb-4">
              <div>
                <span className="text-[10px] uppercase font-mono tracking-wider text-[#6B7A8D]">Longitudinal View</span>
                <h3 className="font-serif text-xl text-[#1C2B3A]">Patient Timeline</h3>
              </div>
              <span className="text-xs font-mono font-medium text-[#4A90C4] bg-[#FAF8F3] border border-[#DDD9D1] px-2.5 py-1 rounded-sm">
                HS-PAT-8921
              </span>
            </div>

            {/* Timeline Stream Specimen */}
            <div className="space-y-3">
              
              {/* Event 1: Verified Consultation */}
              <div className="p-3.5 rounded-sm border border-[#DDD9D1] bg-[#FAF8F3] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-[#1C2B3A]">Cardiology Follow-Up</span>
                  <TrustBadge state="verified" />
                </div>
                <p className="text-xs text-[#6B7A8D]">
                  BP controlled at 126/82 mmHg. Telmisartan 40mg confirmed.
                </p>
                <div className="text-[11px] text-[#6B7A8D] flex items-center gap-1.5 pt-1 border-t border-[#DDD9D1]">
                  <Stethoscope className="w-3 h-3 text-[#3D8B6E]" />
                  <span>Dr. Priya Nair · AIIMS New Delhi · 12 Sep 2026</span>
                </div>
              </div>

              {/* Event 2: Extracted - Pending Verification */}
              <div className="p-3.5 rounded-sm border border-[#FCDDC1] bg-[#FEF3E8] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-[#1C2B3A]">Prescription Slip (Fortis)</span>
                  <TrustBadge state="extracted" />
                </div>
                <p className="text-xs text-[#6B7A8D]">
                  Rosuvastatin 10mg extracted from scan. Awaiting patient confirmation before saving.
                </p>
                <div className="flex items-center justify-between pt-1 border-t border-[#FCDDC1]">
                  <span className="text-[11px] text-[#A05520] font-semibold">Verification Gate Active</span>
                  <span className="text-[11px] font-semibold text-[#4A90C4]">
                    Patient Action Required →
                  </span>
                </div>
              </div>

              {/* Event 3: AI SBAR Summary Insight */}
              <div className="p-3.5 rounded-sm border border-[#DDD9D1] bg-white space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-[#1C2B3A] flex items-center gap-1.5">
                    <Sparkles className="w-3 h-3 text-[#4A90C4]" />
                    AI Longitudinal Synthesis
                  </span>
                  <TrustBadge state="ai-analyzed" />
                </div>
                <p className="text-xs text-[#6B7A8D]">
                  Identified potential statin therapy duplication between Apollo and Fortis records. Flagged for clinician review.
                </p>
                <div className="text-[10px] text-[#6B7A8D] font-mono pt-1 border-t border-[#DDD9D1]">
                  Sources: Apollo (28 Aug) + Fortis (02 Sep)
                </div>
              </div>

            </div>

            <div className="pt-2 border-t border-[#DDD9D1] text-[11px] text-[#6B7A8D]">
              <span>Data Trust Hierarchy: </span>
              <strong className="text-[#1C2B3A] font-semibold">Raw → Extracted → Patient Verified → Clinically Recorded</strong>
            </div>

          </div>
        </SectionReveal>

      </div>
    </section>
  );
};
