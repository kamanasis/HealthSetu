import React from 'react';
import { ArrowRight, ShieldCheck } from 'lucide-react';
import { TextReveal, SectionReveal } from '../common/TextReveal';
import type { Role } from '../../types';

interface CTAProps {
  onSelectRole: (role: Role) => void;
}

export const CTA: React.FC<CTAProps> = ({ onSelectRole }) => {
  return (
    <section className="py-24 max-w-6xl mx-auto px-6">
      <SectionReveal yOffset={32}>
        <div className="bg-white border border-[#DDD9D1] rounded-sm p-8 sm:p-12 text-center space-y-6">
          
          <div className="max-w-2xl mx-auto space-y-3">
            <span className="text-[11px] uppercase tracking-wider font-semibold text-[#6B7A8D]">
              Start Healthcare Continuity
            </span>
            <h2 className="font-serif text-3xl sm:text-4xl text-[#1C2B3A] font-normal tracking-tight">
              <TextReveal text="Healthcare works better when information is connected" stagger={0.02} yOffset={24} />
            </h2>
            <SectionReveal delay={0.2}>
              <p className="text-sm sm:text-base text-[#6B7A8D] leading-relaxed">
                Eliminate fragmented paper records, repeated diagnostic tests, and emergency facility blind spots. Experience HealthSetu today.
              </p>
            </SectionReveal>
          </div>

          <SectionReveal delay={0.35} yOffset={16}>
            <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
              <button
                onClick={() => onSelectRole('patient')}
                className="bg-[#4A90C4] text-white font-semibold text-xs px-6 py-3 rounded-sm hover:bg-[#3A7DB0] transition-colors flex items-center gap-2 group focus-visible:ring-1 focus-visible:ring-[#4A90C4]"
              >
                <span>Enter Patient Portal</span>
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
              </button>

              <button
                onClick={() => onSelectRole('doctor')}
                className="border border-[#DDD9D1] bg-white text-[#1C2B3A] font-semibold text-xs px-6 py-3 rounded-sm hover:border-[#1C2B3A] hover:bg-[#FAF8F3] transition-colors focus-visible:ring-1 focus-visible:ring-[#1C2B3A]"
              >
                Doctor Clinical Workspace
              </button>

              <button
                onClick={() => onSelectRole('hospital')}
                className="border border-[#DDD9D1] bg-white text-[#1C2B3A] font-semibold text-xs px-6 py-3 rounded-sm hover:border-[#1C2B3A] hover:bg-[#FAF8F3] transition-colors focus-visible:ring-1 focus-visible:ring-[#1C2B3A]"
              >
                Hospital Capacity Network
              </button>
            </div>
          </SectionReveal>

          <SectionReveal delay={0.45} yOffset={12}>
            <div className="text-xs text-[#6B7A8D] flex items-center justify-center gap-2 pt-4 border-t border-[#DDD9D1] max-w-lg mx-auto">
              <ShieldCheck className="w-3.5 h-3.5 text-[#3D8B6E]" />
              <span>Compliant with Indian digital health guidelines · 100% patient consent control</span>
            </div>
          </SectionReveal>

        </div>
      </SectionReveal>
    </section>
  );
};
