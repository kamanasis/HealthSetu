import React, { useState } from 'react';
import { ArrowRight, ShieldCheck, Check, Stethoscope, Sparkles, Clock, UploadCloud, Volume2, Activity } from 'lucide-react';
import { TrustBadge, FreshnessBadge } from '../common/Badge';
import { TextReveal, SectionReveal } from '../common/TextReveal';
import type { Role } from '../../types';

interface HeroProps {
  onSelectRole: (role: Role) => void;
  onEmergencyClick?: () => void;
}

export const Hero: React.FC<HeroProps> = ({ onSelectRole, onEmergencyClick }) => {
  const [accessGranted, setAccessGranted] = useState<boolean>(true);

  const handleEmergencyTrigger = () => {
    if (onEmergencyClick) {
      onEmergencyClick();
    } else {
      const el = document.getElementById('emergency');
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <section className="pt-32 pb-20 px-6 max-w-6xl mx-auto">
      <div className="grid lg:grid-cols-12 gap-8 lg:gap-12 items-start">
        
        {/* Left Column: Copy & Value Proposition */}
        <div className="lg:col-span-7 space-y-6">
          <SectionReveal delay={0}>
            <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-sm bg-[#FFFFFF] border border-[#DDD9D1] text-[#2B5F8A] text-xs font-semibold">
              <ShieldCheck className="w-3.5 h-3.5 text-[#4A90C4]" strokeWidth={2} />
              <span>Consent-Controlled Healthcare Continuity</span>
            </div>
          </SectionReveal>

          <h1 className="font-serif text-4xl sm:text-5xl lg:text-[56px] text-[#1C2B3A] leading-[1.12] tracking-tight font-normal">
            <TextReveal text="Your health," stagger={0.03} yOffset={32} />
            <br />
            <span className="italic text-[#4A90C4]">
              <TextReveal text="always connected." stagger={0.03} yOffset={32} />
            </span>
          </h1>

          <SectionReveal delay={0.3} yOffset={24}>
            <p className="text-base text-[#6B7A8D] max-w-xl font-normal leading-relaxed">
              Bridging patients, doctors, and hospitals into one secure, continuous care platform.
              Patients hold verified records, doctors gain clinical context with deterministic safety checks, and hospitals publish live emergency capacity.
            </p>
          </SectionReveal>

          <SectionReveal delay={0.4} yOffset={24}>
            <div className="pt-2 flex flex-wrap items-center gap-4">
              <button
                onClick={() => onSelectRole('patient')}
                className="bg-[#4A90C4] text-white font-semibold text-xs px-6 py-3 rounded-sm hover:bg-[#3A7DB0] transition-colors flex items-center gap-2 group focus-visible:ring-1 focus-visible:ring-[#4A90C4]"
              >
                <span>Enter Patient Portal</span>
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
              </button>

              <button
                onClick={() => onSelectRole('doctor')}
                className="border border-[#DDD9D1] bg-white text-[#1C2B3A] font-semibold text-xs px-6 py-3 rounded-sm hover:border-[#1C2B3A] hover:bg-[#FAF8F3] transition-colors flex items-center gap-2 focus-visible:ring-1 focus-visible:ring-[#1C2B3A]"
              >
                <Stethoscope className="w-3.5 h-3.5 text-[#3D8B6E]" />
                <span>Doctor Clinical Workspace</span>
              </button>
            </div>
          </SectionReveal>

          {/* Structured Guarantees */}
          <SectionReveal delay={0.5} yOffset={16}>
            <div className="pt-4 border-t border-[#DDD9D1] grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs text-[#6B7A8D]">
              <div className="flex items-start gap-2">
                <Check className="w-3.5 h-3.5 text-[#3D8B6E] mt-0.5 shrink-0" strokeWidth={2.5} />
                <span>Patient-owned consent and revocation</span>
              </div>
              <div className="flex items-start gap-2">
                <Check className="w-3.5 h-3.5 text-[#3D8B6E] mt-0.5 shrink-0" strokeWidth={2.5} />
                <span>Deterministic medication safety matrix</span>
              </div>
              <div className="flex items-start gap-2">
                <Check className="w-3.5 h-3.5 text-[#3D8B6E] mt-0.5 shrink-0" strokeWidth={2.5} />
                <span>Verified live hospital bed readiness</span>
              </div>
            </div>
          </SectionReveal>

          {/* Everyday App Capabilities & Direct Interactive Tools (Replacing abstract jargon with concrete app features) */}
          <SectionReveal delay={0.58} yOffset={16}>
            <div className="bg-white border border-[#DDD9D1] rounded-sm p-4 space-y-3">
              <div className="flex items-center justify-between border-b border-[#DDD9D1] pb-2 text-[11px]">
                <span className="font-mono text-[#1C2B3A] uppercase tracking-wider font-semibold">
                  Everyday Care Tools Inside HealthSetu
                </span>
                <span className="text-[10px] font-mono text-[#2B5F8A] bg-[#EBF4FB] border border-[#D5E8F8] px-2 py-0.5 rounded-sm font-semibold">
                  Live Features
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-[#DDD9D1] gap-3 sm:gap-0 text-xs">
                
                {/* Tool 1 */}
                <div className="sm:pr-3 space-y-1">
                  <div className="flex items-center gap-1.5 font-semibold text-[#1C2B3A]">
                    <UploadCloud className="w-3.5 h-3.5 text-[#4A90C4]" />
                    <span>Prescription Scanner</span>
                  </div>
                  <p className="text-[11px] text-[#6B7A8D] leading-tight">
                    Upload paper slips & verify extracted dosages before saving to your record.
                  </p>
                  <button
                    onClick={() => onSelectRole('patient')}
                    className="text-[11px] font-semibold text-[#4A90C4] hover:underline pt-0.5 block"
                  >
                    Try Scanner →
                  </button>
                </div>

                {/* Tool 2: Medication Safety Engine */}
                <div className="sm:px-3 pt-2 sm:pt-0 space-y-1">
                  <div className="flex items-center gap-1.5 font-semibold text-[#1C2B3A]">
                    <ShieldCheck className="w-3.5 h-3.5 text-[#3D8B6E]" />
                    <span>Medication Safety Engine</span>
                  </div>
                  <p className="text-[11px] text-[#6B7A8D] leading-tight">
                    Real-time checks intercepting drug-drug interactions and documented patient allergies.
                  </p>
                  <button
                    onClick={() => onSelectRole('doctor')}
                    className="text-[11px] font-semibold text-[#3D8B6E] hover:underline pt-0.5 block"
                  >
                    Test Safety Checks →
                  </button>
                </div>

                {/* Tool 3 */}
                <div className="sm:pl-3 pt-2 sm:pt-0 space-y-1">
                  <div className="flex items-center gap-1.5 font-semibold text-[#1C2B3A]">
                    <Activity className="w-3.5 h-3.5 text-[#E07B39]" />
                    <span>Live Emergency Desk</span>
                  </div>
                  <p className="text-[11px] text-[#6B7A8D] leading-tight">
                    Discover nearby hospitals ranked by verified ICU beds and one-tap emergency call.
                  </p>
                  <button
                    onClick={handleEmergencyTrigger}
                    className="text-[11px] font-semibold text-[#E07B39] hover:underline pt-0.5 block"
                  >
                    Check Bed Counts →
                  </button>
                </div>

              </div>

              <div className="pt-2 border-t border-[#DDD9D1] flex flex-wrap items-center justify-between gap-2 text-[11px] text-[#6B7A8D]">
                <span className="flex items-center gap-1.5">
                  <Check className="w-3.5 h-3.5 text-[#3D8B6E]" />
                  <span>Free for patients · Works on mobile and desktop browsers</span>
                </span>
                <span className="font-mono text-[#1C2B3A] font-semibold text-[10px]">Instant Access</span>
              </div>
            </div>
          </SectionReveal>
        </div>

        {/* Right Column: Clean Specimen Architectural Card (Zero bloated shadows, crisp hairlines) */}
        <SectionReveal className="lg:col-span-5" delay={0.3} yOffset={40}>
          <div className="bg-white rounded-sm border border-[#DDD9D1] p-6 space-y-5">
            
            {/* Specimen Header */}
            <div className="flex items-center justify-between border-b border-[#DDD9D1] pb-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-sm bg-[#FAF8F3] border border-[#DDD9D1] flex items-center justify-center text-[#1C2B3A] font-bold text-xs font-mono">
                  RS
                </div>
                <div>
                  <h3 className="font-serif text-lg text-[#1C2B3A]">Rohan Sharma</h3>
                  <div className="flex items-center gap-2 text-xs text-[#6B7A8D]">
                    <span className="font-mono text-[#4A90C4]">HS-PAT-8921</span>
                    <span>·</span>
                    <span>42y Male</span>
                  </div>
                </div>
              </div>
              <TrustBadge state="verified" />
            </div>

            {/* Active Clinical Access Consent Ledger */}
            <div className="bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs font-semibold text-[#1C2B3A]">
                  <Stethoscope className="w-3.5 h-3.5 text-[#3D8B6E]" />
                  <span>Dr. Priya Nair (AIIMS Delhi)</span>
                </div>
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-sm border ${
                  accessGranted ? 'bg-[#EBF5EC] text-[#2D5A40] border-[#D3EAD7]' : 'bg-[#FDEEF4] text-[#D94F7A] border-[#F8D2DF]'
                }`}>
                  {accessGranted ? 'Active Access' : 'Revoked'}
                </span>
              </div>

              <p className="text-xs text-[#6B7A8D] leading-relaxed">
                {accessGranted
                  ? 'Authorized for Full Clinical Record & Prescription History. Expires in 11h 45m.'
                  : 'Access revoked. Consulting doctor cannot view protected patient clinical history.'}
              </p>

              <div className="flex items-center justify-between pt-1 border-t border-[#DDD9D1]">
                <span className="text-[11px] text-[#6B7A8D] flex items-center gap-1">
                  <Clock className="w-3 h-3" /> Auto-expires tonight
                </span>
                <button
                  onClick={() => setAccessGranted(!accessGranted)}
                  className={`text-xs font-semibold px-3 py-1 rounded-sm border transition-colors ${
                    accessGranted
                      ? 'bg-white border-[#DDD9D1] text-[#D94F7A] hover:bg-[#FDEEF4]'
                      : 'bg-[#3D8B6E] border-[#3D8B6E] text-white hover:bg-[#2D5A40]'
                  }`}
                >
                  {accessGranted ? 'Revoke Access' : 'Grant Scoped Access'}
                </button>
              </div>
            </div>

            {/* Structured Longitudinal Record Ledger */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs font-semibold text-[#6B7A8D] px-0.5">
                <span>Active Longitudinal Record</span>
                <button
                  onClick={() => onSelectRole('patient')}
                  className="text-[#4A90C4] hover:underline"
                >
                  View all 3 items →
                </button>
              </div>

              <div className="p-3 rounded-sm border border-[#DDD9D1] bg-white flex items-center justify-between hover:border-[#1C2B3A] transition-colors">
                <div>
                  <div className="text-xs font-semibold text-[#1C2B3A]">Telmisartan 40mg (OD)</div>
                  <div className="text-[11px] text-[#6B7A8D]">Morning with water · Dr. Priya Nair (AIIMS)</div>
                </div>
                <span className="text-[10px] font-semibold text-[#2D5A40] bg-[#EBF5EC] border border-[#D3EAD7] px-2 py-0.5 rounded-sm">
                  Verified
                </span>
              </div>

              <div className="p-3 rounded-sm border border-[#DDD9D1] bg-[#FAF8F3] flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-[#1C2B3A] flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-[#4A90C4]" />
                    AI Clinical History SBAR
                  </div>
                  <div className="text-[11px] text-[#6B7A8D]">Stable BP control across 3 facilities · No allergy conflict</div>
                </div>
                <span className="text-[10px] font-mono font-semibold text-[#2B5F8A] bg-white px-2 py-0.5 rounded-sm border border-[#DDD9D1]">
                  SBAR
                </span>
              </div>
            </div>

            {/* Real-time Hospital Capacity Bar */}
            <div className="border-t border-[#DDD9D1] pt-3 flex items-center justify-between text-xs text-[#6B7A8D]">
              <FreshnessBadge state="current" lastUpdated="3m ago" />
              <span className="text-xs text-[#1C2B3A]">
                Apollo Delhi: <strong className="text-[#3D8B6E] font-semibold">7 ICU Beds Available</strong>
              </span>
            </div>

          </div>
        </SectionReveal>

      </div>
    </section>
  );
};
