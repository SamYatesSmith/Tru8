'use client';

import { ShieldCheck } from 'lucide-react';

interface FactCheckBadgeProps {
  publisher: string;
  rating?: string;
  className?: string;
}

export function FactCheckBadge({ publisher, rating, className = '' }: FactCheckBadgeProps) {
  return (
    <div className={`inline-flex items-center gap-1.5 px-2 py-1 bg-blue-50 text-blue-700 border border-blue-200 text-xs font-medium ${className}`}>
      <ShieldCheck size={12} />
      <span>Fact-Check: {publisher}</span>
      {rating && (
        <>
          <span className="text-blue-400">&middot;</span>
          <span className="text-blue-600">{rating}</span>
        </>
      )}
    </div>
  );
}
