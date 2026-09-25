import React, { useState } from 'react';
import { User, Stethoscope, Building2, ArrowRight, Check, ShieldCheck, Lock, BedDouble, AlertTriangle } from 'lucide-react';
import { TextReveal, SectionReveal } from '../common/TextReveal';
import type { Role } from '../../types';

interface RoleSectionProps {
  onSelectRole: (role: Role) => void;
}

export const RoleSection: React.FC<RoleSectionProps> = ({ onSelectRole }) => {
  const [selectedRole, setSelectedRole] = useState<'patient' | 'doctor' | 'hospital'>('patient');

  const roleDetails = {
    patient: {
      tag: '01 / Patient Experience',
      title: 'Full Ownership of Your Health Timeline',
      summary: 'Patients are not passive subjects in HealthSetu. You own your data, ingest paper prescriptions through a human-in-the-loop verification gate, grant time-scoped access to clinicians, and follow an audio-enabled care plan.',
      cta: 'Launch Patient Portal',
      features: [
        'Persistent Patient ID across facilities (ABDM/FHIR aligned)',
        'Physical prescription upload with mandatory patient confirmation',
        'Time-scoped clinical consent with 1-click instant revocation',
        'Daily morning/afternoon/night care schedule with audio playback',
      ],
      preview: {
        header: 'Patient Identity & Consent Console',
        id: 'HS-PAT-8921 · Rohan Sharma',
        metric1: { label: 'Active Meds', value: '3 Verified' },
        metric2: { label: 'Active Consents', value: '1 Doctor' },
        status: 'Consent Enforced',
      }
    },
    doctor: {
      tag: '02 / Doctor Workspace',
      title: 'Clinical Context with Deterministic Safety',
      summary: 'Clinicians receive an immediate, high-fidelity synthesis of longitudinal history rather than a disorganized stack of paper slips. Review AI SBAR summaries backed by clickable citations, and prescribe treatment protected by real-time interaction checks.',
      cta: 'Launch Doctor Workspace',
      features: [
        'Rapid patient lookup with scoped, audited clinical access',
        'Evidence-linked AI SBAR summaries citing original scans',
        'Deterministic drug-drug and allergy interaction warnings',
        'Direct treatment plan updates synchronizing to patient app',
      ],
      preview: {
        header: 'Clinical Encounter & Safety Console',
        id: 'Dr. Priya Nair, MD · AIIMS Delhi',
        metric1: { label: 'Safety Engine', value: 'Deterministic' },
        metric2: { label: 'Allergy Matrix', value: 'Active Guard' },
        status: 'Full Record Access',
      }
    },
    hospital: {
      tag: '03 / Hospital Operations',
      title: 'Operational Capacity Without Data Exposure',
      summary: 'Hospitals share real-time bed and specialized emergency readiness without exposing confidential internal clinical records. Manage bed lifecycles across ICU, ER, and General wards with cryptographic data freshness timestamps.',
      cta: 'Launch Hospital Operations',
      features: [
        'Real-time bed lifecycle tracking (Available / Occupied / Prep)',
        'Emergency readiness broadcast (Cath Lab, Stroke Center, Level-1 Trauma)',
        'Strict isolation between operational capacity and private health records',
        'Freshness-tracked capacity stamps to avoid emergency misdirection',
      ],
      preview: {
        header: 'Hospital Capacity & Resource Feed',
        id: 'Apollo Indraprastha · DEL-HOSP-012',
        metric1: { label: 'ICU Beds', value: '7 Available' },
        metric2: { label: 'Freshness', value: 'Current (3m)' },
        status: 'Live Broadcast Active',
      }
    }
  };

  const active = roleDetails[selectedRole];

  return (
    <section className="bg-white py-20 border-b border-[#DDD9D1]">
      <div className="max-w-6xl mx-auto px-6 space-y-12">
        
        {/* Section Header */}
        <div className="max-w-2xl space-y-3">
          <SectionReveal>
            <span className="text-[11px] uppercase tracking-wider font-semibold text-[#6B7A8D]">
              Three Connected Stakeholders
            </span>
          </SectionReveal>
          <h2 className="font-serif text-3xl sm:text-4xl text-[#1C2B3A] font-normal leading-tight">
            <TextReveal text="One platform. Three purpose-built experiences." stagger={0.02} yOffset={24} />
          </h2>
          <SectionReveal delay={0.2}>
            <p className="text-[#6B7A8D] text-sm sm:text-base leading-relaxed">
              HealthSetu respects the distinct legal responsibilities of patients, clinicians, and hospital administrators while connecting them through a single continuity protocol.
            </p>
          </SectionReveal>
        </div>

        {/* Asymmetric Split Layout: Left Navigation & Manifesto / Right Interactive Specimen */}
        <div className="grid lg:grid-cols-12 gap-8 items-stretch">
          
          {/* Left Column (5 cols): Role Selection Ticker & Core Details */}
          <div className="lg:col-span-5 flex flex-col justify-between space-y-6">
            <div className="space-y-2">
              {[
                { id: 'patient', label: 'Patient Experience', role: 'Data Owner & Controller' },
                { id: 'doctor', label: 'Doctor Workspace', role: 'Clinical Decision Maker' },
                { id: 'hospital', label: 'Hospital Operations', role: 'Capacity & Facility Network' },
              ].map(item => (
                <button
                  key={item.id}
                  onClick={() => setSelectedRole(item.id as any)}
                  className={`w-full text-left p-4 rounded-sm border transition-all flex items-center justify-between ${
                    selectedRole === item.id
                      ? 'bg-[#FAF8F3] border-[#1C2B3A] text-[#1C2B3A]'
                      : 'bg-white border-[#DDD9D1] text-[#6B7A8D] hover:border-[#6B7A8D] hover:text-[#1C2B3A]'
                  }`}
                >
                  <div>
                    <div className="text-xs font-semibold">{item.label}</div>
                    <div className="text-[11px] text-[#6B7A8D]">{item.role}</div>
                  </div>
                  <span className={`text-xs font-mono font-medium ${
                    selectedRole === item.id ? 'text-[#4A90C4]' : 'text-transparent'
                  }`}>
                    →
                  </span>
                </button>
              ))}
            </div>

            <div className="space-y-4 pt-4 border-t border-[#DDD9D1]">
              <span className="font-mono text-[10px] uppercase text-[#6B7A8D]">{active.tag}</span>
              <h3 className="font-serif text-2xl text-[#1C2B3A] font-normal leading-tight">
                {active.title}
              </h3>
              <p className="text-xs text-[#6B7A8D] leading-relaxed">
                {active.summary}
              </p>
            </div>

            <button
              onClick={() => onSelectRole(selectedRole)}
              className="bg-[#4A90C4] text-white font-semibold text-xs py-3 px-6 rounded-sm hover:bg-[#3A7DB0] transition-colors flex items-center justify-center gap-2 group w-full sm:w-auto"
            >
              <span>{active.cta}</span>
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
            </button>
          </div>

          {/* Right Column (7 cols): Direct Operational Specimen View */}
          <div className="lg:col-span-7 bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm p-6 sm:p-8 flex flex-col justify-between space-y-6">
            
            {/* Specimen Header */}
            <div className="border-b border-[#DDD9D1] pb-4 flex items-center justify-between">
              <div>
                <span className="text-[10px] uppercase font-mono tracking-wider text-[#6B7A8D]">Live Environment Preview</span>
                <h4 className="text-sm font-semibold text-[#1C2B3A]">{active.preview.header}</h4>
                <p className="text-xs text-[#6B7A8D] font-mono mt-0.5">{active.preview.id}</p>
              </div>
              <span className="text-[10px] font-mono font-semibold px-2 py-1 rounded-sm bg-white border border-[#DDD9D1] text-[#2B5F8A]">
                {active.preview.status}
              </span>
            </div>

            {/* Specimen Metrics & Architecture Capabilities */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white border border-[#DDD9D1] p-3 rounded-sm">
                <span className="text-[10px] uppercase font-mono text-[#6B7A8D]">{active.preview.metric1.label}</span>
                <div className="text-base font-semibold text-[#1C2B3A] mt-0.5">{active.preview.metric1.value}</div>
              </div>
              <div className="bg-white border border-[#DDD9D1] p-3 rounded-sm">
                <span className="text-[10px] uppercase font-mono text-[#6B7A8D]">{active.preview.metric2.label}</span>
                <div className="text-base font-semibold text-[#3D8B6E] mt-0.5">{active.preview.metric2.value}</div>
              </div>
            </div>

            {/* Structured Feature Checklist */}
            <div className="space-y-3 bg-white border border-[#DDD9D1] p-4 rounded-sm">
              <span className="text-[10px] uppercase tracking-wider font-semibold text-[#6B7A8D]">
                Enforced Guarantees & Workflows
              </span>
              <ul className="space-y-2.5 text-xs text-[#1C2B3A]">
                {active.features.map((feat, idx) => (
                  <li key={idx} className="flex items-start gap-2.5">
                    <Check className="w-3.5 h-3.5 text-[#3D8B6E] mt-0.5 shrink-0" strokeWidth={2.5} />
                    <span className="leading-snug">{feat}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Bottom Proof Note */}
            <div className="border-t border-[#DDD9D1] pt-3 text-[11px] text-[#6B7A8D] flex items-center justify-between">
              <span>Security: ABAC policy enforced</span>
              <span className="text-[#1C2B3A] font-semibold">Zero data lock-in</span>
            </div>

          </div>

        </div>

      </div>
    </section>
  );
};
