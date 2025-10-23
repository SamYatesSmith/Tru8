'use client';

import { Info } from 'lucide-react';

interface NonVerifiableNoticeProps {
  claimType: string;
  reason: string;
  className?: string;
}

const claimTypeLabels: Record<string, string> = {
  opinion: 'Opinion',
  prediction: 'Prediction',
  personal_experience: 'Personal Experience',
  factual: 'Factual Claim',
};

export function NonVerifiableNotice({ claimType, reason, className = '' }: NonVerifiableNoticeProps) {
  return (
    <div className={`bg-slate-700/50 border-2 border-slate-600 rounded-xl p-6 ${className}`}>
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-0.5">
          <Info size={24} className="text-slate-400" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <h4 className="text-base font-bold text-white">Not Verifiable</h4>
            <span className="px-2 py-0.5 bg-slate-600 text-slate-200 text-xs font-medium rounded">
              {claimTypeLabels[claimType] || claimType}
            </span>
          </div>
          <p className="text-sm text-slate-300 leading-relaxed">{reason}</p>
        </div>
      </div>
    </div>
  );
}
