import React from 'react';
import { Activity, User, Stethoscope, Building2, PhoneCall } from 'lucide-react';
import type { Role } from '../../types';

interface NavbarProps {
  currentRole: Role;
  setCurrentRole: (role: Role) => void;
  onEmergencyClick?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentRole,
  setCurrentRole,
  onEmergencyClick,
}) => {
  return (
    <header className="fixed top-0 left-0 right-0 h-16 bg-[#FAF8F3] border-b border-[#DDD9D1] z-50">
      <div className="max-w-6xl mx-auto h-full px-4 sm:px-6 flex items-center justify-between">
        
        {/* Brand Logo */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => setCurrentRole('landing')}
            className="flex items-center gap-3 text-left focus-visible:ring-1 focus-visible:ring-[#4A90C4] focus:outline-none py-1"
          >
            <div className="w-8 h-8 rounded-sm bg-[#FFFFFF] border border-[#DDD9D1] flex items-center justify-center text-[#4A90C4]">
              <Activity className="w-4 h-4 text-[#4A90C4]" strokeWidth={2.2} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-serif text-xl text-[#1C2B3A] tracking-tight">HealthSetu</span>
              </div>
              <p className="text-[10px] uppercase font-semibold tracking-wider text-[#6B7A8D] -mt-0.5">
                Continuous Care Platform
              </p>
            </div>
          </button>
        </div>

        {/* Center Links / Role Switcher */}
        <nav className="hidden md:flex items-center bg-[#F0EDE7] p-1 rounded-sm border border-[#DDD9D1]">
          <button
            onClick={() => setCurrentRole('landing')}
            className={`px-3 py-1.5 rounded-sm text-xs font-semibold transition-colors focus-visible:ring-1 focus-visible:ring-[#4A90C4] ${
              currentRole === 'landing'
                ? 'bg-[#FFFFFF] text-[#1C2B3A] border border-[#DDD9D1]'
                : 'text-[#6B7A8D] hover:text-[#1C2B3A]'
            }`}
          >
            Overview
          </button>
          
          <button
            onClick={() => setCurrentRole('patient')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-sm text-xs font-semibold transition-colors focus-visible:ring-1 focus-visible:ring-[#4A90C4] ${
              currentRole === 'patient'
                ? 'bg-[#FFFFFF] text-[#2B5F8A] border border-[#D5E8F8]'
                : 'text-[#6B7A8D] hover:text-[#2B5F8A]'
            }`}
          >
            <User className="w-3.5 h-3.5" strokeWidth={1.8} />
            Patient Portal
          </button>

          <button
            onClick={() => setCurrentRole('doctor')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-sm text-xs font-semibold transition-colors focus-visible:ring-1 focus-visible:ring-[#4A90C4] ${
              currentRole === 'doctor'
                ? 'bg-[#FFFFFF] text-[#2D5A40] border border-[#D3EAD7]'
                : 'text-[#6B7A8D] hover:text-[#2D5A40]'
            }`}
          >
            <Stethoscope className="w-3.5 h-3.5" strokeWidth={1.8} />
            Doctor Clinical
          </button>

          <button
            onClick={() => setCurrentRole('hospital')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-sm text-xs font-semibold transition-colors focus-visible:ring-1 focus-visible:ring-[#4A90C4] ${
              currentRole === 'hospital'
                ? 'bg-[#FFFFFF] text-[#5B3D8A] border border-[#E9DCF8]'
                : 'text-[#6B7A8D] hover:text-[#5B3D8A]'
            }`}
          >
            <Building2 className="w-3.5 h-3.5" strokeWidth={1.8} />
            Hospital Capacity
          </button>
        </nav>

        {/* Action Buttons */}
        <div className="flex items-center gap-2 sm:gap-3">
          <button
            onClick={onEmergencyClick}
            className="flex items-center gap-2 bg-[#E07B39] text-[#FFFFFF] font-semibold text-xs px-3 sm:px-4 py-2 rounded-sm hover:bg-[#C96A28] transition-colors focus-visible:ring-1 focus-visible:ring-[#E07B39]"
          >
            <PhoneCall className="w-3.5 h-3.5" strokeWidth={2} />
            <span className="hidden sm:inline">Emergency Hospital Search</span>
            <span className="sm:hidden">Emergency</span>
          </button>
          
          {currentRole !== 'landing' && (
            <button
              onClick={() => setCurrentRole('landing')}
              className="flex items-center gap-1 text-xs font-semibold text-[#6B7A8D] hover:text-[#1C2B3A] border border-[#DDD9D1] px-2.5 sm:px-3 py-2 rounded-sm bg-[#FFFFFF] hover:bg-[#F0EDE7] transition-colors"
            >
              Exit
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
