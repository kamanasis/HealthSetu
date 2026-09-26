import React, { useState, useEffect } from 'react';
import { 
  X, 
  User, 
  Stethoscope, 
  Building2, 
  KeyRound, 
  Sparkles, 
  CheckCircle2, 
  Copy, 
  Check, 
  ShieldCheck, 
  ArrowRight,
  Fingerprint
} from 'lucide-react';
import { authStore, generateUniqueId, type UserProfile, DEMO_PROFILES } from '../../services/authStore';
import type { Role } from '../../types';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultRole?: Role;
  onLoginSuccess: (user: UserProfile) => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  defaultRole = 'patient',
  onLoginSuccess,
}) => {
  const [selectedRole, setSelectedRole] = useState<'patient' | 'doctor' | 'hospital'>(
    defaultRole === 'landing' ? 'patient' : defaultRole
  );
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [isSuccess, setIsSuccess] = useState<boolean>(false);
  const [newlyCreatedUser, setNewlyCreatedUser] = useState<UserProfile | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  // Login form state
  const [loginIdentifier, setLoginIdentifier] = useState<string>('');
  const [loginPassword, setLoginPassword] = useState<string>('StrongP@ssw0rd123!');
  const [loginError, setLoginError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Dynamic preview ID for registration
  const [previewId, setPreviewId] = useState<string>('');

  // Registration form fields
  const [regName, setRegName] = useState<string>('');
  const [regEmail, setRegEmail] = useState<string>('');
  const [regPhone, setRegPhone] = useState<string>('');
  const [regPassword, setRegPassword] = useState<string>('StrongP@ssw0rd123!');

  // Patient specific fields
  const [patientAge, setPatientAge] = useState<number>(38);
  const [patientGender, setPatientGender] = useState<string>('Male');
  const [patientBlood, setPatientBlood] = useState<string>('O Positive');
  const [patientCity, setPatientCity] = useState<string>('New Delhi');
  const [patientEmergency, setPatientEmergency] = useState<string>('Sunita Sharma (Spouse) · +91 98104 22911');

  // Doctor specific fields
  const [docDegree, setDocDegree] = useState<string>('MD, MBBS');
  const [docSpecialization, setDocSpecialization] = useState<string>('Cardiologist');
  const [docHospital, setDocHospital] = useState<string>('AIIMS, New Delhi');
  const [docRegNo, setDocRegNo] = useState<string>('MCI-58291');

  // Hospital specific fields
  const [hospType, setHospType] = useState<string>('Super Speciality Hospital');
  const [hospCity, setHospCity] = useState<string>('New Delhi');
  const [hospTotalBeds, setHospTotalBeds] = useState<number>(200);
  const [hospIcuBeds, setHospIcuBeds] = useState<number>(35);
  const [hospHelpline, setHospHelpline] = useState<string>('+91 11 2692 5858');

  // Generate preview unique ID when role or modal opens
  useEffect(() => {
    if (isOpen) {
      setPreviewId(generateUniqueId(selectedRole));
      setIsSuccess(false);
      setNewlyCreatedUser(null);
      setLoginError(null);
    }
  }, [isOpen, selectedRole]);

  // Pause Lenis smooth scroll and lock body when open
  useEffect(() => {
    if (isOpen) {
      const originalOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      const lenis = (window as any).__lenis;
      if (lenis && typeof lenis.stop === 'function') lenis.stop();

      return () => {
        document.body.style.overflow = originalOverflow;
        if (lenis && typeof lenis.start === 'function') lenis.start();
      };
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSelectRole = (r: 'patient' | 'doctor' | 'hospital') => {
    setSelectedRole(r);
    setPreviewId(generateUniqueId(r));
    setLoginError(null);
  };

  const handleDemoFill = () => {
    const demo = DEMO_PROFILES[selectedRole];
    setLoginIdentifier(demo.id);
    setLoginPassword('StrongP@ssw0rd123!');
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const idToUse = loginIdentifier.trim() || DEMO_PROFILES[selectedRole].id;
    setIsLoading(true);
    setLoginError(null);

    try {
      const res = await authStore.login(idToUse, loginPassword, selectedRole);
      setIsLoading(false);
      if (res.user) {
        onLoginSuccess(res.user);
        onClose();
      } else {
        setLoginError(res.error || 'Authentication failed. Please verify credentials.');
      }
    } catch {
      setIsLoading(false);
      setLoginError('Authentication failed.');
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!regName.trim()) {
      setLoginError('Please enter a valid full name or organization name.');
      return;
    }

    setIsLoading(true);
    setLoginError(null);

    try {
      const res = await authStore.register({
        name: regName.trim(),
        role: selectedRole,
        email: regEmail.trim() || `${previewId.toLowerCase()}@healthsetu.org`,
        phone: regPhone.trim(),
        password: regPassword,
        patientDetails: selectedRole === 'patient' ? {
          age: patientAge,
          gender: patientGender,
          bloodGroup: patientBlood,
          city: patientCity,
          emergencyContact: patientEmergency,
        } : undefined,
        doctorDetails: selectedRole === 'doctor' ? {
          degree: docDegree,
          specialization: docSpecialization,
          hospital: docHospital,
          councilReg: docRegNo,
        } : undefined,
        hospitalDetails: selectedRole === 'hospital' ? {
          facilityType: hospType,
          city: hospCity,
          totalBeds: hospTotalBeds,
          icuBeds: hospIcuBeds,
          helpline: hospHelpline,
        } : undefined,
      });

      setIsLoading(false);
      if (res.user) {
        setNewlyCreatedUser(res.user);
        setIsSuccess(true);
      }
    } catch {
      setIsLoading(false);
      setLoginError('Registration failed. Please check the fields and try again.');
    }
  };

  const handleCopyId = () => {
    if (newlyCreatedUser) {
      navigator.clipboard.writeText(newlyCreatedUser.id);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleFinishRegistration = () => {
    if (newlyCreatedUser) {
      onLoginSuccess(newlyCreatedUser);
      onClose();
    }
  };

  return (
    <div 
      data-lenis-prevent="true"
      className="fixed inset-0 z-50 overflow-y-auto bg-[#1C2B3A]/75 flex items-center justify-center p-3 sm:p-5 backdrop-blur-xs"
      style={{ overscrollBehavior: 'contain' }}
      onWheel={(e) => e.stopPropagation()}
      onTouchMove={(e) => e.stopPropagation()}
    >
      <div 
        data-lenis-prevent="true"
        className="relative bg-white rounded-sm border border-[#DDD9D1] max-w-xl w-full flex flex-col max-h-[92vh] shadow-2xl overflow-hidden my-auto"
        style={{ overscrollBehavior: 'contain' }}
        onClick={(e) => e.stopPropagation()}
        onWheel={(e) => e.stopPropagation()}
        onTouchMove={(e) => e.stopPropagation()}
      >
        
        {/* Header */}
        <div className="shrink-0 flex items-center justify-between border-b border-[#DDD9D1] px-5 sm:px-6 py-4 bg-white">
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono uppercase font-semibold text-[#2B5F8A]">
                Unified National Health Identity
              </span>
              <span className="inline-flex items-center gap-1 text-[10px] font-mono bg-[#EBF5EC] text-[#2D5A40] px-1.5 py-0.5 rounded-sm border border-[#D3EAD7]">
                <Fingerprint className="w-3 h-3 text-[#3D8B6E]" />
                Sovereign ID Protocol
              </span>
            </div>
            <h3 className="font-serif text-xl text-[#1C2B3A]">
              HealthSetu Identity & Login
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-sm text-[#6B7A8D] hover:text-[#1C2B3A] hover:bg-[#FAF8F3] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Body */}
        <div 
          data-lenis-prevent="true"
          className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-5 custom-modal-scrollbar"
          style={{ overscrollBehavior: 'contain' }}
          onWheel={(e) => e.stopPropagation()}
          onTouchMove={(e) => e.stopPropagation()}
        >

          {/* Success Screen (New Unique ID Minted) */}
          {isSuccess && newlyCreatedUser ? (
            <div className="space-y-5 py-2 text-center">
              <div className="w-14 h-14 rounded-full bg-[#EBF7F0] border border-[#C3E8D2] flex items-center justify-center mx-auto text-[#227248] animate-bounce">
                <CheckCircle2 className="w-8 h-8" />
              </div>

              <div className="space-y-1">
                <h4 className="font-serif text-2xl text-[#1C2B3A]">
                  Unique HealthSetu ID Issued!
                </h4>
                <p className="text-xs text-[#6B7A8D] max-w-sm mx-auto">
                  Your official profile has been registered in the HealthSetu network. Use your unique ID anytime to sign in.
                </p>
              </div>

              {/* Digital Credential Pass Card */}
              <div className="bg-[#FAF8F3] border-2 border-[#4A90C4] rounded-sm p-5 text-left space-y-4 max-w-md mx-auto shadow-md">
                <div className="flex items-center justify-between border-b border-[#DDD9D1] pb-2.5">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-sm bg-[#1C2B3A] text-white flex items-center justify-center font-bold text-xs">
                      {newlyCreatedUser.avatarInitials}
                    </div>
                    <div>
                      <h5 className="font-serif text-sm font-semibold text-[#1C2B3A]">
                        {newlyCreatedUser.name}
                      </h5>
                      <span className="text-[10px] text-[#6B7A8D] uppercase font-mono tracking-wider">
                        {newlyCreatedUser.role.toUpperCase()} CREDENTIAL
                      </span>
                    </div>
                  </div>
                  <span className="inline-flex items-center gap-1 text-[10px] font-mono bg-[#EBF5EC] text-[#2D5A40] border border-[#D3EAD7] px-2 py-0.5 rounded-sm font-semibold">
                    <ShieldCheck className="w-3 h-3 text-[#3D8B6E]" />
                    Verified Active
                  </span>
                </div>

                <div className="space-y-1 bg-white p-3 rounded-sm border border-[#DDD9D1]">
                  <span className="text-[10px] font-semibold text-[#6B7A8D] uppercase tracking-wider block">
                    Your Sovereign HealthSetu Unique ID:
                  </span>
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xl font-extrabold text-[#2B5F8A] tracking-wider">
                      {newlyCreatedUser.id}
                    </span>
                    <button
                      type="button"
                      onClick={handleCopyId}
                      className="text-xs font-semibold px-2.5 py-1 rounded-sm border border-[#DDD9D1] bg-[#FAF8F3] hover:bg-white text-[#1C2B3A] flex items-center gap-1 transition-all"
                    >
                      {copied ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-[#3D8B6E]" />
                          <span className="text-[#3D8B6E]">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5 text-[#6B7A8D]" />
                          <span>Copy</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-[11px] text-[#6B7A8D] pt-1">
                  <div>
                    <span className="block font-medium">Issue Date:</span>
                    <span className="font-semibold text-[#1C2B3A]">{newlyCreatedUser.issuedAt}</span>
                  </div>
                  <div>
                    <span className="block font-medium">Associated Login:</span>
                    <span className="font-semibold text-[#1C2B3A] truncate block">{newlyCreatedUser.email}</span>
                  </div>
                </div>
              </div>

              <div className="pt-2 flex justify-center">
                <button
                  type="button"
                  onClick={handleFinishRegistration}
                  className="bg-[#3D8B6E] text-white font-semibold text-xs px-6 py-2.5 rounded-sm hover:bg-[#2D5A40] transition-colors flex items-center gap-2 shadow-sm"
                >
                  <span>Proceed to {selectedRole === 'patient' ? 'Patient Portal' : selectedRole === 'doctor' ? 'Doctor Clinical' : 'Hospital Capacity'}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          ) : (
            <>
              {/* Role / Audience Selector (3 Personas) */}
              <div className="space-y-2">
                <label className="text-[11px] font-semibold text-[#6B7A8D] uppercase tracking-wider block">
                  Select Your Portal Role:
                </label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => handleSelectRole('patient')}
                    className={`p-3 rounded-sm border text-left flex flex-col items-start gap-1.5 transition-all ${
                      selectedRole === 'patient'
                        ? 'border-[#2B5F8A] bg-[#FAF8F3] ring-1 ring-[#2B5F8A]'
                        : 'border-[#DDD9D1] bg-white hover:border-[#4A90C4]'
                    }`}
                  >
                    <div className={`w-7 h-7 rounded-sm flex items-center justify-center ${
                      selectedRole === 'patient' ? 'bg-[#2B5F8A] text-white' : 'bg-[#FAF8F3] text-[#2B5F8A]'
                    }`}>
                      <User className="w-4 h-4" />
                    </div>
                    <div>
                      <span className="text-xs font-semibold text-[#1C2B3A] block">Patient</span>
                      <span className="text-[10px] text-[#6B7A8D] font-mono">HS-PAT-xxxx</span>
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleSelectRole('doctor')}
                    className={`p-3 rounded-sm border text-left flex flex-col items-start gap-1.5 transition-all ${
                      selectedRole === 'doctor'
                        ? 'border-[#2D5A40] bg-[#FAF8F3] ring-1 ring-[#2D5A40]'
                        : 'border-[#DDD9D1] bg-white hover:border-[#3D8B6E]'
                    }`}
                  >
                    <div className={`w-7 h-7 rounded-sm flex items-center justify-center ${
                      selectedRole === 'doctor' ? 'bg-[#2D5A40] text-white' : 'bg-[#FAF8F3] text-[#2D5A40]'
                    }`}>
                      <Stethoscope className="w-4 h-4" />
                    </div>
                    <div>
                      <span className="text-xs font-semibold text-[#1C2B3A] block">Doctor</span>
                      <span className="text-[10px] text-[#6B7A8D] font-mono">HS-DOC-xxxx</span>
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleSelectRole('hospital')}
                    className={`p-3 rounded-sm border text-left flex flex-col items-start gap-1.5 transition-all ${
                      selectedRole === 'hospital'
                        ? 'border-[#5B3D8A] bg-[#FAF8F3] ring-1 ring-[#5B3D8A]'
                        : 'border-[#DDD9D1] bg-white hover:border-[#7B5EA7]'
                    }`}
                  >
                    <div className={`w-7 h-7 rounded-sm flex items-center justify-center ${
                      selectedRole === 'hospital' ? 'bg-[#5B3D8A] text-white' : 'bg-[#FAF8F3] text-[#5B3D8A]'
                    }`}>
                      <Building2 className="w-4 h-4" />
                    </div>
                    <div>
                      <span className="text-xs font-semibold text-[#1C2B3A] block">Organization</span>
                      <span className="text-[10px] text-[#6B7A8D] font-mono">HS-HOSP-xxxx</span>
                    </div>
                  </button>
                </div>
              </div>

              {/* Mode Switcher: Log In vs Create Profile */}
              <div className="flex border-b border-[#DDD9D1] text-xs font-semibold">
                <button
                  type="button"
                  onClick={() => setMode('login')}
                  className={`flex-1 py-2 text-center border-b-2 transition-colors ${
                    mode === 'login'
                      ? 'border-[#1C2B3A] text-[#1C2B3A]'
                      : 'border-transparent text-[#6B7A8D] hover:text-[#1C2B3A]'
                  }`}
                >
                  Log In with Unique ID
                </button>
                <button
                  type="button"
                  onClick={() => setMode('register')}
                  className={`flex-1 py-2 text-center border-b-2 transition-colors flex items-center justify-center gap-1.5 ${
                    mode === 'register'
                      ? 'border-[#1C2B3A] text-[#1C2B3A]'
                      : 'border-transparent text-[#6B7A8D] hover:text-[#1C2B3A]'
                  }`}
                >
                  <span>Create Profile & Get Unique ID</span>
                  <span className="w-1.5 h-1.5 rounded-full bg-[#3D8B6E]" />
                </button>
              </div>

              {/* Error Banner */}
              {loginError && (
                <div className="p-2.5 bg-[#FEF3E8] border border-[#FCDDC1] text-[#A05520] text-xs rounded-sm">
                  {loginError}
                </div>
              )}

              {/* Tab 1: Log In */}
              {mode === 'login' && (
                <form onSubmit={handleLoginSubmit} className="space-y-4">
                  {/* Preset Demo Quick Login Button */}
                  <div className="p-2.5 bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm flex items-center justify-between text-xs">
                    <span className="text-[#6B7A8D]">
                      Testing {selectedRole}? Use verified demo credentials:
                    </span>
                    <button
                      type="button"
                      onClick={handleDemoFill}
                      className="text-xs font-semibold text-[#2B5F8A] hover:underline"
                    >
                      Fill {DEMO_PROFILES[selectedRole].id}
                    </button>
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] font-semibold text-[#6B7A8D]">
                      HealthSetu Unique ID / Registered Email
                    </label>
                    <input
                      type="text"
                      value={loginIdentifier}
                      onChange={(e) => setLoginIdentifier(e.target.value)}
                      placeholder={
                        selectedRole === 'patient' 
                          ? 'e.g. HS-PAT-8921 or patient@healthsetu.org'
                          : selectedRole === 'doctor'
                            ? 'e.g. DOC-AIIMS-104 or doctor@healthsetu.org'
                            : 'e.g. HOSP-APOLLO-01 or admin@healthsetu.org'
                      }
                      className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-3 py-2 text-xs font-mono text-[#1C2B3A] focus:border-[#4A90C4] outline-none"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] font-semibold text-[#6B7A8D]">
                      Password
                    </label>
                    <input
                      type="password"
                      value={loginPassword}
                      onChange={(e) => setLoginPassword(e.target.value)}
                      className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-3 py-2 text-xs text-[#1C2B3A] focus:border-[#4A90C4] outline-none"
                    />
                  </div>

                  <div className="pt-2 flex items-center justify-between">
                    <button
                      type="button"
                      onClick={onClose}
                      className="text-xs font-semibold text-[#6B7A8D] hover:text-[#1C2B3A]"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isLoading}
                      className="bg-[#1C2B3A] text-white font-semibold text-xs px-5 py-2 rounded-sm hover:bg-[#2C3B4A] transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50"
                    >
                      <KeyRound className="w-3.5 h-3.5" />
                      <span>{isLoading ? 'Authenticating...' : `Log In to ${selectedRole === 'patient' ? 'Patient Portal' : selectedRole === 'doctor' ? 'Doctor Clinical' : 'Hospital Capacity'}`}</span>
                    </button>
                  </div>
                </form>
              )}

              {/* Tab 2: Create Profile & Mint Unique ID */}
              {mode === 'register' && (
                <form onSubmit={handleRegisterSubmit} className="space-y-4">
                  {/* Live Minting ID Banner */}
                  <div className="bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm p-3 flex items-center justify-between">
                    <div>
                      <span className="text-[10px] font-semibold text-[#6B7A8D] uppercase tracking-wider block">
                        Assigned Sovereign Unique ID:
                      </span>
                      <span className="font-mono text-sm font-bold text-[#2B5F8A]">
                        {previewId}
                      </span>
                    </div>
                    <span className="text-[10px] font-mono text-[#2D5A40] bg-[#EBF5EC] px-2 py-0.5 rounded-sm border border-[#D3EAD7] font-semibold">
                      Auto-Minted for {selectedRole.toUpperCase()}
                    </span>
                  </div>

                  {/* Common Basic Fields */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <label className="text-[11px] font-semibold text-[#6B7A8D]">
                        {selectedRole === 'hospital' ? 'Hospital / Clinic Name' : 'Full Name'} *
                      </label>
                      <input
                        type="text"
                        value={regName}
                        onChange={(e) => setRegName(e.target.value)}
                        placeholder={
                          selectedRole === 'patient' ? 'e.g. Subrata Mondal' : selectedRole === 'doctor' ? 'e.g. Dr. Sanjay Ghoshal' : 'e.g. Joint Care Clinic'
                        }
                        required
                        className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2.5 py-1.5 text-xs text-[#1C2B3A] focus:border-[#4A90C4] outline-none font-medium"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-[11px] font-semibold text-[#6B7A8D]">Email Address</label>
                      <input
                        type="email"
                        value={regEmail}
                        onChange={(e) => setRegEmail(e.target.value)}
                        placeholder="e.g. yourname@example.com"
                        className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2.5 py-1.5 text-xs text-[#1C2B3A] focus:border-[#4A90C4] outline-none"
                      />
                    </div>
                  </div>

                  {/* Patient Specific Fields */}
                  {selectedRole === 'patient' && (
                    <div className="space-y-3 pt-1 border-t border-[#DDD9D1]">
                      <span className="text-[10px] font-semibold text-[#6B7A8D] uppercase tracking-wider block">
                        Patient Health Profile:
                      </span>
                      <div className="grid grid-cols-3 gap-2">
                        <div className="space-y-1">
                          <label className="text-[10px] text-[#6B7A8D]">Age</label>
                          <input
                            type="number"
                            value={patientAge}
                            onChange={(e) => setPatientAge(Number(e.target.value))}
                            className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2 py-1 text-xs"
                          />
                        </div>
                        <div className="space-y-1">
                          <label className="text-[10px] text-[#6B7A8D]">Biological Sex</label>
                          <select
                            value={patientGender}
                            onChange={(e) => setPatientGender(e.target.value)}
                            className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2 py-1 text-xs"
                          >
                            <option value="Male">Male</option>
                            <option value="Female">Female</option>
                            <option value="Other">Other</option>
                          </select>
                        </div>
                        <div className="space-y-1">
                          <label className="text-[10px] text-[#6B7A8D]">Blood Group</label>
                          <input
                            type="text"
                            value={patientBlood}
                            onChange={(e) => setPatientBlood(e.target.value)}
                            className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2 py-1 text-xs"
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-2">
                        <div className="space-y-1">
                          <label className="text-[10px] text-[#6B7A8D]">City / Residence</label>
                          <input
                            type="text"
                            value={patientCity}
                            onChange={(e) => setPatientCity(e.target.value)}
                            className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2 py-1 text-xs"
                          />
                        </div>
                        <div className="space-y-1">
                          <label className="text-[10px] text-[#6B7A8D]">Emergency Contact</label>
                          <input
                            type="text"
                            value={patientEmergency}
                            onChange={(e) => setPatientEmergency(e.target.value)}
                            className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2 py-1 text-xs"
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Doctor Specific Fields */}
                  {selectedRole === 'doctor' && (
                    <div className="space-y-3 pt-1 border-t border-[#DDD9D1]">
                      <span className="text-[10px] font-semibold text-[#6B7A8D] uppercase tracking-wider block">
                        Clinical Credentials:
                      </span>
                      <div className="grid grid-cols-2 gap-2">
                        <div className="space-y-1">
                          <label className="text-[10px] text-[#6B7A8D]">Medical Degree(s)</label>
                          <input
                            type="text"
                            value={docDegree}
                            onChange={(e) => setDocDegree(e.target.value)}
                            placeholder="e.g. MBBS, MS (Orthopaedics)"
                            className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2 py-1 text-xs"
                          />
                        </div>
                        <div className="space-y-1">
                          <label className="text-[10px] text-[#6B7A8D]">Specialization</label>
                          <input
                            type="text"
                            value={docSpecialization}
                            onChange={(e) => setDocSpecialization(e.target.value)}
                            placeholder="e.g. Orthopaedic Surgeon"
                            className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2 py-1 text-xs"
                          />
                        </div>
                        <div className="space-y-1">
                          <label className="text-[10px] text-[#6B7A8D]">Affiliated Hospital / Clinic</label>
                          <input
                            type="text"
                            value={docHospital}
                            onChange={(e) => setDocHospital(e.target.value)}
                            placeholder="e.g. Joint Care Clinic"
                            className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2 py-1 text-xs"
                          />
                        </div>
                        <div className="space-y-1">
                          <label className="text-[10px] text-[#6B7A8D]">Council Reg. Number</label>
                          <input
                            type="text"
                            value={docRegNo}
                            onChange={(e) => setDocRegNo(e.target.value)}
                            placeholder="e.g. MCI-58291"
                            className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2 py-1 text-xs font-mono"
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Hospital Specific Fields */}
                  {selectedRole === 'hospital' && (
                    <div className="space-y-3 pt-1 border-t border-[#DDD9D1]">
                      <span className="text-[10px] font-semibold text-[#6B7A8D] uppercase tracking-wider block">
                        Organization Details:
                      </span>
                      <div className="grid grid-cols-2 gap-2">
                        <div className="space-y-1">
                          <label className="text-[10px] text-[#6B7A8D]">Facility Category</label>
                          <input
                            type="text"
                            value={hospType}
                            onChange={(e) => setHospType(e.target.value)}
                            className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2 py-1 text-xs"
                          />
                        </div>
                        <div className="space-y-1">
                          <label className="text-[10px] text-[#6B7A8D]">City / Jurisdiction</label>
                          <input
                            type="text"
                            value={hospCity}
                            onChange={(e) => setHospCity(e.target.value)}
                            className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2 py-1 text-xs"
                          />
                        </div>
                        <div className="space-y-1">
                          <label className="text-[10px] text-[#6B7A8D]">Total Bed Capacity</label>
                          <input
                            type="number"
                            value={hospTotalBeds}
                            onChange={(e) => setHospTotalBeds(Number(e.target.value))}
                            className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2 py-1 text-xs"
                          />
                        </div>
                        <div className="space-y-1">
                          <label className="text-[10px] text-[#6B7A8D]">24x7 Emergency Helpline</label>
                          <input
                            type="text"
                            value={hospHelpline}
                            onChange={(e) => setHospHelpline(e.target.value)}
                            className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2 py-1 text-xs font-mono"
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="pt-2 flex items-center justify-between border-t border-[#DDD9D1]">
                    <button
                      type="button"
                      onClick={() => setMode('login')}
                      className="text-xs font-semibold text-[#6B7A8D] hover:text-[#1C2B3A]"
                    >
                      Already have an ID? Log In
                    </button>
                    <button
                      type="submit"
                      disabled={isLoading}
                      className="bg-[#3D8B6E] text-white font-semibold text-xs px-5 py-2 rounded-sm hover:bg-[#2D5A40] transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>{isLoading ? 'Minting ID...' : `Create Profile & Issue ${previewId}`}</span>
                    </button>
                  </div>
                </form>
              )}
            </>
          )}

        </div>

      </div>
    </div>
  );
};
