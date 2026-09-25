import React, { useState } from 'react';
import { ArrowRight, ShieldCheck, CheckCircle2, User, Stethoscope, AlertTriangle, Sparkles, Clock, Lock } from 'lucide-react';
import { TrustBadge, FreshnessBadge } from '../common/Badge';
import { TextReveal, SectionReveal } from '../common/TextReveal';
import type { Role } from '../../types';

interface HeroProps {
  onSelectRole: (role: Role) => void;
}

export const Hero: React.FC<HeroProps> = ({ onSelectRole }) => {
  const [accessGranted, setAccessGranted] = useState<boolean>(true);

  return (
    <section className="pt-32 pb-20 px-6 max-w-6xl mx-auto">
      <div className="grid lg:grid-cols-12 gap-12 lg:gap-16 items-center">
        
        {/* Left Column: Copy & Value Proposition */}
        <div className="lg:col-span-7 space-y-6">
          <SectionReveal delay={0}>
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#EBF4FB] border border-[#D5E8F8] text-[#2B5F8A] text-xs font-bold">
              <ShieldCheck className="w-4 h-4 text-[#4A90C4]" strokeWidth={2} />
              <span>Consent-Controlled Healthcare Continuity</span>
            </div>
          </SectionReveal>

          <h1 className="font-serif text-5xl sm:text-6xl lg:text-[62px] text-[#1C2B3A] leading-[1.12] tracking-tight">
            <TextReveal text="Your health," stagger={0.03} yOffset={32} />
            <br />
            <span className="italic font-normal text-[#4A90C4]">
              <TextReveal text="always connected." stagger={0.03} yOffset={32} />
            </span>
          </h1>

          <SectionReveal delay={0.3} yOffset={30}>
            <p className="text-lg text-[#6B7A8D] max-w-xl font-normal leading-relaxed">
              Bridging patients, doctors, and hospitals into one secure, continuous care platform.
              Patients own their longitudinal records, doctors gain clinical clarity, and hospitals coordinate real-time emergency capacity.
            </p>
          </SectionReveal>

          <SectionReveal delay={0.45} yOffset={24}>
            <div className="pt-2 flex flex-wrap items-center gap-4">
              <button
                onClick={() => onSelectRole('patient')}
                className="bg-[#4A90C4] text-white font-semibold text-sm px-6 py-3.5 rounded-xl hover:bg-[#3A7DB0] transition-colors duration-200 shadow-sm flex items-center gap-2 group"
              >
                <span>Enter Patient Portal</span>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
              </button>

              <button
                onClick={() => onSelectRole('doctor')}
                className="border border-[#DDD9D1] bg-white text-[#1C2B3A] font-semibold text-sm px-6 py-3.5 rounded-xl hover:border-[#4A90C4] hover:bg-[#FAF8F3] transition-colors duration-200 flex items-center gap-2"
              >
                <Stethoscope className="w-4 h-4 text-[#3D8B6E]" />
                <span>Doctor Clinical Workspace</span>
              </button>
            </div>
          </SectionReveal>

          {/* Micro-guarantees */}
          <SectionReveal delay={0.55} yOffset={20}>
            <div className="pt-4 flex flex-wrap items-center gap-6 text-xs text-[#6B7A8D]">
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-[#3D8B6E]" />
                <span>Patient-controlled consent</span>
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-[#3D8B6E]" />
                <span>Deterministic medication safety</span>
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-[#3D8B6E]" />
                <span>Verified hospital bed capacity</span>
              </div>
            </div>
          </SectionReveal>
        </div>

        {/* Right Column: Live Interactive Architecture Widget */}
        <SectionReveal className="lg:col-span-5" delay={0.3} yOffset={50}>
          <div className="bg-white rounded-3xl border border-[#DDD9D1] p-6 shadow-soft space-y-5 transition-all duration-300 hover:shadow-md">
            
            {/* Widget Header: Patient Identifier */}
            <div className="flex items-center justify-between border-b border-[#DDD9D1] pb-4">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-2xl bg-[#EBF4FB] border border-[#D5E8F8] flex items-center justify-center text-[#2B5F8A] font-bold text-sm">
                  RS
                </div>
                <div>
                  <h3 className="font-serif text-lg font-bold text-[#1C2B3A]">Rohan Sharma</h3>
                  <div className="flex items-center gap-2 text-xs text-[#6B7A8D]">
                    <span className="font-mono font-semibold text-[#4A90C4]">HS-PAT-8921</span>
                    <span>·</span>
                    <span>42 yrs, Male</span>
                  </div>
                </div>
              </div>
              <TrustBadge state="verified" />
            </div>

            {/* Active Clinical Access Consent Card */}
            <div className="bg-[#FAF8F3] border border-[#DDD9D1] rounded-2xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs font-bold text-[#1C2B3A]">
                  <Stethoscope className="w-4 h-4 text-[#3D8B6E]" />
                  <span>Dr. Priya Nair (AIIMS Delhi)</span>
                </div>
                <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${
                  accessGranted ? 'bg-[#EBF5EC] text-[#2D5A40]' : 'bg-[#FDEEF4] text-[#D94F7A]'
                }`}>
                  {accessGranted ? 'Active Access' : 'Revoked'}
                </span>
              </div>

              <p className="text-xs text-[#6B7A8D] leading-relaxed">
                {accessGranted
                  ? 'Authorized for Full Clinical Record & Prescription History. Expires in 11h 45m.'
                  : 'Access revoked. Doctor cannot view protected patient clinical history.'}
              </p>

              <div className="flex items-center justify-between pt-1">
                <span className="text-[11px] text-[#6B7A8D] flex items-center gap-1">
                  <Clock className="w-3 h-3" /> Auto-expires tonight
                </span>
                <button
                  onClick={() => setAccessGranted(!accessGranted)}
                  className={`text-xs font-bold px-3 py-1.5 rounded-lg transition-colors ${
                    accessGranted
                      ? 'bg-white border border-[#DDD9D1] text-[#D94F7A] hover:bg-[#FDEEF4]'
                      : 'bg-[#3D8B6E] text-white hover:bg-[#2D5A40]'
                  }`}
                >
                  {accessGranted ? 'Revoke Scoped Access' : 'Grant Scoped Access'}
                </button>
              </div>
            </div>

            {/* Longitudinal Health Signal Snippet */}
            <div className="space-y-2.5">
              <div className="flex items-center justify-between text-xs font-bold text-[#6B7A8D]">
                <span>Active Longitudinal Record</span>
                <span className="text-[#4A90C4] hover:underline cursor-pointer" onClick={() => onSelectRole('patient')}>
                  View all 3 items →
                </span>
              </div>

              <div className="p-3 rounded-xl border border-[#DDD9D1] bg-white flex items-center justify-between">
                <div>
                  <div className="text-xs font-bold text-[#1C2B3A]">Telmisartan 40mg (OD)</div>
                  <div className="text-[11px] text-[#6B7A8D]">Morning with water · Dr. Priya Nair (AIIMS)</div>
                </div>
                <span className="text-[11px] font-bold text-[#3D8B6E] bg-[#EBF5EC] px-2 py-0.5 rounded-full">
                  Verified
                </span>
              </div>

              <div className="p-3 rounded-xl border border-[#D5E8F8] bg-[#EBF4FB]/60 flex items-center justify-between">
                <div>
                  <div className="text-xs font-bold text-[#1C2B3A] flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-[#4A90C4]" />
                    AI Longitudinal History Summary
                  </div>
                  <div className="text-[11px] text-[#6B7A8D]">Stable BP control across 3 facilities · No allergy conflict</div>
                </div>
                <span className="text-[10px] font-bold text-[#2B5F8A] bg-white/80 px-2 py-0.5 rounded-full border border-[#D5E8F8]">
                  SBAR
                </span>
              </div>
            </div>

            {/* Real-time Hospital Capacity Pulse */}
            <div className="border-t border-[#DDD9D1] pt-3 flex items-center justify-between text-xs text-[#6B7A8D]">
              <div className="flex items-center gap-1.5">
                <FreshnessBadge state="current" lastUpdated="3m ago" />
              </div>
              <span className="font-semibold text-[#1C2B3A]">
                Apollo Delhi: <span className="text-[#3D8B6E]">7 ICU Beds</span>
              </span>
            </div>

          </div>
        </SectionReveal>

      </div>
    </section>
  );
};
