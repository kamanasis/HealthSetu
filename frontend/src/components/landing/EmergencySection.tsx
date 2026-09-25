import React, { useState } from 'react';
import { PhoneCall, AlertTriangle, Search, MapPin, BedDouble, Activity, ShieldAlert, Clock } from 'lucide-react';
import { INITIAL_HOSPITALS } from '../../data/mockData';
import { FreshnessBadge } from '../common/Badge';
import { TextReveal, SectionReveal } from '../common/TextReveal';

export const EmergencySection: React.FC = () => {
  const [selectedCondition, setSelectedCondition] = useState<string>('Cardiac');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const conditions = [
    { id: 'Cardiac', label: 'Acute Chest Pain / Cardiac', specialty: '24x7 Cath Lab' },
    { id: 'Stroke', label: 'Stroke / Facial Droop / Slurred Speech', specialty: 'Comprehensive Stroke Center' },
    { id: 'Trauma', label: 'Trauma / Accident Injury', specialty: 'Level-1 Trauma' },
    { id: 'Pediatric', label: 'Pediatric Emergency', specialty: 'Pediatric ICU' },
  ];

  const filteredHospitals = INITIAL_HOSPITALS.filter(h => {
    const matchesSearch = h.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          h.city.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSearch;
  });

  return (
    <section id="emergency" className="py-20 max-w-6xl mx-auto px-6 border-b border-[#DDD9D1]">
      <div className="grid lg:grid-cols-12 gap-12 lg:gap-16 items-start">
        
        {/* Left Column: Context & Critical Rules */}
        <div className="lg:col-span-5 space-y-6">
          <SectionReveal>
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#FEF3E8] border border-[#FCDDC1] text-[#A05520] text-xs font-bold">
              <AlertTriangle className="w-4 h-4 text-[#E07B39]" strokeWidth={2} />
              <span>Emergency Facility Discovery</span>
            </div>
          </SectionReveal>

          <h2 className="font-serif text-3xl sm:text-4xl text-[#1C2B3A] leading-tight">
            <TextReveal text="Find the right hospital with verified emergency capacity" stagger={0.02} yOffset={24} />
          </h2>

          <SectionReveal delay={0.2}>
            <p className="text-[#6B7A8D] text-sm leading-relaxed">
              During critical medical emergencies, searching generic maps can lead to facilities without specialized care, ICU beds, or functioning catheterization labs.
            </p>
          </SectionReveal>

          <div className="bg-[#FEF3E8]/60 border border-[#FCDDC1] rounded-2xl p-4 space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold text-[#A05520]">
              <ShieldAlert className="w-4 h-4 text-[#E07B39]" />
              <span>Strict Freshness Guarantee</span>
            </div>
            <p className="text-xs text-[#A05520]/90 leading-relaxed">
              HealthSetu does not promise admission unless the hospital has transmitted sufficiently current capacity records. Outdated records are flagged as <span className="font-bold underline">Stale</span> or <span className="font-bold underline">Unknown</span>.
            </p>
          </div>

          <div className="p-4 rounded-2xl border border-[#DDD9D1] bg-white flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#FEF3E8] flex items-center justify-center text-[#E07B39]">
                <PhoneCall className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs font-bold text-[#1C2B3A]">National Emergency Ambulance</div>
                <div className="text-xs text-[#6B7A8D]">Instant emergency dispatch</div>
              </div>
            </div>
            <a
              href="tel:108"
              className="text-xs font-bold bg-[#E07B39] text-white px-3.5 py-2 rounded-xl hover:bg-[#C96A28] transition-colors"
            >
              Dial 108
            </a>
          </div>
        </div>

        {/* Right Column: Hospital Capacity Discovery Interface */}
        <SectionReveal className="lg:col-span-7" delay={0.15} yOffset={50}>
        <div className="bg-white rounded-3xl border border-[#DDD9D1] p-6 shadow-soft space-y-5">
          
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <span className="text-[11px] uppercase tracking-wider font-bold text-[#6B7A8D]">Live Network Feed</span>
              <h3 className="font-serif text-xl font-bold text-[#1C2B3A]">Nearby Participating Hospitals</h3>
            </div>
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-3 text-[#6B7A8D]" />
              <input
                type="text"
                placeholder="Search hospital or area..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-[#F0EDE7] rounded-xl pl-9 pr-3 py-2 text-xs text-[#1C2B3A] placeholder:text-[#6B7A8D] focus:ring-1 focus:ring-[#4A90C4] outline-none w-full sm:w-48"
              />
            </div>
          </div>

          {/* Condition Selectors */}
          <div className="flex flex-wrap gap-2 pt-1">
            {conditions.map((c) => (
              <button
                key={c.id}
                onClick={() => setSelectedCondition(c.id)}
                className={`text-xs px-3 py-1.5 rounded-xl font-semibold transition-all ${
                  selectedCondition === c.id
                    ? 'bg-[#E07B39] text-white shadow-sm'
                    : 'bg-[#F0EDE7] text-[#6B7A8D] hover:text-[#1C2B3A]'
                }`}
              >
                {c.label}
              </button>
            ))}
          </div>

          {/* Results List */}
          <div className="space-y-3 pt-2">
            {filteredHospitals.map((hospital) => (
              <div
                key={hospital.id}
                className="p-4 rounded-2xl border border-[#DDD9D1] bg-[#FAF8F3]/60 hover:bg-white hover:shadow-sm transition-all space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-bold text-[#1C2B3A]">{hospital.name}</h4>
                      <FreshnessBadge state={hospital.freshness} lastUpdated={hospital.lastUpdated} />
                    </div>
                    <div className="flex items-center gap-2 text-xs text-[#6B7A8D] mt-0.5">
                      <MapPin className="w-3.5 h-3.5 text-[#6B7A8D]" />
                      <span>{hospital.city}</span>
                      <span>·</span>
                      <span className="font-semibold text-[#1C2B3A]">{hospital.distanceKm} km away</span>
                    </div>
                  </div>

                  <a
                    href={`tel:${hospital.phone}`}
                    className="inline-flex items-center justify-center gap-1.5 text-xs font-bold bg-[#E07B39] text-white px-3.5 py-2 rounded-xl hover:bg-[#C96A28] transition-colors shrink-0"
                  >
                    <PhoneCall className="w-3.5 h-3.5" />
                    <span>Emergency Desk</span>
                  </a>
                </div>

                {/* Bed Status metrics */}
                <div className="grid grid-cols-3 gap-2 pt-2 border-t border-[#DDD9D1]/70 text-center">
                  <div className="bg-white p-2 rounded-xl border border-[#DDD9D1]">
                    <div className="text-[10px] uppercase font-bold text-[#6B7A8D]">ICU Beds</div>
                    <div className={`text-base font-bold ${hospital.availableBeds.icu > 0 ? 'text-[#3D8B6E]' : 'text-[#D94F7A]'}`}>
                      {hospital.availableBeds.icu > 0 ? `${hospital.availableBeds.icu} Avail` : 'Full'}
                    </div>
                  </div>

                  <div className="bg-white p-2 rounded-xl border border-[#DDD9D1]">
                    <div className="text-[10px] uppercase font-bold text-[#6B7A8D]">ER / Trauma</div>
                    <div className="text-base font-bold text-[#1C2B3A]">
                      {hospital.availableBeds.emergency} Avail
                    </div>
                  </div>

                  <div className="bg-white p-2 rounded-xl border border-[#DDD9D1]">
                    <div className="text-[10px] uppercase font-bold text-[#6B7A8D]">Status</div>
                    <div className="text-xs font-bold text-[#3D8B6E] mt-1">
                      {hospital.emergencyStatus}
                    </div>
                  </div>
                </div>

                {/* Specialties Tagline */}
                <div className="flex flex-wrap items-center gap-1.5 pt-1">
                  {hospital.specialties.map((spec, i) => (
                    <span key={i} className="text-[10px] font-semibold bg-white border border-[#DDD9D1] px-2 py-0.5 rounded-lg text-[#6B7A8D]">
                      {spec}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>

        </div>
        </SectionReveal>

      </div>
    </section>
  );
};
