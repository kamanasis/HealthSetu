import React, { useState } from 'react';
import { 
  Building2, 
  BedDouble, 
  Activity, 
  Clock, 
  ShieldCheck, 
  CheckCircle2, 
  RefreshCw, 
  Share2, 
  Lock, 
  AlertTriangle,
  HeartPulse
} from 'lucide-react';
import { FreshnessBadge } from '../common/Badge';

export const HospitalPortal: React.FC = () => {
  // Bed Lifecycle inventory state
  const [beds, setBeds] = useState({
    icu: { available: 7, occupied: 31, cleaning: 2, total: 40 },
    emergency: { available: 12, occupied: 11, cleaning: 2, total: 25 },
    general: { available: 45, occupied: 92, cleaning: 8, total: 145 },
  });

  const [lastUpdated, setLastUpdated] = useState<string>('Just now');
  const [networkShared, setNetworkShared] = useState<boolean>(true);
  const [successToast, setSuccessToast] = useState<string | null>(null);

  const triggerToast = (msg: string) => {
    setSuccessToast(msg);
    setTimeout(() => setSuccessToast(null), 3000);
  };

  const handleBedTransition = (category: 'icu' | 'emergency' | 'general', action: 'admit' | 'discharge') => {
    setBeds(prev => {
      const current = prev[category];
      if (action === 'admit' && current.available > 0) {
        return {
          ...prev,
          [category]: {
            ...current,
            available: current.available - 1,
            occupied: current.occupied + 1,
          }
        };
      } else if (action === 'discharge' && current.occupied > 0) {
        return {
          ...prev,
          [category]: {
            ...current,
            occupied: current.occupied - 1,
            available: current.available + 1,
          }
        };
      }
      return prev;
    });

    setLastUpdated('Just now');
    triggerToast(`Bed lifecycle state updated for ${category.toUpperCase()} ward.`);
  };

  return (
    <div className="pt-24 pb-20 max-w-6xl mx-auto px-6 space-y-8 animate-in fade-in duration-300">
      
      {/* Toast Notification */}
      {successToast && (
        <div className="fixed top-20 right-6 z-50 bg-[#1C2B3A] text-white text-xs font-semibold px-4 py-3 rounded-2xl shadow-xl flex items-center gap-2 border border-white/10 animate-in slide-in-from-top-4 duration-200">
          <CheckCircle2 className="w-4 h-4 text-[#3D8B6E]" />
          <span>{successToast}</span>
        </div>
      )}

      {/* Hospital Identity Header */}
      <div className="bg-white rounded-3xl border border-[#DDD9D1] p-6 sm:p-8 shadow-soft flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-[#F5F0FC] border border-[#E9DCF8] flex items-center justify-center text-[#7B5EA7]">
            <Building2 className="w-8 h-8" strokeWidth={1.8} />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="font-serif text-3xl font-bold text-[#1C2B3A]">Apollo Indraprastha Hospital</h1>
              <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-[#F5F0FC] text-[#5B3D8A] border border-[#E9DCF8]">
                NABH Accredited · Org ID: DEL-HOSP-012
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-xs text-[#6B7A8D] mt-1.5">
              <span>Sarita Vihar, Delhi Mathura Road, New Delhi</span>
              <span>·</span>
              <span>Emergency Desk: <strong className="text-[#1C2B3A]">+91 11 2692 5858</strong></span>
              <span>·</span>
              <FreshnessBadge state="current" lastUpdated={lastUpdated} />
            </div>
          </div>
        </div>

        {/* Network Sharing Status Badge */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setNetworkShared(!networkShared);
              triggerToast(networkShared ? 'Capacity data hidden from HealthSetu network' : 'Capacity published to HealthSetu network');
            }}
            className={`flex items-center gap-2 text-xs font-bold px-4 py-2.5 rounded-xl border transition-all ${
              networkShared
                ? 'bg-[#F5F0FC] text-[#5B3D8A] border-[#E9DCF8] hover:bg-[#E9DCF8]'
                : 'bg-[#F0EDE7] text-[#6B7A8D] border-[#DDD9D1]'
            }`}
          >
            <Share2 className="w-3.5 h-3.5" />
            <span>{networkShared ? 'Network Feed: Active' : 'Network Feed: Paused'}</span>
          </button>
        </div>
      </div>

      {/* Bed Inventory Lifecycle Management */}
      <div className="bg-white rounded-3xl border border-[#DDD9D1] p-6 sm:p-8 shadow-soft space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#DDD9D1] pb-4">
          <div>
            <span className="text-[11px] uppercase tracking-wider font-bold text-[#7B5EA7]">Operational Coordination</span>
            <h2 className="font-serif text-2xl font-bold text-[#1C2B3A]">Bed Inventory & Capacity Lifecycle</h2>
            <p className="text-xs text-[#6B7A8D] mt-0.5">
              Lifecycle stages: <span className="font-bold text-[#3D8B6E]">Available</span> → <span className="font-bold text-[#D94F7A]">Occupied</span> → <span className="font-bold text-[#E07B39]">Cleaning / Prep</span> → <span className="font-bold text-[#3D8B6E]">Available</span>
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs text-[#6B7A8D]">
            <Clock className="w-4 h-4 text-[#7B5EA7]" />
            <span>Last published: <strong className="text-[#1C2B3A]">{lastUpdated}</strong></span>
          </div>
        </div>

        {/* 3 Ward Cards */}
        <div className="grid md:grid-cols-3 gap-6">
          
          {/* ICU Ward */}
          <div className="bg-[#FAF8F3]/60 rounded-2xl border border-[#DDD9D1] p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-serif text-lg font-bold text-[#1C2B3A]">Intensive Care (ICU)</h3>
                <span className="text-[11px] text-[#6B7A8D]">Ventilator & Cath Lab Ready</span>
              </div>
              <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-[#EBF5EC] text-[#2D5A40]">
                {beds.icu.available} Available
              </span>
            </div>

            <div className="bg-white rounded-xl p-3 border border-[#DDD9D1] space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-[#6B7A8D]">Available Beds:</span>
                <strong className="text-[#3D8B6E] text-sm">{beds.icu.available}</strong>
              </div>
              <div className="flex justify-between">
                <span className="text-[#6B7A8D]">Occupied Beds:</span>
                <strong className="text-[#1C2B3A]">{beds.icu.occupied}</strong>
              </div>
              <div className="flex justify-between">
                <span className="text-[#6B7A8D]">Cleaning / Sanitizing:</span>
                <strong className="text-[#E07B39]">{beds.icu.cleaning}</strong>
              </div>
              <div className="flex justify-between pt-1 border-t border-[#DDD9D1]/50 font-bold">
                <span>Total Licensed ICU:</span>
                <span>{beds.icu.total}</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-1">
              <button
                onClick={() => handleBedTransition('icu', 'admit')}
                disabled={beds.icu.available <= 0}
                className="text-xs font-bold py-2 rounded-xl bg-white border border-[#DDD9D1] text-[#1C2B3A] hover:bg-[#FAF8F3] disabled:opacity-50 transition-colors"
              >
                + Admit Patient
              </button>
              <button
                onClick={() => handleBedTransition('icu', 'discharge')}
                disabled={beds.icu.occupied <= 0}
                className="text-xs font-bold py-2 rounded-xl bg-[#EBF5EC] text-[#2D5A40] border border-[#D3EAD7] hover:bg-[#D3EAD7] disabled:opacity-50 transition-colors"
              >
                Discharge & Free
              </button>
            </div>
          </div>

          {/* Emergency / Trauma Ward */}
          <div className="bg-[#FAF8F3]/60 rounded-2xl border border-[#DDD9D1] p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-serif text-lg font-bold text-[#1C2B3A]">Emergency / Trauma</h3>
                <span className="text-[11px] text-[#6B7A8D]">Level-1 Triage & Resus</span>
              </div>
              <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-[#FEF3E8] text-[#A05520]">
                {beds.emergency.available} Available
              </span>
            </div>

            <div className="bg-white rounded-xl p-3 border border-[#DDD9D1] space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-[#6B7A8D]">Available Bays:</span>
                <strong className="text-[#3D8B6E] text-sm">{beds.emergency.available}</strong>
              </div>
              <div className="flex justify-between">
                <span className="text-[#6B7A8D]">Occupied Bays:</span>
                <strong className="text-[#1C2B3A]">{beds.emergency.occupied}</strong>
              </div>
              <div className="flex justify-between">
                <span className="text-[#6B7A8D]">Sterilizing:</span>
                <strong className="text-[#E07B39]">{beds.emergency.cleaning}</strong>
              </div>
              <div className="flex justify-between pt-1 border-t border-[#DDD9D1]/50 font-bold">
                <span>Total ER Capacity:</span>
                <span>{beds.emergency.total}</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-1">
              <button
                onClick={() => handleBedTransition('emergency', 'admit')}
                disabled={beds.emergency.available <= 0}
                className="text-xs font-bold py-2 rounded-xl bg-white border border-[#DDD9D1] text-[#1C2B3A] hover:bg-[#FAF8F3] disabled:opacity-50 transition-colors"
              >
                + Admit Patient
              </button>
              <button
                onClick={() => handleBedTransition('emergency', 'discharge')}
                disabled={beds.emergency.occupied <= 0}
                className="text-xs font-bold py-2 rounded-xl bg-[#EBF5EC] text-[#2D5A40] border border-[#D3EAD7] hover:bg-[#D3EAD7] disabled:opacity-50 transition-colors"
              >
                Discharge & Free
              </button>
            </div>
          </div>

          {/* General Inpatient Ward */}
          <div className="bg-[#FAF8F3]/60 rounded-2xl border border-[#DDD9D1] p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-serif text-lg font-bold text-[#1C2B3A]">General Inpatient</h3>
                <span className="text-[11px] text-[#6B7A8D]">Medical & Surgical Wards</span>
              </div>
              <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-[#EBF4FB] text-[#2B5F8A]">
                {beds.general.available} Available
              </span>
            </div>

            <div className="bg-white rounded-xl p-3 border border-[#DDD9D1] space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-[#6B7A8D]">Available Beds:</span>
                <strong className="text-[#3D8B6E] text-sm">{beds.general.available}</strong>
              </div>
              <div className="flex justify-between">
                <span className="text-[#6B7A8D]">Occupied Beds:</span>
                <strong className="text-[#1C2B3A]">{beds.general.occupied}</strong>
              </div>
              <div className="flex justify-between">
                <span className="text-[#6B7A8D]">Cleaning & Preparation:</span>
                <strong className="text-[#E07B39]">{beds.general.cleaning}</strong>
              </div>
              <div className="flex justify-between pt-1 border-t border-[#DDD9D1]/50 font-bold">
                <span>Total General Beds:</span>
                <span>{beds.general.total}</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-1">
              <button
                onClick={() => handleBedTransition('general', 'admit')}
                disabled={beds.general.available <= 0}
                className="text-xs font-bold py-2 rounded-xl bg-white border border-[#DDD9D1] text-[#1C2B3A] hover:bg-[#FAF8F3] disabled:opacity-50 transition-colors"
              >
                + Admit Patient
              </button>
              <button
                onClick={() => handleBedTransition('general', 'discharge')}
                disabled={beds.general.occupied <= 0}
                className="text-xs font-bold py-2 rounded-xl bg-[#EBF5EC] text-[#2D5A40] border border-[#D3EAD7] hover:bg-[#D3EAD7] disabled:opacity-50 transition-colors"
              >
                Discharge & Free
              </button>
            </div>
          </div>

        </div>

      </div>

      {/* Network Sharing Boundary Controls (Private Hospital Data vs Network-Shareable) */}
      <div className="bg-white rounded-3xl border border-[#DDD9D1] p-6 sm:p-8 shadow-soft space-y-5">
        <div className="border-b border-[#DDD9D1] pb-4 flex items-center justify-between">
          <div>
            <span className="text-[11px] uppercase tracking-wider font-bold text-[#7B5EA7]">Data Isolation Architecture</span>
            <h3 className="font-serif text-2xl font-bold text-[#1C2B3A]">Private Hospital Data vs Network-Shareable Data</h3>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-[#2D5A40] bg-[#EBF5EC] px-3 py-1 rounded-full font-bold">
            <ShieldCheck className="w-4 h-4 text-[#3D8B6E]" />
            <span>Zero Patient PII Leaked</span>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          
          {/* Private Internal Data (Guarded) */}
          <div className="bg-[#FAF8F3] border border-[#DDD9D1] rounded-2xl p-5 space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold text-[#1C2B3A]">
              <Lock className="w-4 h-4 text-[#D94F7A]" />
              <span>Private Hospital Records (Internal Only)</span>
            </div>
            <p className="text-xs text-[#6B7A8D] leading-relaxed">
              These records reside inside Apollo’s internal hospital database and are strictly unreachable by outside institutions or network queries:
            </p>
            <ul className="text-xs text-[#6B7A8D] space-y-1 list-disc pl-4">
              <li>Internal Patient Medical Charts & EMR Notes</li>
              <li>Doctor & Nursing Duty Rosters / Personal Phone Numbers</li>
              <li>Billing & Commercial Insurance Records</li>
            </ul>
          </div>

          {/* Network-Shareable Data (Published) */}
          <div className="bg-[#F5F0FC]/60 border border-[#E9DCF8] rounded-2xl p-5 space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold text-[#5B3D8A]">
              <Share2 className="w-4 h-4 text-[#7B5EA7]" />
              <span>Network-Shareable Operational Capacity (Published)</span>
            </div>
            <p className="text-xs text-[#6B7A8D] leading-relaxed">
              Deliberately published metrics broadcast to the HealthSetu Emergency Facility Discovery network:
            </p>
            <ul className="text-xs text-[#6B7A8D] space-y-1 list-disc pl-4">
              <li>Live Available ICU & Emergency Bed Counts</li>
              <li>24x7 Cath Lab & Comprehensive Stroke Center Status</li>
              <li>Freshness Timestamp (<strong className="text-[#3D8B6E]">Updated {lastUpdated}</strong>)</li>
            </ul>
          </div>

        </div>
      </div>

    </div>
  );
};
