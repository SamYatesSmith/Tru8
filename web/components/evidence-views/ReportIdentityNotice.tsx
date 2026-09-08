export interface ReportIdentity {
  basis: 'evidence_snapshot_v1';
  contentHash: string;
  revisionId: string | null;
  status: 'retained' | 'unretained';
}

export function ReportIdentityNotice({ checkId, identity }: { checkId: string; identity?: ReportIdentity }) {
  if (!identity) return <p className="text-xs text-zinc-500 my-3">Evidence snapshot identity is unavailable for this response.</p>;
  return <section aria-label="Evidence snapshot identity" className="border border-zinc-200 p-3 my-3 text-xs text-zinc-600 space-y-1">
    <p className="break-all">Evidence snapshot SHA-256: {identity.contentHash}</p>
    {identity.revisionId ? <p className="break-all">Retained revision: {identity.revisionId}. <a className="underline" href={`/verify/${encodeURIComponent(checkId)}?revision=${encodeURIComponent(identity.revisionId)}`}>Check this revision’s signed fields</a></p>
      : <p>No matching retained revision is available for this evidence snapshot.</p>}
    <p>This identifies the captured claims and evidence, not every page field or factual accuracy. The live report can change; a later PDF download may capture a newer snapshot.</p>
  </section>;
}
