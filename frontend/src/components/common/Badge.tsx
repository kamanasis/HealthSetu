import React from 'react';
import { CheckCircle2, Sparkles, AlertTriangle, Clock, Stethoscope } from 'lucide-react';
import { TrustState, FreshnessState } from '../../types';

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
    patient: 'bg-[#EBF4FB] text-[#2B5F8A] border border-[#D5E8F8]',
    doctor: 'bg-[#EBF5EC] text-[#2D5A40] border border-[#D3EAD7]',
    hospital: 'bg-[#F5F0FC] text-[#5B3D8A] border border-[#E9DCF8]',
    warning: 'bg-[#FEF3E8] text-[#A05520] border border-[#FCDDC1]',
    success: 'bg-[#EBF5EC] text-[#3D8B6E] border border-[#D3EAD7]',
    danger: 'bg-[#FDEEF4] text-[#D94F7A] border border-[#FAD3E2]',
    neutral: 'bg-[#F0EDE7] text-[#6B7A8D] border border-[#DDD9D1]',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ${variantStyles[variant]} ${className}`}
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
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#EBF5EC] text-[#3D8B6E] border border-[#D3EAD7] ${className}`}>
          <CheckCircle2 className="w-3.5 h-3.5" />
          Patient Verified
        </span>
      );
    case 'extracted':
      return (
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#FEF3E8] text-[#A05520] border border-[#FCDDC1] ${className}`}>
          <AlertTriangle className="w-3.5 h-3.5 text-[#E07B39]" />
          Extracted · Review Required
        </span>
      );
    case 'ai-analyzed':
      return (
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-white/90 text-[#4A90C4] border border-[#DDD9D1] shadow-sm backdrop-blur-sm ${className}`}>
          <Sparkles className="w-3.5 h-3.5 text-[#4A90C4]" />
          AI-generated · Review before use
        </span>
      );
    case 'raw':
    default:
      return (
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#F0EDE7] text-[#6B7A8D] border border-[#DDD9D1] ${className}`}>
          Raw Unverified
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
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#EBF5EC] text-[#2D5A40] border border-[#D3EAD7] ${className}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-[#3D8B6E] animate-pulse" />
          Current {lastUpdated ? `· ${lastUpdated}` : ''}
        </span>
      );
    case 'stale':
      return (
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#FEF3E8] text-[#A05520] border border-[#FCDDC1] ${className}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-[#E07B39]" />
          Stale {lastUpdated ? `· ${lastUpdated}` : ''}
        </span>
      );
    case 'unknown':
    default:
      return (
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#F0EDE7] text-[#6B7A8D] border border-[#DDD9D1] ${className}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-[#DDD9D1]" />
          Unknown Freshness
        </span>
      );
  }
};
