import React, { useState, useEffect, useRef } from 'react';
import Lenis from 'lenis';
import 'lenis/dist/lenis.css';
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
import type { Role } from './types';

export function App() {
  const [currentRole, setCurrentRole] = useState<Role>('landing');
  const lenisRef = useRef<Lenis | null>(null);

  // Initialize Lenis smooth momentum scrolling (inspired by MINEGUARD architecture)
  useEffect(() => {
    const lenis = new Lenis({
      duration: 1.2,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      orientation: 'vertical',
      gestureOrientation: 'vertical',
      smoothWheel: true,
      wheelMultiplier: 1.05,
      touchMultiplier: 1.6,
      infinite: false,
    });

    lenisRef.current = lenis;
    (window as unknown as { __lenis: Lenis | null }).__lenis = lenis;

    let rafId: number;
    function raf(time: number) {
      lenis.raf(time);
      rafId = requestAnimationFrame(raf);
    }
    rafId = requestAnimationFrame(raf);

    return () => {
      cancelAnimationFrame(rafId);
      lenis.destroy();
      lenisRef.current = null;
      (window as unknown as { __lenis: Lenis | null }).__lenis = null;
    };
  }, []);

  // Smooth scroll to top on role switch
  useEffect(() => {
    if (lenisRef.current) {
      lenisRef.current.scrollTo(0, { immediate: true });
    } else {
      window.scrollTo(0, 0);
    }
  }, [currentRole]);

  // Smooth gliding anchor navigation with Lenis offset compensation
  const scrollToEmergency = () => {
    if (currentRole !== 'landing') {
      setCurrentRole('landing');
      setTimeout(() => {
        const el = document.getElementById('emergency');
        if (el) {
          if (lenisRef.current) {
            lenisRef.current.scrollTo(el, { offset: -70, duration: 1.2 });
          } else {
            el.scrollIntoView({ behavior: 'smooth' });
          }
        }
      }, 120);
    } else {
      const el = document.getElementById('emergency');
      if (el) {
        if (lenisRef.current) {
          lenisRef.current.scrollTo(el, { offset: -70, duration: 1.2 });
        } else {
          el.scrollIntoView({ behavior: 'smooth' });
        }
      }
    }
  };

  return (
    <div className="min-h-screen bg-[#FAF8F3] text-[#1C2B3A] font-sans antialiased flex flex-col selection:bg-[#4A90C4]/20 selection:text-[#1C2B3A] relative">

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
            <Hero onSelectRole={setCurrentRole} onEmergencyClick={scrollToEmergency} />
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
