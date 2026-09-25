import React from 'react';
import { 
  FileText, 
  ScanLine, 
  ShieldCheck, 
  AlertTriangle, 
  Sparkles, 
  CalendarClock, 
  Volume2, 
  Building2, 
  Activity 
} from 'lucide-react';
import { TextReveal, SectionReveal } from '../common/TextReveal';

export const FeaturesGrid: React.FC = () => {
  const features = [
    {
      icon: <FileText className="w-5 h-5 text-[#4A90C4]" strokeWidth={1.8} />,
      title: 'Longitudinal Health Record',
      description: 'Preserves your complete healthcare story across clinics, diagnostics, and hospitals in one patient-owned timeline.',
      tag: 'Core Continuity',
      tagColor: 'bg-[#EBF4FB] text-[#2B5F8A]',
    },
    {
      icon: <ScanLine className="w-5 h-5 text-[#4A90C4]" strokeWidth={1.8} />,
      title: 'Prescription Intelligence',
      description: 'Ingests physical prescriptions with OCR and multimodal vision, followed by mandatory patient verification before saving.',
      tag: 'Intelligent Ingestion',
      tagColor: 'bg-[#EBF4FB] text-[#2B5F8A]',
    },
    {
      icon: <ShieldCheck className="w-5 h-5 text-[#3D8B6E]" strokeWidth={1.8} />,
      title: 'Consent-Controlled Access',
      description: 'Doctors must request permission. Patients view active sessions with full audit trails and instant 1-click access revocation.',
      tag: 'Patient Sovereignty',
      tagColor: 'bg-[#EBF5EC] text-[#2D5A40]',
    },
    {
      icon: <AlertTriangle className="w-5 h-5 text-[#E07B39]" strokeWidth={1.8} />,
      title: 'Medication Safety Engine',
      description: 'Deterministic checks for drug-drug interactions, duplicate therapies, allergy conflicts, and food-drug contraindications.',
      tag: 'Clinical Safety',
      tagColor: 'bg-[#FEF3E8] text-[#A05520]',
    },
    {
      icon: <Sparkles className="w-5 h-5 text-[#7B5EA7]" strokeWidth={1.8} />,
      title: 'Evidence-Linked AI SBAR',
      description: 'Surfaces recurring symptoms, medication changes, and historical patterns with clickable links to underlying clinical sources.',
      tag: 'Decision Support',
      tagColor: 'bg-[#F5F0FC] text-[#5B3D8A]',
    },
    {
      icon: <CalendarClock className="w-5 h-5 text-[#4A90C4]" strokeWidth={1.8} />,
      title: 'Actionable Care Plans',
      description: 'Translates complex post-visit instructions into clear morning, afternoon, evening, and bedtime tasks with meal cues.',
      tag: 'Patient Adherence',
      tagColor: 'bg-[#EBF4FB] text-[#2B5F8A]',
    },
    {
      icon: <Volume2 className="w-5 h-5 text-[#3D8B6E]" strokeWidth={1.8} />,
      title: 'Multilingual & Audio Guidance',
      description: 'Supports localized terminology and speech synthesis while rigorously preserving drug names, dosages, and critical metrics.',
      tag: 'Accessibility',
      tagColor: 'bg-[#EBF5EC] text-[#2D5A40]',
    },
    {
      icon: <Activity className="w-5 h-5 text-[#E07B39]" strokeWidth={1.8} />,
      title: 'Emergency Facility Discovery',
      description: 'Identifies nearby hospitals matching your emergency condition with verified ICU beds, stroke units, and cath lab readiness.',
      tag: 'Emergency Routing',
      tagColor: 'bg-[#FEF3E8] text-[#A05520]',
    },
    {
      icon: <Building2 className="w-5 h-5 text-[#7B5EA7]" strokeWidth={1.8} />,
      title: 'Hospital Capacity Network',
      description: 'Enables healthcare organizations to publish operational bed and service availability without exposing internal private records.',
      tag: 'Interoperability',
      tagColor: 'bg-[#F5F0FC] text-[#5B3D8A]',
    },
  ];

  return (
    <section className="bg-white py-20 border-b border-[#DDD9D1]">
      <div className="max-w-6xl mx-auto px-6 space-y-12">
        
        <div className="text-center max-w-2xl mx-auto space-y-3">
          <SectionReveal>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#FAF8F3] border border-[#DDD9D1] text-[#6B7A8D]">
              Comprehensive Capabilities
            </span>
          </SectionReveal>
          <h2 className="font-serif text-3xl sm:text-4xl text-[#1C2B3A]">
            <TextReveal text="Designed for safety, trust, and continuity" stagger={0.02} yOffset={24} />
          </h2>
          <SectionReveal delay={0.2}>
            <p className="text-[#6B7A8D] text-base leading-relaxed">
              Every feature works within HealthSetu's overarching trust architecture: data provenance is maintained, clinicians remain the deciders, and patients remain in control.
            </p>
          </SectionReveal>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map((feature, idx) => (
            <SectionReveal key={idx} delay={(idx % 3) * 0.1} yOffset={40}>
              <div
                className="bg-white rounded-2xl border border-[#DDD9D1] p-6 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 flex flex-col justify-between group h-full"
              >
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="w-10 h-10 rounded-xl bg-[#FAF8F3] border border-[#DDD9D1] flex items-center justify-center group-hover:scale-110 transition-transform duration-200">
                      {feature.icon}
                    </div>
                    <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${feature.tagColor}`}>
                      {feature.tag}
                    </span>
                  </div>

                  <div>
                    <h3 className="font-serif text-xl font-bold text-[#1C2B3A]">{feature.title}</h3>
                    <p className="text-xs text-[#6B7A8D] mt-1.5 leading-relaxed">
                      {feature.description}
                    </p>
                  </div>
                </div>
              </div>
            </SectionReveal>
          ))}
        </div>

      </div>
    </section>
  );
};
