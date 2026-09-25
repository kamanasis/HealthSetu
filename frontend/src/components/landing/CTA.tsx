import React from 'react';
import { ArrowRight, ShieldCheck, HeartHandshake } from 'lucide-react';
import { Role } from '../../types';

interface CTAProps {
  onSelectRole: (role: Role) => void;
}

export const CTA: React.FC<CTAProps> = ({ onSelectRole }) => {
  return (
    <section className="py-24 max-w-6xl mx-auto px-6">
      <div className="bg-gradient-to-br from-[#EBF4FB] via-[#FAF8F3] to-[#EBF5EC] border border-[#DDD9D1] rounded-3xl p-10 md:p-16 text-center space-y-8 shadow-sm">
        
        <div className="w-14 h-14 rounded-2xl bg-white border border-[#D5E8F8] flex items-center justify-center mx-auto text-[#4A90C4] shadow-sm">
          <HeartHandshake className="w-7 h-7" strokeWidth={1.8} />
        </div>

        <div className="max-w-2xl mx-auto space-y-3">
          <h2 className="font-serif text-3xl sm:text-5xl text-[#1C2B3A] tracking-tight">
            Healthcare works better when information is connected
          </h2>
          <p className="text-base text-[#6B7A8D] leading-relaxed">
            Eliminate fragmented prescriptions, repeated tests, and emergency blind spots. Experience HealthSetu today.
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
          <button
            onClick={() => onSelectRole('patient')}
            className="bg-[#4A90C4] text-white font-semibold text-sm px-7 py-3.5 rounded-xl hover:bg-[#3A7DB0] transition-colors duration-200 shadow-sm flex items-center gap-2 group"
          >
            <span>Create Patient Account</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
          </button>

          <button
            onClick={() => onSelectRole('doctor')}
            className="border border-[#DDD9D1] bg-white text-[#1C2B3A] font-semibold text-sm px-7 py-3.5 rounded-xl hover:border-[#4A90C4] hover:bg-[#FAF8F3] transition-colors duration-200"
          >
            Doctor Portal Access
          </button>

          <button
            onClick={() => onSelectRole('hospital')}
            className="border border-[#DDD9D1] bg-white text-[#1C2B3A] font-semibold text-sm px-7 py-3.5 rounded-xl hover:border-[#7B5EA7] hover:bg-[#FAF8F3] transition-colors duration-200"
          >
            Hospital Capacity Network
          </button>
        </div>

        <div className="text-xs text-[#6B7A8D] flex items-center justify-center gap-2 pt-2">
          <ShieldCheck className="w-4 h-4 text-[#3D8B6E]" />
          <span>Compliant with Indian digital health guidelines · Patient retains 100% consent control</span>
        </div>

      </div>
    </section>
  );
};
