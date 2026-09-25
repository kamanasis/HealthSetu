import React from 'react';
import { ShieldCheck, Database, Sparkles, Building2, Lock } from 'lucide-react';
import { SectionReveal } from '../common/TextReveal';

export const TrustStrip: React.FC = () => {
  const trustItems = [
    {
      icon: <Lock className="w-4 h-4 text-[#4A90C4]" strokeWidth={2} />,
      label: 'Patient-Controlled Consent',
      sub: 'Time-scoped, instantly revocable access',
    },
    {
      icon: <Database className="w-4 h-4 text-[#3D8B6E]" strokeWidth={2} />,
      label: 'Deterministic Medication Safety',
      sub: 'Authoritative rules, not LLM guesses',
    },
    {
      icon: <Sparkles className="w-4 h-4 text-[#7B5EA7]" strokeWidth={2} />,
      label: 'Evidence-Linked AI Summaries',
      sub: 'Full provenance back to original records',
    },
    {
      icon: <Building2 className="w-4 h-4 text-[#E07B39]" strokeWidth={2} />,
      label: 'Verified Hospital Capacity',
      sub: 'Freshness-tracked ICU & emergency beds',
    },
  ];

  return (
    <section className="bg-[#EBF4FB] border-y border-[#D5E8F8] py-6">
      <div className="max-w-6xl mx-auto px-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {trustItems.map((item, index) => (
            <SectionReveal key={index} delay={index * 0.1} yOffset={24}>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-white border border-[#D5E8F8] flex items-center justify-center shrink-0 shadow-sm">
                  {item.icon}
                </div>
                <div>
                  <h4 className="text-xs font-bold text-[#1C2B3A]">{item.label}</h4>
                  <p className="text-[11px] text-[#6B7A8D]">{item.sub}</p>
                </div>
              </div>
            </SectionReveal>
          ))}
        </div>
      </div>
    </section>
  );
};
