import React from 'react';
import { CheckCircle2, Sparkles, AlertTriangle } from 'lucide-react';
import type { TrustState, FreshnessState } from '../../types';

interface BadgeProps {
  variant?: 'patient' | 'doctor' | 'hospital' | 'warning' | 'success' | 'danger' | 'neutral';
  children: React.ReactNode;
  className?: string;
  icon?: React.ReactNode;
}

export const Badge: React.FC<BadgeProps> = ({
  variant = 'patient',
  children,
  className = '',
  icon
}) => {
  const variantStyles = {
    patient: 'bg-[#EBF4FB] text-[#2B5F8A] border-[#D5E8F8]',
    doctor: 'bg-[#EBF5EC] text-[#2D5A40] border-[#D3EAD7]',
    hospital: 'bg-[#F5F0FC] text-[#5B3D8A] border-[#E9DCF8]',
    warning: 'bg-[#FEF3E8] text-[#A05520] border-[#FCDDC1]',
    success: 'bg-[#EBF5EC] text-[#3D8B6E] border-[#D3EAD7]',
    danger: 'bg-[#FDEEF4] text-[#D94F7A] border-[#F8D2DF]',
    neutral: 'bg-[#F0EDE7] text-[#6B7A8D] border-[#DDD9D1]',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-sm text-xs font-semibold border ${variantStyles[variant]} ${className}`}
    >
      {icon}
      {children}
    </span>
  );
};

export const TrustBadge: React.FC<{ state: TrustState; className?: string }> = ({ state, className = '' }) => {
  switch (state) {
    case 'verified':
      return (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[11px] font-semibold text-[#2D5A40] bg-[#EBF5EC] border border-[#D3EAD7] ${className}`}>
          <CheckCircle2 className="w-3 h-3 text-[#3D8B6E]" strokeWidth={2} />
          Patient-verified
        </span>
      );
    case 'extracted':
      return (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[11px] font-semibold bg-[#FEF3E8] text-[#A05520] border border-[#FCDDC1] ${className}`}>
          <AlertTriangle className="w-3 h-3 text-[#E07B39]" strokeWidth={2} />
          Raw / unverified
        </span>
      );
    case 'ai-analyzed':
      return (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[11px] font-semibold bg-[#FFFFFF] text-[#1C2B3A] border border-[#DDD9D1] ${className}`}>
          <Sparkles className="w-3 h-3 text-[#4A90C4]" strokeWidth={2} />
          AI-generated · Verified link
        </span>
      );
    case 'raw':
    default:
      return (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[11px] font-semibold bg-[#FEF3E8] text-[#A05520] border border-[#FCDDC1] ${className}`}>
          Raw / unverified
        </span>
      );
  }
};

export const FreshnessBadge: React.FC<{ state: FreshnessState; lastUpdated?: string; className?: string }> = ({
  state,
  lastUpdated,
  className = ''
}) => {
  switch (state) {
    case 'current':
      return (
        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm text-[11px] font-semibold bg-[#EBF5EC] text-[#2D5A40] border border-[#D3EAD7] ${className}`}>
          <span className="w-1.5 h-1.5 rounded-none bg-[#3D8B6E]" />
          Current {lastUpdated ? `· ${lastUpdated}` : ''}
        </span>
      );
    case 'stale':
      return (
        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm text-[11px] font-semibold bg-[#FEF3E8] text-[#A05520] border border-[#FCDDC1] ${className}`}>
          <span className="w-1.5 h-1.5 rounded-none bg-[#E07B39]" />
          Stale {lastUpdated ? `· ${lastUpdated}` : ''}
        </span>
      );
    case 'unknown':
    default:
      return (
        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm text-[11px] font-semibold bg-[#F0EDE7] text-[#6B7A8D] border border-[#DDD9D1] ${className}`}>
          <span className="w-1.5 h-1.5 rounded-none bg-[#6B7A8D]" />
          Unknown
        </span>
      );
  }
};
