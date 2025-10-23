'use client';

import { Clock } from 'lucide-react';

interface TimeSensitiveIndicatorProps {
  timeReference: string;
  className?: string;
}

const timeReferenceLabels: Record<string, string> = {
  present: 'Current',
  recent_past: 'Recent',
  specific_year: 'Historical Date',
  historical: 'Historical',
  future: 'Future Prediction',
};

export function TimeSensitiveIndicator({ timeReference, className = '' }: TimeSensitiveIndicatorProps) {
  return (
    <div className={`inline-flex items-center gap-1.5 px-2 py-1 bg-amber-900/20 text-amber-400 border border-amber-600/50 rounded text-xs font-medium ${className}`}>
      <Clock size={12} />
      <span>Time-Sensitive ({timeReferenceLabels[timeReference] || timeReference})</span>
    </div>
  );
}
