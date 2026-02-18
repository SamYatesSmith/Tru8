'use client';

interface GapIndicatorProps {
  elementDescription: string;
  elementNumber: number;
}

export function GapIndicator({ elementDescription, elementNumber }: GapIndicatorProps) {
  return (
    <div className="border border-dashed border-zinc-300 bg-zinc-50/30 px-4 py-3 min-w-[170px] text-center">
      <div className="font-mono text-[9px] uppercase tracking-widest text-zinc-300 mb-1">
        Element {String(elementNumber).padStart(2, '0')}
      </div>
      <div className="text-[11px] text-zinc-400 italic mb-1 line-clamp-1">
        {elementDescription}
      </div>
      <div className="font-mono text-[9px] uppercase tracking-widest text-zinc-300">
        No evidence found
      </div>
    </div>
  );
}
