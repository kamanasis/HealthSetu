import React from 'react';
import { User, Stethoscope, Building2, ArrowRight, ShieldCheck, FileText, CheckCircle2, BedDouble } from 'lucide-react';
import { Role } from '../../types';

interface RoleSectionProps {
  onSelectRole: (role: Role) => void;
}

export const RoleSection: React.FC<RoleSectionProps> = ({ onSelectRole }) => {
  return (
    <section className="bg-white py-20 border-b border-[#DDD9D1]">
      <div className="max-w-6xl mx-auto px-6 space-y-12">
        
        {/* Section Header */}
        <div className="text-center max-w-2xl mx-auto space-y-3">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#FAF8F3] border border-[#DDD9D1] text-[#6B7A8D]">
            Three Connected Stakeholders
          </div>
          <h2 className="font-serif text-3xl sm:text-4xl text-[#1C2B3A]">
            One platform. Three purpose-built experiences.
          </h2>
          <p className="text-[#6B7A8D] text-base leading-relaxed">
            HealthSetu respects the unique responsibilities of patients, clinicians, and hospital administrators while connecting them through a unified continuity layer.
          </p>
        </div>

        {/* Three Role Cards Grid */}
        <div className="grid md:grid-cols-3 gap-6">
          
          {/* Card 1: Patient */}
          <div className="bg-[#FAF8F3]/60 rounded-2xl border border-[#DDD9D1] p-6 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 flex flex-col justify-between group">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="w-12 h-12 rounded-2xl bg-[#EBF4FB] border border-[#D5E8F8] flex items-center justify-center text-[#4A90C4] group-hover:scale-105 transition-transform duration-200">
                  <User className="w-6 h-6" strokeWidth={1.8} />
                </div>
                <span className="text-xs font-bold px-3 py-1 rounded-full bg-[#EBF4FB] text-[#2B5F8A]">
                  Patient Controller
                </span>
              </div>

              <div>
                <h3 className="font-serif text-2xl font-bold text-[#1C2B3A]">Patient Experience</h3>
                <p className="text-xs text-[#6B7A8D] mt-1 leading-relaxed">
                  You own your medical timeline. Upload past prescriptions, verify extracted medications, grant or revoke doctor access, and follow localized care plans.
                </p>
              </div>

              <div className="space-y-2 pt-2 border-t border-[#DDD9D1]/70 text-xs text-[#1C2B3A]">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#4A90C4]" />
                  <span>Unique Patient ID & Health Record</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#4A90C4]" />
                  <span>Prescription Ingestion & Verification</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#4A90C4]" />
                  <span>Time-scoped Consent & 1-Click Revocation</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#4A90C4]" />
                  <span>Audio & Multilingual Care Plan Schedule</span>
                </div>
              </div>
            </div>

            <div className="pt-6">
              <button
                onClick={() => onSelectRole('patient')}
                className="w-full bg-[#4A90C4] text-white font-semibold text-xs py-3 rounded-xl hover:bg-[#3A7DB0] transition-colors duration-200 shadow-sm flex items-center justify-center gap-2"
              >
                <span>Launch Patient Portal</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Card 2: Doctor */}
          <div className="bg-[#FAF8F3]/60 rounded-2xl border border-[#DDD9D1] p-6 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 flex flex-col justify-between group">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="w-12 h-12 rounded-2xl bg-[#EBF5EC] border border-[#D3EAD7] flex items-center justify-center text-[#3D8B6E] group-hover:scale-105 transition-transform duration-200">
                  <Stethoscope className="w-6 h-6" strokeWidth={1.8} />
                </div>
                <span className="text-xs font-bold px-3 py-1 rounded-full bg-[#EBF5EC] text-[#2D5A40]">
                  Clinical Reviewer
                </span>
              </div>

              <div>
                <h3 className="font-serif text-2xl font-bold text-[#1C2B3A]">Doctor Workspace</h3>
                <p className="text-xs text-[#6B7A8D] mt-1 leading-relaxed">
                  Authorized access to longitudinal patient history. Review AI SBAR summaries with evidence links, and prescribe treatment with real-time interaction checks.
                </p>
              </div>

              <div className="space-y-2 pt-2 border-t border-[#DDD9D1]/70 text-xs text-[#1C2B3A]">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#3D8B6E]" />
                  <span>Patient Lookup & Scoped Access Request</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#3D8B6E]" />
                  <span>Evidence-Linked AI SBAR Summaries</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#3D8B6E]" />
                  <span>Real-time Drug-Drug & Allergy Matrix</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#3D8B6E]" />
                  <span>Instant Patient Record & Plan Update</span>
                </div>
              </div>
            </div>

            <div className="pt-6">
              <button
                onClick={() => onSelectRole('doctor')}
                className="w-full bg-[#3D8B6E] text-white font-semibold text-xs py-3 rounded-xl hover:bg-[#2D5A40] transition-colors duration-200 shadow-sm flex items-center justify-center gap-2"
              >
                <span>Launch Doctor Workspace</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Card 3: Hospital */}
          <div className="bg-[#FAF8F3]/60 rounded-2xl border border-[#DDD9D1] p-6 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 flex flex-col justify-between group">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="w-12 h-12 rounded-2xl bg-[#F5F0FC] border border-[#E9DCF8] flex items-center justify-center text-[#7B5EA7] group-hover:scale-105 transition-transform duration-200">
                  <Building2 className="w-6 h-6" strokeWidth={1.8} />
                </div>
                <span className="text-xs font-bold px-3 py-1 rounded-full bg-[#F5F0FC] text-[#5B3D8A]">
                  Operational Facility
                </span>
              </div>

              <div>
                <h3 className="font-serif text-2xl font-bold text-[#1C2B3A]">Hospital Capacity</h3>
                <p className="text-xs text-[#6B7A8D] mt-1 leading-relaxed">
                  Operational capacity sharing without compromising private clinical records. Manage bed lifecycles, emergency availability, and data freshness.
                </p>
              </div>

              <div className="space-y-2 pt-2 border-t border-[#DDD9D1]/70 text-xs text-[#1C2B3A]">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#7B5EA7]" />
                  <span>Bed Lifecycle (Available / Occupied / Prep)</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#7B5EA7]" />
                  <span>ICU, Cath Lab & Emergency Readiness</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#7B5EA7]" />
                  <span>Strict Private vs Network Sharing Isolation</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#7B5EA7]" />
                  <span>Freshness Stamps (Current / Stale / Unknown)</span>
                </div>
              </div>
            </div>

            <div className="pt-6">
              <button
                onClick={() => onSelectRole('hospital')}
                className="w-full bg-[#7B5EA7] text-white font-semibold text-xs py-3 rounded-xl hover:bg-[#5B3D8A] transition-colors duration-200 shadow-sm flex items-center justify-center gap-2"
              >
                <span>Launch Hospital Operations</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

        </div>
      </div>
    </section>
  );
};
