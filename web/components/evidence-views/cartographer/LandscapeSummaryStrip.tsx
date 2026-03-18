'use client';

interface LandscapeSummaryStripProps {
  totalSources: number;
  primaryCount: number;
  reportingCount: number;
  commentaryCount: number;
}

export function LandscapeSummaryStrip({
  totalSources,
  primaryCount,
  reportingCount,
  commentaryCount,
}: LandscapeSummaryStripProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12 border border-zinc-200 bg-[var(--surface-raised)] p-5">
      <div className="flex flex-col items-center gap-1">
        <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Sources</span>
        <span className="font-mono text-2xl font-semibold text-zinc-900">{totalSources}</span>
      </div>
      <div className="flex flex-col items-center gap-1">
        <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Primary</span>
        <span className="font-mono text-2xl font-semibold" style={{ color: 'var(--tier1-accent)' }}>{primaryCount}</span>
      </div>
      <div className="flex flex-col items-center gap-1">
        <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Reporting</span>
        <span className="font-mono text-2xl font-semibold text-zinc-700">{reportingCount}</span>
      </div>
      <div className="flex flex-col items-center gap-1">
        <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Commentary</span>
        <span className="font-mono text-2xl font-semibold text-zinc-400">{commentaryCount}</span>
      </div>
    </div>
  );
}
