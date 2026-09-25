import React from 'react';
import { 
  FileText, 
  ScanLine, 
  ShieldCheck, 
  AlertTriangle, 
  Sparkles, 
  CalendarClock, 
  Volume2, 
  Building2, 
  Activity,
  Check
} from 'lucide-react';
import { TextReveal, SectionReveal } from '../common/TextReveal';

export const FeaturesGrid: React.FC = () => {
  const capabilities = [
    {
      index: '01',
      title: 'Longitudinal Health Record',
      description: 'Preserves your complete healthcare journey across clinics, labs, and hospital visits in a single patient-owned timeline.',
      domain: 'Continuity',
    },
    {
      index: '02',
      title: 'Prescription Intelligence & OCR',
      description: 'Multimodal extraction of physical slips followed by mandatory patient verification before saving to the permanent record.',
      domain: 'Ingestion',
    },
    {
      index: '03',
      title: 'Consent-Controlled Access & 1-Click Revocation',
      description: 'Consulting clinicians request time-scoped access. Patients view active sessions with complete audit trails and instant revocation.',
      domain: 'Governance',
    },
    {
      index: '04',
      title: 'Evidence-Linked AI SBAR Summaries',
      description: 'Surfaces recurring symptoms, medication changes, and patterns with clickable links directly back to original clinical records.',
      domain: 'Decision Support',
    },
    {
      index: '05',
      title: 'Actionable & Multilingual Care Plans',
      description: 'Translates post-visit instructions into morning, afternoon, and bedtime tasks with meal cues and audio synthesis in regional languages.',
      domain: 'Adherence',
    },
    {
      index: '06',
      title: 'Hospital Capacity & Emergency Routing',
      description: 'Live availability tracking for ICU beds, Cath Labs, and trauma suites so emergency decisions are never based on stale information.',
      domain: 'Operations',
    },
  ];

  return (
    <section className="bg-white py-20 border-b border-[#DDD9D1]">
      <div className="max-w-6xl mx-auto px-6 space-y-12">
        
        {/* Section Header */}
        <div className="max-w-2xl space-y-3">
          <SectionReveal>
            <span className="text-[11px] uppercase tracking-wider font-semibold text-[#6B7A8D]">
              Platform Architecture
            </span>
          </SectionReveal>
          <h2 className="font-serif text-3xl sm:text-4xl text-[#1C2B3A] font-normal leading-tight">
            <TextReveal text="Designed for clinical safety, trust, and continuity" stagger={0.02} yOffset={24} />
          </h2>
          <SectionReveal delay={0.2}>
            <p className="text-[#6B7A8D] text-sm sm:text-base leading-relaxed">
              Every system capability is governed by deterministic safety rules and cryptographic consent. No hallucinated health records, no unverified data ingestion.
            </p>
          </SectionReveal>
        </div>

        {/* Asymmetric Composition: Flagship Capability Feature Split */}
        <SectionReveal delay={0.1} yOffset={30}>
          <div className="bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm p-6 sm:p-8">
            <div className="grid lg:grid-cols-12 gap-8 items-center">
              
              <div className="lg:col-span-6 space-y-4">
                <span className="font-mono text-[10px] uppercase font-semibold text-[#4A90C4]">
                  Flagship Capability
                </span>
                <h3 className="font-serif text-2xl text-[#1C2B3A] font-normal">
                  Deterministic Medication Safety Engine
                </h3>
                <p className="text-xs text-[#6B7A8D] leading-relaxed">
                  Unlike generative models that can fabricate drug interactions, HealthSetu runs deterministic checks against curated medical ontologies (RxNorm, OpenFDA, and CDSCO guidelines).
                </p>
                <div className="space-y-2 pt-2 text-xs text-[#1C2B3A]">
                  <div className="flex items-center gap-2">
                    <Check className="w-3.5 h-3.5 text-[#3D8B6E]" strokeWidth={2.5} />
                    <span>Real-time Drug-Drug Interaction analysis</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Check className="w-3.5 h-3.5 text-[#3D8B6E]" strokeWidth={2.5} />
                    <span>Cross-visit duplicate therapy detection</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Check className="w-3.5 h-3.5 text-[#3D8B6E]" strokeWidth={2.5} />
                    <span>Documented allergy conflict interception</span>
                  </div>
                </div>
              </div>

              {/* Specimen Safety Alert Output */}
              <div className="lg:col-span-6 bg-white border border-[#DDD9D1] p-4 rounded-sm space-y-3">
                <div className="flex items-center justify-between border-b border-[#DDD9D1] pb-2 text-xs">
                  <span className="font-mono font-semibold text-[#1C2B3A]">CLINICAL SAFETY ALERT #MS-842</span>
                  <span className="text-[10px] font-semibold text-[#A05520] bg-[#FEF3E8] border border-[#FCDDC1] px-2 py-0.5 rounded-sm">
                    Moderate Risk
                  </span>
                </div>
                <div className="text-xs text-[#1C2B3A] space-y-1">
                  <div className="font-semibold text-[#D94F7A]">Interaction: Telmisartan + Ibuprofen / NSAIDs</div>
                  <p className="text-[11px] text-[#6B7A8D] leading-normal">
                    Concomitant use may diminish the antihypertensive effect of Telmisartan and increase the risk of renal impairment in hypertensive patients.
                  </p>
                </div>
                <div className="border-t border-[#DDD9D1] pt-2 text-[10px] font-mono text-[#6B7A8D] flex items-center justify-between">
                  <span>Engine: Deterministic Rule Matrix v7</span>
                  <span className="text-[#3D8B6E] font-semibold">Interception Verified</span>
                </div>
              </div>

            </div>
          </div>
        </SectionReveal>

        {/* Structured Capability Matrix (Clean hairline grid, zero rounded pill cards) */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 border border-[#DDD9D1] divide-y sm:divide-y-0 sm:divide-x divide-[#DDD9D1] bg-white">
          {capabilities.map((cap, idx) => (
            <SectionReveal
              key={idx}
              delay={idx * 0.05}
              yOffset={16}
              className={`p-6 space-y-3 hover:bg-[#FAF8F3] transition-colors ${
                idx >= 3 ? 'sm:border-t sm:border-[#DDD9D1]' : ''
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-[#6B7A8D] font-medium">[{cap.index}]</span>
                <span className="text-[10px] font-mono uppercase text-[#6B7A8D]">{cap.domain}</span>
              </div>
              <h4 className="text-sm font-semibold text-[#1C2B3A]">{cap.title}</h4>
              <p className="text-xs text-[#6B7A8D] leading-relaxed">{cap.description}</p>
            </SectionReveal>
          ))}
        </div>

      </div>
    </section>
  );
};
