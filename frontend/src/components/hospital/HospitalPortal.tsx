import React, { useState } from 'react';
import { 
  Building2, 
  Clock, 
  ShieldCheck, 
  CheckCircle2, 
  Share2, 
  Lock
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
    <div className="pt-24 pb-20 max-w-6xl mx-auto px-6 space-y-6">
      
      {/* Toast Notification */}
      {successToast && (
        <div className="fixed top-20 right-6 z-50 bg-[#1C2B3A] text-white text-xs font-semibold px-4 py-3 rounded-sm border border-[#DDD9D1] flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-[#3D8B6E]" />
          <span>{successToast}</span>
        </div>
      )}

      {/* Hospital Identity Header (Authoritative operational header) */}
      <div className="bg-white rounded-sm border border-[#DDD9D1] p-6 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-sm bg-[#FAF8F3] border border-[#DDD9D1] flex items-center justify-center text-[#7B5EA7]">
            <Building2 className="w-6 h-6" strokeWidth={1.8} />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="font-serif text-2xl text-[#1C2B3A]">Apollo Indraprastha Hospital</h1>
              <span className="text-xs font-mono font-medium px-2 py-0.5 rounded-sm bg-[#FAF8F3] text-[#5B3D8A] border border-[#DDD9D1]">
                DEL-HOSP-012 · NABH Accredited
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-xs text-[#6B7A8D] mt-1">
              <span>Sarita Vihar, Delhi Mathura Road, New Delhi</span>
              <span>·</span>
              <span>Emergency Desk: <strong className="text-[#1C2B3A]">+91 11 2692 5858</strong></span>
              <span>·</span>
              <FreshnessBadge state="current" lastUpdated={lastUpdated} />
            </div>
          </div>
        </div>

        {/* Network Sharing Toggle */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setNetworkShared(!networkShared);
              triggerToast(networkShared ? 'Capacity feed hidden from network' : 'Capacity published to network');
            }}
            className={`flex items-center gap-2 text-xs font-semibold px-3.5 py-2 rounded-sm border transition-colors ${
              networkShared
                ? 'bg-[#FAF8F3] text-[#5B3D8A] border-[#DDD9D1] hover:border-[#5B3D8A]'
                : 'bg-white text-[#6B7A8D] border-[#DDD9D1]'
            }`}
          >
            <Share2 className="w-3.5 h-3.5" />
            <span>{networkShared ? 'Network Feed: Active' : 'Network Feed: Paused'}</span>
          </button>
        </div>
      </div>

      {/* Bed Inventory & Operational Ward Ledger */}
      <div className="bg-white rounded-sm border border-[#DDD9D1] p-6 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#DDD9D1] pb-4">
          <div>
            <span className="text-[10px] uppercase font-mono tracking-wider text-[#7B5EA7]">Operational Coordination</span>
            <h2 className="font-serif text-xl text-[#1C2B3A]">Bed Inventory & Capacity Lifecycle</h2>
            <p className="text-xs text-[#6B7A8D] mt-0.5">
              Lifecycle stages: <span className="font-semibold text-[#3D8B6E]">Available</span> → <span className="font-semibold text-[#D94F7A]">Occupied</span> → <span className="font-semibold text-[#E07B39]">Cleaning & Prep</span> → <span className="font-semibold text-[#3D8B6E]">Available</span>
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs text-[#6B7A8D] font-mono">
            <Clock className="w-3.5 h-3.5 text-[#7B5EA7]" />
            <span>Last broadcast: <strong className="text-[#1C2B3A] font-semibold">{lastUpdated}</strong></span>
          </div>
        </div>

        {/* Ward Capacity Ledger (Structured tabular cards with hairline borders) */}
        <div className="grid md:grid-cols-3 border border-[#DDD9D1] divide-y md:divide-y-0 md:divide-x divide-[#DDD9D1] bg-white rounded-sm">
          
          {/* ICU Ward */}
          <div className="p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-serif text-base text-[#1C2B3A]">Intensive Care (ICU)</h3>
                <span className="text-[11px] text-[#6B7A8D]">Ventilator & Cath Lab Ready</span>
              </div>
              <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded-sm bg-[#EBF5EC] text-[#2D5A40] border border-[#D3EAD7]">
                {beds.icu.available} Available
              </span>
            </div>

            <div className="bg-[#FAF8F3] rounded-sm p-3 border border-[#DDD9D1] space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-[#6B7A8D]">Available Beds:</span>
                <strong className="text-[#3D8B6E] font-semibold">{beds.icu.available}</strong>
              </div>
              <div className="flex justify-between">
                <span className="text-[#6B7A8D]">Occupied Beds:</span>
                <strong className="text-[#1C2B3A] font-semibold">{beds.icu.occupied}</strong>
              </div>
              <div className="flex justify-between">
                <span className="text-[#6B7A8D]">Sanitizing / Prep:</span>
                <strong className="text-[#E07B39] font-semibold">{beds.icu.cleaning}</strong>
              </div>
              <div className="flex justify-between pt-1 border-t border-[#DDD9D1] font-semibold">
                <span>Total Licensed ICU:</span>
                <span>{beds.icu.total}</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-1">
              <button
                onClick={() => handleBedTransition('icu', 'admit')}
                disabled={beds.icu.available <= 0}
                className="text-xs font-semibold py-1.5 rounded-sm bg-white border border-[#DDD9D1] text-[#1C2B3A] hover:bg-[#FAF8F3] disabled:opacity-40 transition-colors"
              >
                + Admit Patient
              </button>
              <button
                onClick={() => handleBedTransition('icu', 'discharge')}
                disabled={beds.icu.occupied <= 0}
                className="text-xs font-semibold py-1.5 rounded-sm bg-[#FAF8F3] text-[#2D5A40] border border-[#DDD9D1] hover:border-[#2D5A40] disabled:opacity-40 transition-colors"
              >
                Discharge Bed
              </button>
            </div>
          </div>

          {/* Emergency / Trauma Ward */}
          <div className="p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-serif text-base text-[#1C2B3A]">Emergency / Trauma</h3>
                <span className="text-[11px] text-[#6B7A8D]">Level-1 Triage & Resus</span>
              </div>
              <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded-sm bg-[#FEF3E8] text-[#A05520] border border-[#FCDDC1]">
                {beds.emergency.available} Available
              </span>
            </div>

            <div className="bg-[#FAF8F3] rounded-sm p-3 border border-[#DDD9D1] space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-[#6B7A8D]">Available Bays:</span>
                <strong className="text-[#3D8B6E] font-semibold">{beds.emergency.available}</strong>
              </div>
              <div className="flex justify-between">
                <span className="text-[#6B7A8D]">Occupied Bays:</span>
                <strong className="text-[#1C2B3A] font-semibold">{beds.emergency.occupied}</strong>
              </div>
              <div className="flex justify-between">
                <span className="text-[#6B7A8D]">Sterilizing:</span>
                <strong className="text-[#E07B39] font-semibold">{beds.emergency.cleaning}</strong>
              </div>
              <div className="flex justify-between pt-1 border-t border-[#DDD9D1] font-semibold">
                <span>Total ER Capacity:</span>
                <span>{beds.emergency.total}</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-1">
              <button
                onClick={() => handleBedTransition('emergency', 'admit')}
                disabled={beds.emergency.available <= 0}
                className="text-xs font-semibold py-1.5 rounded-sm bg-white border border-[#DDD9D1] text-[#1C2B3A] hover:bg-[#FAF8F3] disabled:opacity-40 transition-colors"
              >
                + Admit Patient
              </button>
              <button
                onClick={() => handleBedTransition('emergency', 'discharge')}
                disabled={beds.emergency.occupied <= 0}
                className="text-xs font-semibold py-1.5 rounded-sm bg-[#FAF8F3] text-[#2D5A40] border border-[#DDD9D1] hover:border-[#2D5A40] disabled:opacity-40 transition-colors"
              >
                Discharge Bed
              </button>
            </div>
          </div>

          {/* General Inpatient Ward */}
          <div className="p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-serif text-base text-[#1C2B3A]">General Inpatient</h3>
                <span className="text-[11px] text-[#6B7A8D]">Medical & Surgical Wards</span>
              </div>
              <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded-sm bg-[#FAF8F3] text-[#2B5F8A] border border-[#DDD9D1]">
                {beds.general.available} Available
              </span>
            </div>

            <div className="bg-[#FAF8F3] rounded-sm p-3 border border-[#DDD9D1] space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-[#6B7A8D]">Available Beds:</span>
                <strong className="text-[#3D8B6E] font-semibold">{beds.general.available}</strong>
              </div>
              <div className="flex justify-between">
                <span className="text-[#6B7A8D]">Occupied Beds:</span>
                <strong className="text-[#1C2B3A] font-semibold">{beds.general.occupied}</strong>
              </div>
              <div className="flex justify-between">
                <span className="text-[#6B7A8D]">Cleaning & Prep:</span>
                <strong className="text-[#E07B39] font-semibold">{beds.general.cleaning}</strong>
              </div>
              <div className="flex justify-between pt-1 border-t border-[#DDD9D1] font-semibold">
                <span>Total General Beds:</span>
                <span>{beds.general.total}</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-1">
              <button
                onClick={() => handleBedTransition('general', 'admit')}
                disabled={beds.general.available <= 0}
                className="text-xs font-semibold py-1.5 rounded-sm bg-white border border-[#DDD9D1] text-[#1C2B3A] hover:bg-[#FAF8F3] disabled:opacity-40 transition-colors"
              >
                + Admit Patient
              </button>
              <button
                onClick={() => handleBedTransition('general', 'discharge')}
                disabled={beds.general.occupied <= 0}
                className="text-xs font-semibold py-1.5 rounded-sm bg-[#FAF8F3] text-[#2D5A40] border border-[#DDD9D1] hover:border-[#2D5A40] disabled:opacity-40 transition-colors"
              >
                Discharge Bed
              </button>
            </div>
          </div>

        </div>

      </div>

      {/* Network Sharing Boundary Controls (Private Hospital Data vs Network-Shareable) */}
      <div className="bg-white rounded-sm border border-[#DDD9D1] p-6 space-y-4">
        <div className="border-b border-[#DDD9D1] pb-3 flex items-center justify-between">
          <div>
            <span className="text-[10px] uppercase font-mono tracking-wider text-[#7B5EA7]">Data Isolation Architecture</span>
            <h3 className="font-serif text-lg text-[#1C2B3A]">Private Hospital Data vs Network-Shareable Data</h3>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-[#2D5A40] bg-[#EBF5EC] border border-[#D3EAD7] px-2.5 py-0.5 rounded-sm font-semibold">
            <ShieldCheck className="w-3.5 h-3.5 text-[#3D8B6E]" />
            <span>Zero Patient PII Leaked</span>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          
          {/* Private Internal Data (Guarded) */}
          <div className="bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm p-4 space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#1C2B3A]">
              <Lock className="w-3.5 h-3.5 text-[#D94F7A]" />
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
          <div className="bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm p-4 space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#5B3D8A]">
              <Share2 className="w-3.5 h-3.5 text-[#7B5EA7]" />
              <span>Network-Shareable Operational Capacity (Published)</span>
            </div>
            <p className="text-xs text-[#6B7A8D] leading-relaxed">
              Deliberately published metrics broadcast to the HealthSetu Emergency Facility Discovery network:
            </p>
            <ul className="text-xs text-[#6B7A8D] space-y-1 list-disc pl-4">
              <li>Live Available ICU & Emergency Bed Counts</li>
              <li>24x7 Cath Lab & Comprehensive Stroke Center Readiness</li>
              <li>Freshness Timestamp (<strong className="text-[#3D8B6E]">Updated {lastUpdated}</strong>)</li>
            </ul>
          </div>

        </div>
      </div>

    </div>
  );
};
