'use client';

interface ExtractionSummaryStripProps {
  referenceId: string;
  claimsFound: number;
  extractionTime: string;
}

export function ExtractionSummaryStrip({
  referenceId,
  claimsFound,
  extractionTime,
}: ExtractionSummaryStripProps) {
  return (
    <div className="border border-zinc-200 bg-[var(--surface-raised)] p-4 mb-8">
      <div className="flex flex-wrap items-center justify-between gap-6">
        <div className="flex flex-col gap-1">
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">
            Reference
          </span>
          <span className="font-mono text-[11px] font-medium">{referenceId}</span>
        </div>
        <div className="h-8 w-[1px] bg-zinc-200 hidden md:block" />
        <div className="flex flex-col gap-1">
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">
            Claims Found
          </span>
          <span className="font-mono text-[11px] font-medium">{claimsFound}</span>
        </div>
        <div className="h-8 w-[1px] bg-zinc-200 hidden md:block" />
        <div className="flex flex-col gap-1">
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">
            Extracted
          </span>
          <span className="font-mono text-[11px] font-medium">{extractionTime}</span>
        </div>
        <div className="h-8 w-[1px] bg-zinc-200 hidden md:block" />
        <div className="flex flex-col gap-1">
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">
            Status
          </span>
          <span
            className="font-mono text-[11px] font-medium"
            style={{ color: 'var(--accent)' }}
          >
            Awaiting Selection
          </span>
        </div>
      </div>
    </div>
  );
}
