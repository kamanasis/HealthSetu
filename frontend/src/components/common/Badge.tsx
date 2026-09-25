import React from 'react';
import { CheckCircle2, Sparkles, AlertTriangle, Building2, Stethoscope } from 'lucide-react';
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
    patient: 'bg-[#EBF4FB] text-[#2B5F8A]',
    doctor: 'bg-[#EBF5EC] text-[#2D5A40]',
    hospital: 'bg-[#F5F0FC] text-[#5B3D8A]',
    warning: 'bg-[#FEF3E8] text-[#A05520]',
    success: 'bg-[#EBF5EC] text-[#3D8B6E]',
    danger: 'bg-[#FDEEF4] text-[#D94F7A]',
    neutral: 'bg-[#F0EDE7] text-[#6B7A8D]',
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
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold text-[#3D8B6E] bg-[#EBF5EC] ${className}`}>
          <CheckCircle2 className="w-3.5 h-3.5 text-[#3D8B6E]" strokeWidth={1.8} />
          Patient-verified
        </span>
      );
    case 'extracted':
      return (
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#FEF3E8] text-[#A05520] border border-[#E07B39]/30 ${className}`}>
          <AlertTriangle className="w-3.5 h-3.5 text-[#E07B39]" strokeWidth={1.8} />
          Raw / unverified
        </span>
      );
    case 'ai-analyzed':
      return (
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-white/60 text-[#1C2B3A] border border-[#DDD9D1] shadow-sm backdrop-blur-sm ${className}`}>
          <Sparkles className="w-3.5 h-3.5 text-[#4A90C4]" strokeWidth={1.8} />
          AI-generated · Review before use
        </span>
      );
    case 'raw':
    default:
      return (
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#FEF3E8] text-[#A05520] border border-[#E07B39]/30 ${className}`}>
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
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#EBF5EC] text-[#2D5A40] ${className}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-[#3D8B6E]" />
          Current {lastUpdated ? `· ${lastUpdated}` : ''}
        </span>
      );
    case 'stale':
      return (
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#FEF3E8] text-[#A05520] ${className}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-[#C9A0A0]" />
          Stale {lastUpdated ? `· ${lastUpdated}` : ''}
        </span>
      );
    case 'unknown':
    default:
      return (
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#F0EDE7] text-[#6B7A8D] ${className}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-[#DDD9D1]" />
          Unknown
        </span>
      );
  }
};
