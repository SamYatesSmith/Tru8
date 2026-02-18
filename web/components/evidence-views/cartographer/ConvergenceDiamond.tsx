'use client';

interface ConvergenceDiamondProps {
  count: number;
}

export function ConvergenceDiamond({ count }: ConvergenceDiamondProps) {
  if (count === 0) return null;

  return (
    <div className="flex justify-center my-4">
      <div className="flex items-center gap-3">
        <div className="h-[1px] w-16 bg-zinc-200" />
        <div className="flex items-center gap-2 px-3 py-1.5 border border-orange-200 bg-orange-50">
          <div className="w-[10px] h-[10px] bg-[var(--convergence)] rotate-45" />
          <span className="font-mono text-[9px] uppercase tracking-widest text-orange-700 font-bold">
            {count} convergence {count === 1 ? 'point' : 'points'}
          </span>
        </div>
        <div className="h-[1px] w-16 bg-zinc-200" />
      </div>
    </div>
  );
}
