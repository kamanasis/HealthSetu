import React, { useState } from 'react';
import { PhoneCall, AlertTriangle, Search, MapPin, ShieldAlert, RotateCcw } from 'lucide-react';
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
      <div className="grid lg:grid-cols-12 gap-8 lg:gap-12 items-start">
        
        {/* Left Column: Context & Critical Rules */}
        <div className="lg:col-span-5 space-y-6">
          <SectionReveal>
            <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-sm bg-[#FEF3E8] border border-[#FCDDC1] text-[#A05520] text-xs font-semibold">
              <AlertTriangle className="w-3.5 h-3.5 text-[#E07B39]" strokeWidth={2} />
              <span>Emergency Facility Discovery</span>
            </div>
          </SectionReveal>

          <h2 className="font-serif text-3xl sm:text-4xl text-[#1C2B3A] font-normal leading-tight">
            <TextReveal text="Find the right hospital with verified emergency capacity" stagger={0.02} yOffset={24} />
          </h2>

          <SectionReveal delay={0.2}>
            <p className="text-[#6B7A8D] text-sm leading-relaxed">
              During critical emergencies, generic map apps can direct ambulances to hospitals lacking ICU beds, on-call interventionalists, or ready surgical suites.
            </p>
          </SectionReveal>

          <div className="bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm p-4 space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#1C2B3A]">
              <ShieldAlert className="w-3.5 h-3.5 text-[#E07B39]" />
              <span>Strict Freshness Guarantee</span>
            </div>
            <p className="text-xs text-[#6B7A8D] leading-relaxed">
              HealthSetu only confirms available admission when a facility transmits sufficiently fresh capacity timestamps. Stale records are explicitly demarcated to avoid misdirection.
            </p>
          </div>

          <div className="p-4 rounded-sm border border-[#DDD9D1] bg-white flex items-center justify-between">
            <div>
              <div className="text-xs font-semibold text-[#1C2B3A]">National Emergency Ambulance</div>
              <div className="text-xs text-[#6B7A8D]">Government Central Dispatch</div>
            </div>
            <a
              href="tel:108"
              className="text-xs font-semibold bg-[#E07B39] text-white px-4 py-2 rounded-sm hover:bg-[#C96A28] transition-colors focus-visible:ring-1 focus-visible:ring-[#E07B39]"
            >
              Dial 108
            </a>
          </div>
        </div>

        {/* Right Column: Hospital Capacity Discovery Interface */}
        <SectionReveal className="lg:col-span-7" delay={0.15} yOffset={40}>
          <div className="bg-white rounded-sm border border-[#DDD9D1] p-6 space-y-6">
            
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#DDD9D1] pb-4">
              <div>
                <span className="text-[10px] uppercase font-mono tracking-wider text-[#6B7A8D]">Live Network Feed</span>
                <h3 className="font-serif text-xl text-[#1C2B3A]">Nearby Participating Hospitals</h3>
              </div>
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-2.5 text-[#6B7A8D]" />
                <input
                  type="text"
                  placeholder="Search hospital or city..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm pl-9 pr-3 py-1.5 text-xs text-[#1C2B3A] placeholder:text-[#6B7A8D] focus:ring-1 focus:ring-[#4A90C4] focus:border-[#4A90C4] outline-none w-full sm:w-52"
                />
              </div>
            </div>

            {/* Condition Selectors (Crisp segmented tabs, no rounded pills) */}
            <div className="flex flex-wrap gap-1.5">
              {conditions.map((c) => (
                <button
                  key={c.id}
                  onClick={() => setSelectedCondition(c.id)}
                  className={`text-xs px-3 py-1.5 rounded-sm font-semibold transition-colors border ${
                    selectedCondition === c.id
                      ? 'bg-[#1C2B3A] border-[#1C2B3A] text-white'
                      : 'bg-[#FAF8F3] border-[#DDD9D1] text-[#6B7A8D] hover:text-[#1C2B3A]'
                  }`}
                >
                  {c.label}
                </button>
              ))}
            </div>

            {/* Results List or Empty State */}
            {filteredHospitals.length === 0 ? (
              <div className="py-12 px-6 text-center border border-dashed border-[#DDD9D1] rounded-sm bg-[#FAF8F3] space-y-3">
                <Search className="w-8 h-8 text-[#6B7A8D] mx-auto" strokeWidth={1.5} />
                <h4 className="text-sm font-semibold text-[#1C2B3A]">No facilities found matching "{searchQuery}"</h4>
                <p className="text-xs text-[#6B7A8D] max-w-sm mx-auto">
                  No participating hospital matched your search terms. Try searching for "Delhi", "Apollo", or "AIIMS".
                </p>
                <button
                  onClick={() => setSearchQuery('')}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#4A90C4] hover:underline pt-1"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Reset hospital search</span>
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {filteredHospitals.map((hospital) => (
                  <div
                    key={hospital.id}
                    className="p-4 rounded-sm border border-[#DDD9D1] bg-[#FAF8F3] hover:bg-white hover:border-[#1C2B3A] transition-colors space-y-3"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="text-sm font-semibold text-[#1C2B3A]">{hospital.name}</h4>
                          <FreshnessBadge state={hospital.freshness} lastUpdated={hospital.lastUpdated} />
                        </div>
                        <div className="flex items-center gap-2 text-xs text-[#6B7A8D] mt-0.5">
                          <MapPin className="w-3.5 h-3.5 text-[#6B7A8D]" />
                          <span>{hospital.city}</span>
                          <span>·</span>
                          <span className="font-medium text-[#1C2B3A]">{hospital.distanceKm} km away</span>
                        </div>
                      </div>

                      <a
                        href={`tel:${hospital.phone}`}
                        className="inline-flex items-center justify-center gap-1.5 text-xs font-semibold bg-[#E07B39] text-white px-3 py-1.5 rounded-sm hover:bg-[#C96A28] transition-colors shrink-0"
                      >
                        <PhoneCall className="w-3.5 h-3.5" />
                        <span>Emergency Desk</span>
                      </a>
                    </div>

                    {/* Bed Status Metrics (Clean hairline dividers) */}
                    <div className="grid grid-cols-3 gap-2 pt-2 border-t border-[#DDD9D1] text-center">
                      <div className="bg-white p-2 rounded-sm border border-[#DDD9D1]">
                        <div className="text-[10px] uppercase font-mono text-[#6B7A8D]">ICU Beds</div>
                        <div className={`text-sm font-semibold ${hospital.availableBeds.icu > 0 ? 'text-[#3D8B6E]' : 'text-[#D94F7A]'}`}>
                          {hospital.availableBeds.icu > 0 ? `${hospital.availableBeds.icu} Avail` : 'Full'}
                        </div>
                      </div>

                      <div className="bg-white p-2 rounded-sm border border-[#DDD9D1]">
                        <div className="text-[10px] uppercase font-mono text-[#6B7A8D]">ER / Trauma</div>
                        <div className="text-sm font-semibold text-[#1C2B3A]">
                          {hospital.availableBeds.emergency} Avail
                        </div>
                      </div>

                      <div className="bg-white p-2 rounded-sm border border-[#DDD9D1]">
                        <div className="text-[10px] uppercase font-mono text-[#6B7A8D]">Status</div>
                        <div className="text-xs font-semibold text-[#3D8B6E] mt-0.5">
                          {hospital.emergencyStatus}
                        </div>
                      </div>
                    </div>

                    {/* Specialties */}
                    <div className="flex flex-wrap items-center gap-1.5 pt-1">
                      {hospital.specialties.map((spec, i) => (
                        <span key={i} className="text-[10px] font-mono bg-white border border-[#DDD9D1] px-2 py-0.5 rounded-sm text-[#6B7A8D]">
                          {spec}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}

          </div>
        </SectionReveal>

      </div>
    </section>
  );
};
