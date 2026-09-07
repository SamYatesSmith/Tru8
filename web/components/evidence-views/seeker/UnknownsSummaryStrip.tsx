interface UnknownsSummaryStripProps {
  gaps: number;
  needsReview: number;
  coverage: number;
}

export function UnknownsSummaryStrip({
  gaps,
  needsReview,
  coverage,
}: UnknownsSummaryStripProps) {
  return (
    <div className="border border-zinc-200 bg-[var(--surface-raised)] p-5">
      <div className="grid grid-cols-3 gap-4">
        <div className="flex flex-col items-center gap-1">
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Gaps</span>
          <span className="font-mono text-2xl font-semibold text-zinc-900">{gaps}</span>
        </div>
        <div className="flex flex-col items-center gap-1">
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Needs review</span>
          <span className="font-mono text-2xl font-semibold text-zinc-500">{needsReview}</span>
        </div>
        <div className="flex flex-col items-center gap-1">
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Evidence mapped</span>
          <span className="font-mono text-2xl font-semibold text-zinc-700">{coverage}%</span>
        </div>
      </div>
      <p className="text-center font-mono text-[10px] text-zinc-400 mt-3 leading-relaxed">
        <span className="font-bold">Gaps</span> have no mapped evidence.{' '}
        <span className="font-bold">Needs review</span> includes contextual, disputed and unresolved elements with evidence.{' '}
        The percentage measures evidence presence, not certainty or search completeness.
      </p>
    </div>
  );
}
