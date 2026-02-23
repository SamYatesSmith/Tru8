'use client';

interface LandscapeSummaryStripProps {
  totalSources: number;
  primaryCount: number;
  reportingCount: number;
  commentaryCount: number;
  convergencePoints: number;
  gaps: number;
  diagnosticHighCount?: number;
  diagnosticTotalCount?: number;
}

export function LandscapeSummaryStrip({
  totalSources,
  primaryCount,
  reportingCount,
  commentaryCount,
  convergencePoints,
  gaps,
  diagnosticHighCount,
  diagnosticTotalCount,
}: LandscapeSummaryStripProps) {
  const showDiagnostic = diagnosticHighCount != null && diagnosticTotalCount != null && diagnosticTotalCount > 0;

  return (
    <div className={`grid grid-cols-3 ${showDiagnostic ? 'md:grid-cols-7' : 'md:grid-cols-6'} gap-4 mb-12 border border-zinc-200 bg-[var(--surface-raised)] p-5`}>
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
      <div className="flex flex-col items-center gap-1">
        <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Convergence</span>
        <span className="font-mono text-2xl font-semibold" style={{ color: 'var(--convergence)' }}>{convergencePoints}</span>
      </div>
      <div className="flex flex-col items-center gap-1">
        <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Gaps</span>
        <span className="font-mono text-2xl font-semibold text-zinc-300">{gaps}</span>
      </div>
      {showDiagnostic && (
        <div className="flex flex-col items-center gap-1">
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Diagnostic</span>
          <span className="font-mono text-2xl font-semibold" style={{ color: 'var(--accent)' }}>
            {diagnosticHighCount} <span className="text-sm text-zinc-400">of {diagnosticTotalCount}</span>
          </span>
        </div>
      )}
    </div>
  );
}
