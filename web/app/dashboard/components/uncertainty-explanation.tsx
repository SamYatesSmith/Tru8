'use client';

import { AlertTriangle } from 'lucide-react';

interface UncertaintyExplanationProps {
  explanation: string;
  className?: string;
}

export function UncertaintyExplanation({ explanation, className = '' }: UncertaintyExplanationProps) {
  if (!explanation) return null;

  return (
    <div className={`bg-amber-900/20 border-2 border-amber-600/50 rounded-xl p-4 ${className}`}>
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-0.5">
          <AlertTriangle size={20} className="text-amber-400" />
        </div>
        <div className="flex-1">
          <h4 className="text-sm font-semibold text-amber-300 mb-1">Why Uncertain?</h4>
          <p className="text-sm text-amber-100 leading-relaxed">{explanation}</p>
        </div>
      </div>
    </div>
  );
}
