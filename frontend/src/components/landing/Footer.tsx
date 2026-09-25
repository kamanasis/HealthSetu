import React from 'react';
import { Activity, ShieldCheck, Heart } from 'lucide-react';
import { Role } from '../../types';

interface FooterProps {
  onSelectRole: (role: Role) => void;
}

export const Footer: React.FC<FooterProps> = ({ onSelectRole }) => {
  return (
    <footer className="bg-white border-t border-[#DDD9D1] pt-16 pb-12">
      <div className="max-w-6xl mx-auto px-6 space-y-12">
        
        {/* 4-column grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          
          {/* Col 1: Brand & Mission */}
          <div className="space-y-4">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-[#EBF4FB] border border-[#D5E8F8] flex items-center justify-center text-[#4A90C4]">
                <Activity className="w-4 h-4 text-[#4A90C4]" strokeWidth={2} />
              </div>
              <span className="font-serif text-xl font-bold text-[#1C2B3A]">HealthSetu</span>
            </div>
            <p className="text-xs font-semibold text-[#4A90C4]">
              Your health, always connected.
            </p>
            <p className="text-xs text-[#6B7A8D] leading-relaxed">
              Bridging patients, doctors, and hospitals into one secure, continuous care platform.
            </p>
          </div>

          {/* Col 2: Three Stakeholders */}
          <div className="space-y-3">
            <h4 className="text-xs uppercase tracking-wider font-bold text-[#1C2B3A]">Stakeholder Portals</h4>
            <ul className="space-y-2 text-xs text-[#6B7A8D]">
              <li>
                <button
                  onClick={() => onSelectRole('patient')}
                  className="hover:text-[#4A90C4] transition-colors text-left"
                >
                  Patient Longitudinal Record
                </button>
              </li>
              <li>
                <button
                  onClick={() => onSelectRole('doctor')}
                  className="hover:text-[#3D8B6E] transition-colors text-left"
                >
                  Doctor Clinical Workspace
                </button>
              </li>
              <li>
                <button
                  onClick={() => onSelectRole('hospital')}
                  className="hover:text-[#7B5EA7] transition-colors text-left"
                >
                  Hospital Capacity Coordination
                </button>
              </li>
              <li>
                <a href="#emergency" className="hover:text-[#E07B39] transition-colors">
                  Emergency Facility Discovery
                </a>
              </li>
            </ul>
          </div>

          {/* Col 3: Data Trust Architecture */}
          <div className="space-y-3">
            <h4 className="text-xs uppercase tracking-wider font-bold text-[#1C2B3A]">Data Trust Pillars</h4>
            <ul className="space-y-2 text-xs text-[#6B7A8D]">
              <li>Time-Scoped Patient Consent</li>
              <li>Human-in-the-Loop OCR Verification</li>
              <li>Evidence-Linked AI Summaries</li>
              <li>Deterministic Medication Safety</li>
              <li>Live Capacity Freshness Indicators</li>
            </ul>
          </div>

          {/* Col 4: National Integration */}
          <div className="space-y-3">
            <h4 className="text-xs uppercase tracking-wider font-bold text-[#1C2B3A]">Standards & Safety</h4>
            <ul className="space-y-2 text-xs text-[#6B7A8D]">
              <li>Ayushman Bharat Digital Mission (ABDM)</li>
              <li>HL7 FHIR Interoperability Architecture</li>
              <li>RxNorm & OpenFDA Safety Ontologies</li>
              <li>National Emergency Network (Dial 108)</li>
            </ul>
          </div>

        </div>

        {/* Bottom bar */}
        <div className="pt-8 border-t border-[#DDD9D1] flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[#6B7A8D]">
          <p>© {new Date().getFullYear()} HealthSetu. All rights reserved. Designed for healthcare continuity.</p>
          <div className="flex items-center gap-6">
            <span className="flex items-center gap-1.5 text-xs text-[#3D8B6E]">
              <ShieldCheck className="w-4 h-4" />
              <span>Zero Fabricated Data Guarantee</span>
            </span>
          </div>
        </div>

      </div>
    </footer>
  );
};
