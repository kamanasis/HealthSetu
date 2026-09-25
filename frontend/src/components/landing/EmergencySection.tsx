import React, { useState } from 'react';
import { PhoneCall, AlertTriangle, Search, MapPin, ShieldAlert, RotateCcw, Activity } from 'lucide-react';
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
      <div className="space-y-8">
        
        {/* Landscape Top Header & Context Row (Replacing Left/Right split with unified landscape flow) */}
        <div className="grid lg:grid-cols-12 gap-8 items-start">
          
          {/* Header Title & Description (7 Cols) */}
          <div className="lg:col-span-7 space-y-3">
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
              <p className="text-[#6B7A8D] text-sm leading-relaxed max-w-2xl">
                During critical emergencies, generic map apps can direct ambulances to facilities lacking available ICU beds, ready catheterization labs, or specialized trauma teams. HealthSetu validates live capacity before routing.
              </p>
            </SectionReveal>
          </div>

          {/* Quick Hotline & Guarantee Cards (5 Cols, landscape side-by-side) */}
          <div className="lg:col-span-5 grid sm:grid-cols-2 gap-4">
            
            {/* National 108 Card */}
            <SectionReveal delay={0.25} yOffset={16}>
              <div className="p-4 rounded-sm border border-[#DDD9D1] bg-white space-y-3 h-full flex flex-col justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-sm bg-[#FEF3E8] flex items-center justify-center text-[#E07B39] shrink-0">
                    <PhoneCall className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-[#1C2B3A]">Ambulance Dispatch</div>
                    <div className="text-[11px] text-[#6B7A8D]">Central Govt Hotline</div>
                  </div>
                </div>
                <a
                  href="tel:108"
                  className="w-full text-center text-xs font-semibold bg-[#E07B39] text-white py-2 rounded-sm hover:bg-[#C96A28] transition-colors block"
                >
                  Dial 108 Emergency
                </a>
              </div>
            </SectionReveal>

            {/* Strict Freshness Guarantee Card */}
            <SectionReveal delay={0.3} yOffset={16}>
              <div className="p-4 rounded-sm border border-[#DDD9D1] bg-[#FAF8F3] space-y-2 h-full flex flex-col justify-between">
                <div className="flex items-center gap-2 text-xs font-semibold text-[#1C2B3A]">
                  <ShieldAlert className="w-3.5 h-3.5 text-[#E07B39]" />
                  <span>Freshness Guarantee</span>
                </div>
                <p className="text-[11px] text-[#6B7A8D] leading-tight">
                  Confirmed admission requires current capacity timestamps. Outdated feeds are marked <strong className="text-[#A05520]">Stale</strong>.
                </p>
                <div className="text-[10px] font-mono text-[#3D8B6E] font-semibold pt-1 border-t border-[#DDD9D1]">
                  Live Bed Feeds Enforced
                </div>
              </div>
            </SectionReveal>

          </div>

        </div>

        {/* Full-Width Landscape Discovery Console */}
        <SectionReveal delay={0.35} yOffset={30}>
          <div className="bg-white rounded-sm border border-[#DDD9D1] p-6 space-y-6">
            
            {/* Landscape Control Bar: Search + Filter Conditions */}
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[#DDD9D1] pb-5">
              
              {/* Condition Filters */}
              <div className="space-y-1.5">
                <span className="text-[10px] uppercase font-mono tracking-wider text-[#6B7A8D]">
                  Select Clinical Emergency Category
                </span>
                <div className="flex flex-wrap gap-2">
                  {conditions.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => setSelectedCondition(c.id)}
                      className={`text-xs px-3 py-1.5 rounded-sm font-semibold transition-colors border ${
                        selectedCondition === c.id
                          ? 'bg-[#1C2B3A] border-[#1C2B3A] text-white'
                          : 'bg-[#FAF8F3] border-[#DDD9D1] text-[#6B7A8D] hover:text-[#1C2B3A] hover:border-[#1C2B3A]'
                      }`}
                    >
                      <span>{c.label}</span>
                      <span className="text-[10px] opacity-75 font-mono ml-1.5">({c.specialty})</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Search Bar & Result Counter */}
              <div className="flex items-center gap-3 shrink-0">
                <div className="relative">
                  <Search className="w-4 h-4 absolute left-3 top-2.5 text-[#6B7A8D]" />
                  <input
                    type="text"
                    placeholder="Search hospital, city, or specialty..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm pl-9 pr-3 py-1.5 text-xs text-[#1C2B3A] placeholder:text-[#6B7A8D] focus:border-[#4A90C4] outline-none w-full sm:w-64"
                  />
                </div>
                <span className="text-xs font-mono text-[#6B7A8D] hidden sm:inline whitespace-nowrap">
                  {filteredHospitals.length} Facilities Online
                </span>
              </div>

            </div>

            {/* Landscape Facility Cards (Full horizontal row per hospital) */}
            {filteredHospitals.length === 0 ? (
              <div className="py-16 px-6 text-center border border-dashed border-[#DDD9D1] rounded-sm bg-[#FAF8F3] space-y-3">
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
              <div className="space-y-4">
                {filteredHospitals.map((hospital) => (
                  <div
                    key={hospital.id}
                    className="p-5 rounded-sm border border-[#DDD9D1] bg-[#FAF8F3] hover:bg-white hover:border-[#1C2B3A] transition-colors flex flex-col lg:flex-row lg:items-center justify-between gap-6"
                  >
                    
                    {/* Left: Hospital Identity, Location & Specialties */}
                    <div className="space-y-2 lg:max-w-md xl:max-w-lg">
                      <div className="flex flex-wrap items-center gap-2.5">
                        <h4 className="text-base font-semibold text-[#1C2B3A]">{hospital.name}</h4>
                        <FreshnessBadge state={hospital.freshness} lastUpdated={hospital.lastUpdated} />
                      </div>
                      
                      <div className="flex flex-wrap items-center gap-3 text-xs text-[#6B7A8D]">
                        <span className="flex items-center gap-1">
                          <MapPin className="w-3.5 h-3.5 text-[#6B7A8D]" />
                          <span>{hospital.city}</span>
                        </span>
                        <span>·</span>
                        <span className="font-semibold text-[#1C2B3A]">{hospital.distanceKm} km away</span>
                        <span>·</span>
                        <span className="font-mono text-[11px] text-[#4A90C4]">NABH Accredited</span>
                      </div>

                      {/* Specialized Units */}
                      <div className="flex flex-wrap items-center gap-1.5 pt-1">
                        {hospital.specialties.map((spec, i) => (
                          <span
                            key={i}
                            className="text-[10px] font-mono bg-white border border-[#DDD9D1] px-2 py-0.5 rounded-sm text-[#6B7A8D]"
                          >
                            {spec}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Center: Live Bed Metrics (Horizontal landscape strip) */}
                    <div className="grid grid-cols-3 divide-x divide-[#DDD9D1] border border-[#DDD9D1] bg-white rounded-sm text-center shrink-0 w-full sm:w-auto">
                      
                      <div className="p-3 sm:px-4 space-y-0.5">
                        <div className="text-[10px] uppercase font-mono text-[#6B7A8D]">ICU Beds</div>
                        <div className={`text-base font-semibold ${hospital.availableBeds.icu > 0 ? 'text-[#3D8B6E]' : 'text-[#D94F7A]'}`}>
                          {hospital.availableBeds.icu > 0 ? `${hospital.availableBeds.icu} Avail` : 'Full'}
                        </div>
                      </div>

                      <div className="p-3 sm:px-4 space-y-0.5">
                        <div className="text-[10px] uppercase font-mono text-[#6B7A8D]">ER / Trauma</div>
                        <div className="text-base font-semibold text-[#1C2B3A]">
                          {hospital.availableBeds.emergency} Avail
                        </div>
                      </div>

                      <div className="p-3 sm:px-4 space-y-0.5">
                        <div className="text-[10px] uppercase font-mono text-[#6B7A8D]">Status</div>
                        <div className="text-xs font-semibold text-[#3D8B6E] mt-1">
                          {hospital.emergencyStatus}
                        </div>
                      </div>

                    </div>

                    {/* Right: Direct Emergency Call Action */}
                    <div className="flex sm:flex-col items-center sm:items-end justify-between sm:justify-center gap-2 shrink-0 border-t sm:border-t-0 pt-3 sm:pt-0 border-[#DDD9D1]">
                      <a
                        href={`tel:${hospital.phone}`}
                        className="inline-flex items-center justify-center gap-2 text-xs font-semibold bg-[#E07B39] text-white px-5 py-2.5 rounded-sm hover:bg-[#C96A28] transition-colors w-full sm:w-auto"
                      >
                        <PhoneCall className="w-3.5 h-3.5" />
                        <span>Call Emergency Desk</span>
                      </a>
                      <span className="text-[11px] font-mono text-[#6B7A8D]">
                        {hospital.phone}
                      </span>
                    </div>

                  </div>
                ))}
              </div>
            )}

            {/* Bottom Bar: Operational Protocol Guarantee */}
            <div className="pt-4 border-t border-[#DDD9D1] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-[#6B7A8D]">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-[#3D8B6E]" />
                <span>
                  Hospitals transmit encrypted telemetry updates every 15 minutes. Stale records trigger automated network alert flags.
                </span>
              </div>
              <span className="font-mono text-[#1C2B3A] font-semibold text-[11px]">
                Active Network: Delhi NCR
              </span>
            </div>

          </div>
        </SectionReveal>

      </div>
    </section>
  );
};
