interface UnknownsSummaryStripProps {
  gaps: number;
  unresolved: number;
  coverage: number;
}

export function UnknownsSummaryStrip({
  gaps,
  unresolved,
  coverage,
}: UnknownsSummaryStripProps) {
  return (
    <div className="grid grid-cols-3 gap-4 border border-zinc-200 bg-[var(--surface-raised)] p-5">
      <div className="flex flex-col items-center gap-1">
        <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Gaps</span>
        <span className="font-mono text-2xl font-semibold text-zinc-900">{gaps}</span>
      </div>
      <div className="flex flex-col items-center gap-1">
        <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Unresolved</span>
        <span className="font-mono text-2xl font-semibold text-zinc-500">{unresolved}</span>
      </div>
      <div className="flex flex-col items-center gap-1">
        <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Coverage</span>
        <span className="font-mono text-2xl font-semibold text-zinc-700">{coverage}%</span>
      </div>
    </div>
  );
}
