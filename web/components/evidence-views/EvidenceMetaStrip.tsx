'use client';

interface EvidenceMetaStripProps {
  referenceId: string;
  claimsCount: number;
  sourcesCount: number;
  sourcesFoundCount?: number;
  processingTimeMs?: number;
}

function formatReferenceId(id: string): string {
  const clean = id.replace(/-/g, '').slice(0, 8).toUpperCase().padEnd(8, '0');
  return `TRU-${clean.slice(0, 4)}-${clean.slice(4, 8)}`;
}

function formatTime(ms: number): string {
  return `${(ms / 1000).toFixed(1)}s`;
}

function Divider() {
  return <div className="h-8 w-[1px] bg-zinc-200 hidden md:block" />;
}

export function EvidenceMetaStrip({
  referenceId,
  claimsCount,
  sourcesCount,
  sourcesFoundCount,
  processingTimeMs,
}: EvidenceMetaStripProps) {
  return (
    <div className="border border-zinc-200 bg-[var(--surface-raised)] p-4">
      {/* Phone: a 2-column grid, so four stats read as 2×2 rather than three in
          a row with the fourth orphaned beneath (2026-09-10). md+: the one-row
          strip with dividers, as before. */}
      <div className="grid grid-cols-2 gap-4 md:flex md:flex-wrap md:items-center md:justify-between md:gap-6">
        <div className="flex flex-col gap-1">
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-500">
            Reference
          </span>
          <span className="font-mono text-[11px] font-medium">
            {formatReferenceId(referenceId)}
          </span>
        </div>

        <Divider />

        <div className="flex flex-col gap-1">
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-500">
            Claims Analysed
          </span>
          <span className="font-mono text-[11px] font-medium">{claimsCount}</span>
        </div>

        <Divider />

        <div className="flex flex-col gap-1">
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-500">
            Sources Reviewed
          </span>
          {/* Every organised source was reviewed, so Reviewed can never be the
              smaller number. The stored count is taken at the first search and
              misses items added later (coverage recovery, specialist APIs),
              which printed "Reviewed 10 · Organised 14" (A− S6, 2026-09-24). */}
          <span className="font-mono text-[11px] font-medium">{Math.max(sourcesFoundCount || 0, sourcesCount)}</span>
        </div>

        <Divider />

        <div className="flex flex-col gap-1">
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-500">
            Sources Organised
          </span>
          <span className="font-mono text-[11px] font-medium">{sourcesCount}</span>
        </div>

        {processingTimeMs !== undefined && (
          <>
            <Divider />
            <div className="flex flex-col gap-1">
              <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-500">
                Processed
              </span>
              <span className="font-mono text-[11px] font-medium">
                {formatTime(processingTimeMs)}
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
