'use client';

interface ClaimSummaryProps {
  orientation: string | null;
}

export function ClaimSummary({ orientation }: ClaimSummaryProps) {
  if (!orientation) return null;

  return (
    <div className="border border-zinc-200 bg-[var(--surface-raised)] p-4 mb-10">
      <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400 block mb-2">
        Claim Summary
      </span>
      <p className="text-sm text-zinc-600 leading-relaxed">
        {orientation}
      </p>
    </div>
  );
}
