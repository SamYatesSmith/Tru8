interface UnknownsSummaryStripProps {
  total: number;
  supported: number;
  disputed: number;
  unresolved: number;
  gaps: number;
  coverage: number;
}

export function UnknownsSummaryStrip({
  total,
  supported,
  disputed,
  unresolved,
  gaps,
  coverage,
}: UnknownsSummaryStripProps) {
  return (
    <div className="grid grid-cols-3 md:grid-cols-6 gap-4 border border-zinc-200 bg-[var(--surface-raised)] p-5">
      <div className="flex flex-col items-center gap-1">
        <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Elements</span>
        <span className="font-mono text-2xl font-semibold text-zinc-900">{total}</span>
      </div>
      <div className="flex flex-col items-center gap-1">
        <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Supported</span>
        <span className="font-mono text-2xl font-semibold text-emerald-500">{supported}</span>
      </div>
      <div className="flex flex-col items-center gap-1">
        <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Disputed</span>
        <span className="font-mono text-2xl font-semibold text-amber-500">{disputed}</span>
      </div>
      <div className="flex flex-col items-center gap-1">
        <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Unresolved</span>
        <span className="font-mono text-2xl font-semibold text-zinc-400">{unresolved}</span>
      </div>
      <div className="flex flex-col items-center gap-1">
        <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Gaps</span>
        <span className="font-mono text-2xl font-semibold text-zinc-300">{gaps}</span>
      </div>
      <div className="flex flex-col items-center gap-1">
        <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Coverage</span>
        <span className="font-mono text-2xl font-semibold text-zinc-700">{coverage}%</span>
      </div>
    </div>
  );
}
