import React from 'react';
import { SectionReveal } from '../common/TextReveal';

export const TrustStrip: React.FC = () => {
  const trustItems = [
    {
      index: '01',
      label: 'Patient-Controlled Consent',
      sub: 'Time-scoped, instantly revocable access token',
    },
    {
      index: '02',
      label: 'Deterministic Medication Safety',
      sub: 'Rule-based ontology checks, zero hallucinated data',
    },
    {
      index: '03',
      label: 'Evidence-Linked AI SBAR',
      sub: 'Provenance traceable to primary physical scans',
    },
    {
      index: '04',
      label: 'Verified Facility Capacity',
      sub: 'Freshness-stamped ICU & emergency readiness',
    },
  ];

  return (
    <section className="bg-[#FAF8F3] border-y border-[#DDD9D1] py-8">
      <div className="max-w-6xl mx-auto px-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-[#DDD9D1]">
          {trustItems.map((item, index) => (
            <SectionReveal
              key={index}
              delay={index * 0.08}
              yOffset={16}
              className={`${index > 0 ? 'sm:pl-6' : ''} ${index < trustItems.length - 1 ? 'sm:pr-6' : ''} py-4 sm:py-0`}
            >
              <div className="space-y-1">
                <span className="font-mono text-[10px] text-[#6B7A8D] font-medium tracking-wider">
                  [{item.index}]
                </span>
                <h4 className="text-xs font-semibold text-[#1C2B3A]">{item.label}</h4>
                <p className="text-[11px] text-[#6B7A8D] leading-normal">{item.sub}</p>
              </div>
            </SectionReveal>
          ))}
        </div>
      </div>
    </section>
  );
};
