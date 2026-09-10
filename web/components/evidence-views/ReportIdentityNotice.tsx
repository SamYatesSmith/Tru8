export interface ReportIdentity {
  basis: 'evidence_snapshot_v1';
  contentHash: string;
  revisionId: string | null;
  status: 'retained' | 'unretained';
}

/**
 * Evidence-snapshot identity, folded into a native disclosure (2026-09-09,
 * founder: the bare box made the report "complicated and ugly"). Collapsed
 * by default; the summary line carries the one fact a reader scans for, the
 * hash and the revision link sit inside. Nothing is removed — a `<details>`
 * keeps its content in the DOM, so exports and tests still see it.
 */
export function ReportIdentityNotice({ checkId, identity }: { checkId: string; identity?: ReportIdentity }) {
  if (!identity) return <p className="text-xs text-zinc-500 my-3">Evidence snapshot identity is unavailable for this response.</p>;
  const shortHash = identity.contentHash.slice(0, 12);
  return (
    <details aria-label="Evidence snapshot identity" className="group border border-zinc-200 my-3 text-xs text-zinc-600">
      <summary className="cursor-pointer select-none px-3 py-2 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">
        <span aria-hidden className="inline-block transition-transform group-open:rotate-90">▸</span>
        Record identity
        <span className="min-w-0 truncate normal-case tracking-normal text-zinc-400">
          · {identity.revisionId ? 'retained revision' : 'snapshot only'} · {shortHash}…
        </span>
      </summary>
      <div className="px-3 pb-3 space-y-1">
        <p className="break-all">Evidence snapshot SHA-256: {identity.contentHash}</p>
        {identity.revisionId ? (
          <p className="break-all">
            Retained revision: {identity.revisionId}.{' '}
            <a className="underline" href={`/verify/${encodeURIComponent(checkId)}?revision=${encodeURIComponent(identity.revisionId)}`}>
              Check this revision’s signed fields
            </a>
          </p>
        ) : (
          <p>No matching retained revision is available for this evidence snapshot.</p>
        )}
        <p>This identifies the captured claims and evidence, not every page field or factual accuracy. The live report can change; a later PDF download may capture a newer snapshot.</p>
      </div>
    </details>
  );
}
