'use client';

import { ShieldCheck } from 'lucide-react';

interface FactCheckBadgeProps {
  publisher: string;
  rating?: string;
  className?: string;
}

export function FactCheckBadge({ publisher, rating, className = '' }: FactCheckBadgeProps) {
  return (
    <div className={`inline-flex items-center gap-1.5 px-2 py-1 bg-blue-900/30 text-blue-300 border border-blue-600/50 rounded text-xs font-medium ${className}`}>
      <ShieldCheck size={12} />
      <span>Fact-Check: {publisher}</span>
      {rating && (
        <>
          <span className="text-blue-500">·</span>
          <span className="text-blue-200">{rating}</span>
        </>
      )}
    </div>
  );
}
