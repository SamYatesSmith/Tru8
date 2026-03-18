function formatRange(earliest: Date, latest: Date): string {
  const fmt = (d: Date) => d.toLocaleDateString('en-GB', { month: 'short', year: 'numeric' });
  return `${fmt(earliest)} – ${fmt(latest)}`;
}

function formatRelative(date: Date): string {
  const days = Math.floor((Date.now() - date.getTime()) / (1000 * 60 * 60 * 24));
  if (days < 1) return 'today';
  if (days === 1) return '1d ago';
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo`;
  return `${Math.floor(days / 365)}yr`;
}

interface TemporalInsightStripProps {
  earliest: Date;
  latest: Date;
  datedCount: number;
  totalCount: number;
  gapCount: number;
}

export function TemporalInsightStrip({
  earliest,
  latest,
  datedCount,
  totalCount,
  gapCount,
}: TemporalInsightStripProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8 border border-zinc-200 bg-[var(--surface-raised)] p-5">
      <div className="flex flex-col items-center gap-1">
        <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Date Range</span>
        <span className="font-mono text-sm font-semibold text-zinc-900">{formatRange(earliest, latest)}</span>
      </div>
      <div className="flex flex-col items-center gap-1">
        <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Sources</span>
        <span className="font-mono text-2xl font-semibold text-zinc-900">
          {datedCount} <span className="text-sm text-zinc-400">of {totalCount}</span>
        </span>
      </div>
      <div className="flex flex-col items-center gap-1">
        <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Freshness</span>
        <span className="font-mono text-2xl font-semibold text-zinc-700">{formatRelative(latest)}</span>
      </div>
      <div className="flex flex-col items-center gap-1">
        <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Gaps</span>
        <span className="font-mono text-2xl font-semibold text-zinc-300">{gapCount}</span>
      </div>
    </div>
  );
}
