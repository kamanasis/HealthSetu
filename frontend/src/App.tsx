import React, { useState } from 'react';
import { Navbar } from './components/common/Navbar';
import { Hero } from './components/landing/Hero';
import { TrustStrip } from './components/landing/TrustStrip';
import { RoleSection } from './components/landing/RoleSection';
import { HowItWorks } from './components/landing/HowItWorks';
import { FeaturesGrid } from './components/landing/FeaturesGrid';
import { EmergencySection } from './components/landing/EmergencySection';
import { CTA } from './components/landing/CTA';
import { Footer } from './components/landing/Footer';
import { PatientPortal } from './components/patient/PatientPortal';
import { DoctorWorkspace } from './components/doctor/DoctorWorkspace';
import { HospitalPortal } from './components/hospital/HospitalPortal';
import { Role } from './types';

export function App() {
  const [currentRole, setCurrentRole] = useState<Role>('landing');

  const scrollToEmergency = () => {
    if (currentRole !== 'landing') {
      setCurrentRole('landing');
      setTimeout(() => {
        const el = document.getElementById('emergency');
        el?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    } else {
      const el = document.getElementById('emergency');
      el?.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="min-h-screen bg-[#FAF8F3] text-[#1C2B3A] font-sans antialiased flex flex-col selection:bg-[#4A90C4]/20 selection:text-[#1C2B3A]">
      
      {/* Global Navigation Bar */}
      <Navbar
        currentRole={currentRole}
        setCurrentRole={setCurrentRole}
        onEmergencyClick={scrollToEmergency}
      />

      {/* Main Content Area */}
      <main className="flex-1">
        {currentRole === 'landing' && (
          <>
            <Hero onSelectRole={setCurrentRole} />
            <TrustStrip />
            <RoleSection onSelectRole={setCurrentRole} />
            <HowItWorks />
            <FeaturesGrid />
            <EmergencySection />
            <CTA onSelectRole={setCurrentRole} />
          </>
        )}

        {currentRole === 'patient' && (
          <PatientPortal onEmergencyClick={scrollToEmergency} />
        )}

        {currentRole === 'doctor' && (
          <DoctorWorkspace />
        )}

        {currentRole === 'hospital' && (
          <HospitalPortal />
        )}
      </main>

      {/* Global Footer */}
      <Footer onSelectRole={setCurrentRole} />

    </div>
  );
}

export default App;
