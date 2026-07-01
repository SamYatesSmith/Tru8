'use client';

import { ElementBadge } from '../ElementBadge';

interface GapIndicatorProps {
  elementDescription: string;
  elementNumber: number;
}

export function GapIndicator({ elementDescription, elementNumber }: GapIndicatorProps) {
  return (
    <div className="border border-dashed border-zinc-300 bg-zinc-50/30 px-4 py-3 min-w-[170px] flex flex-col items-center text-center">
      <ElementBadge n={elementNumber} size="sm" className="opacity-60 mb-1.5" />
      <div className="text-[11px] text-zinc-400 italic mb-1 line-clamp-1">
        {elementDescription}
      </div>
      <div className="font-mono text-[9px] uppercase tracking-widest text-zinc-300">
        No evidence found
      </div>
    </div>
  );
}
