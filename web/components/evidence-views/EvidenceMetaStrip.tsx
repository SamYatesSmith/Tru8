'use client';

interface EvidenceMetaStripProps {
  referenceId: string;
  claimsCount: number;
  sourcesCount: number;
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
  processingTimeMs,
}: EvidenceMetaStripProps) {
  return (
    <div className="border border-zinc-200 bg-[var(--surface-raised)] p-4">
      <div className="flex flex-wrap items-center justify-between gap-6">
        <div className="flex flex-col gap-1">
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">
            Reference
          </span>
          <span className="font-mono text-[11px] font-medium">
            {formatReferenceId(referenceId)}
          </span>
        </div>

        <Divider />

        <div className="flex flex-col gap-1">
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">
            Claims Analysed
          </span>
          <span className="font-mono text-[11px] font-medium">{claimsCount}</span>
        </div>

        <Divider />

        <div className="flex flex-col gap-1">
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">
            Sources Found
          </span>
          <span className="font-mono text-[11px] font-medium">{sourcesCount}</span>
        </div>

        {processingTimeMs !== undefined && (
          <>
            <Divider />
            <div className="flex flex-col gap-1">
              <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">
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
