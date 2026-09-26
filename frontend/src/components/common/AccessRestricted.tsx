import React from 'react';
import { ShieldAlert, Lock, ArrowLeft, ArrowRight, KeyRound, User, Stethoscope, Building2 } from 'lucide-react';
import type { Role } from '../../types';
import type { UserProfile } from '../../services/authStore';

interface AccessRestrictedProps {
  attemptedRole: Role;
  currentUser: UserProfile | null;
  onNavigateHome: () => void;
  onNavigateAllowedPortal: (role: Role) => void;
  onOpenAuth: (preferredRole: Role) => void;
}

export const AccessRestricted: React.FC<AccessRestrictedProps> = ({
  attemptedRole,
  currentUser,
  onNavigateHome,
  onNavigateAllowedPortal,
  onOpenAuth,
}) => {
  const getRoleTitle = (r: Role) => {
    switch (r) {
      case 'patient':
        return 'Patient Health Vault';
      case 'doctor':
        return 'Doctor Clinical Workspace';
      case 'hospital':
        return 'Hospital Capacity Management';
      default:
        return 'Protected Portal';
    }
  };

  const getRequiredRole = (r: Role) => {
    switch (r) {
      case 'patient':
        return 'Patient (HS-PAT)';
      case 'doctor':
        return 'Verified Clinician / Doctor (HS-DOC / DOC)';
      case 'hospital':
        return 'Hospital Administration (HS-HOSP / HOSP)';
      default:
        return 'Authorized Role';
    }
  };

  const getRoleIcon = (r: Role) => {
    switch (r) {
      case 'patient':
        return <User className="w-5 h-5 text-[#2B5F8A]" />;
      case 'doctor':
        return <Stethoscope className="w-5 h-5 text-[#2D5A40]" />;
      case 'hospital':
        return <Building2 className="w-5 h-5 text-[#5B3D8A]" />;
      default:
        return <Lock className="w-5 h-5 text-[#6B7A8D]" />;
    }
  };

  const isUnauthenticated = !currentUser;

  return (
    <div className="pt-32 pb-24 max-w-2xl mx-auto px-6">
      <div className="bg-white rounded-sm border border-[#DDD9D1] p-8 shadow-sm space-y-6">
        
        {/* Header Ribbon */}
        <div className="flex items-center gap-3 border-b border-[#DDD9D1] pb-5">
          <div className="w-12 h-12 rounded-sm bg-[#FEF3E8] border border-[#FCDDC1] flex items-center justify-center text-[#C96A28]">
            <ShieldAlert className="w-6 h-6" strokeWidth={1.8} />
          </div>
          <div>
            <span className="text-[10px] font-mono uppercase tracking-wider font-semibold text-[#A05520] block">
              Sovereign Role-Based Access Control (RBAC)
            </span>
            <h2 className="font-serif text-2xl text-[#1C2B3A]">
              {isUnauthenticated ? 'Authentication Required' : 'Access Restricted: Clearance Required'}
            </h2>
          </div>
        </div>

        {/* Diagnostic Explanation Card */}
        {isUnauthenticated ? (
          <div className="p-4 bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm space-y-2 text-xs">
            <p className="text-[#1C2B3A] font-semibold">
              You are attempting to access the {getRoleTitle(attemptedRole)}.
            </p>
            <p className="text-[#6B7A8D] leading-relaxed">
              This section contains sensitive medical and operational data protected under the HealthSetu sovereign protocol. Please log in with your sovereign Unique ID or register a new profile to continue.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="p-4 bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm space-y-3 text-xs">
              <div className="flex items-center justify-between pb-2 border-b border-[#DDD9D1]">
                <div>
                  <span className="text-[10px] font-semibold text-[#6B7A8D] uppercase tracking-wider block">
                    Your Current Identity:
                  </span>
                  <div className="flex items-center gap-2 mt-0.5">
                    {getRoleIcon(currentUser.role)}
                    <span className="font-semibold text-[#1C2B3A]">{currentUser.name}</span>
                    <span className="font-mono text-[11px] px-1.5 py-0.2 rounded-sm bg-white border border-[#DDD9D1] text-[#2B5F8A]">
                      {currentUser.id}
                    </span>
                  </div>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-sm bg-[#EBF5EC] text-[#2D5A40] border border-[#D3EAD7] font-semibold uppercase">
                  {currentUser.role}
                </span>
              </div>

              <div>
                <span className="text-[10px] font-semibold text-[#A05520] uppercase tracking-wider block">
                  Required Clearance For This Portal:
                </span>
                <span className="font-semibold text-[#1C2B3A] mt-0.5 block">
                  {getRequiredRole(attemptedRole)}
                </span>
              </div>

              <p className="text-[#6B7A8D] leading-relaxed pt-1">
                You do not have permission to access the <strong>{getRoleTitle(attemptedRole)}</strong> using your <strong>{currentUser.role.toUpperCase()}</strong> account.
                {currentUser.role === 'patient' && (
                  <span> As a registered patient, your medical rights are sovereign to your personal health vault. Prescribing and clinical oversight workspaces require clinician-grade license verification.</span>
                )}
                {currentUser.role === 'doctor' && (
                  <span> Treating clinicians access patient records through clinical lookup rather than personal patient vaults.</span>
                )}
                {currentUser.role === 'hospital' && (
                  <span> Hospital administrative accounts manage capacity and emergency resource nodes rather than clinician prescribing or personal patient records.</span>
                )}
              </p>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-3 border-t border-[#DDD9D1]">
          <button
            type="button"
            onClick={onNavigateHome}
            className="w-full sm:w-auto text-xs font-semibold text-[#6B7A8D] hover:text-[#1C2B3A] flex items-center justify-center gap-1.5 py-2 px-3"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Return to Overview</span>
          </button>

          <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto justify-end">
            {currentUser && (
              <button
                type="button"
                onClick={() => onNavigateAllowedPortal(currentUser.role)}
                className="w-full sm:w-auto bg-[#1C2B3A] text-white font-semibold text-xs px-4 py-2 rounded-sm hover:bg-[#2C3B4A] transition-colors flex items-center justify-center gap-1.5 shadow-sm"
              >
                <span>Go to Your {currentUser.role === 'patient' ? 'Patient Portal' : currentUser.role === 'doctor' ? 'Doctor Workspace' : 'Hospital Portal'}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}

            <button
              type="button"
              onClick={() => onOpenAuth(attemptedRole)}
              className="w-full sm:w-auto bg-white border border-[#DDD9D1] text-[#1C2B3A] font-semibold text-xs px-4 py-2 rounded-sm hover:bg-[#FAF8F3] hover:border-[#1C2B3A] transition-colors flex items-center justify-center gap-1.5 shadow-2xs"
            >
              <KeyRound className="w-3.5 h-3.5 text-[#2B5F8A]" />
              <span>{isUnauthenticated ? 'Log In / Register' : `Sign In as ${attemptedRole.toUpperCase()}`}</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
