'use client';

interface DivergenceDiamondProps {
  count: number;
}

export function DivergenceDiamond({ count }: DivergenceDiamondProps) {
  if (count === 0) return null;

  return (
    <div className="flex justify-center my-2">
      <div className="flex items-center gap-2 px-3 py-1 border border-dashed border-amber-200 bg-amber-50/30">
        <div className="w-[8px] h-[8px] bg-[var(--divergence)] rotate-45" />
        <span className="font-mono text-[9px] uppercase tracking-widest text-amber-600 font-bold">
          {count} {count === 1 ? 'dispute' : 'disputes'}
        </span>
      </div>
    </div>
  );
}
