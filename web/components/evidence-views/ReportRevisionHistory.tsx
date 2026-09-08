'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { apiClient } from '@/lib/api';
import { parseServerDate } from '@/lib/utils';
import { revisionChanges, safeSourceUrl } from '@/lib/report-revisions';
import type { ReportRevision, RevisionSummary } from '@/lib/report-revisions';

export function ReportRevisionHistory({ checkId, refreshKey }: { checkId: string; refreshKey?: unknown }) {
  const { getToken } = useAuth();
  const [open, setOpen] = useState(false);
  const [retry, setRetry] = useState(0);
  const [detailRetry, setDetailRetry] = useState(0);
  const [list, setList] = useState<RevisionSummary[] | null>(null);
  const [selected, setSelected] = useState('');
  const [comparison, setComparison] = useState('');
  const [listError, setListError] = useState(false);
  const [detailError, setDetailError] = useState('');
  const [result, setResult] = useState<{ key: string; revision: ReportRevision; baseline?: ReportRevision } | null>(null);
  const resultKey = `${checkId}:${selected}:${comparison}`;

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setList(null); setListError(false); setSelected(''); setComparison('');
    (async () => {
      try {
        const token = await getToken();
        if (!token) throw new Error('Authentication required');
        const data = await apiClient.getReportRevisions(checkId, token);
        if (cancelled) return;
        setList(data.revisions);
      } catch { if (!cancelled) setListError(true); }
    })();
    return () => { cancelled = true; };
  }, [checkId, refreshKey, open, getToken, retry]);

  useEffect(() => {
    if (!open || !selected) return;
    let cancelled = false;
    setDetailError('');
    setResult(null);
    (async () => {
      try {
        const token = await getToken();
        if (!token) throw new Error('Authentication required');
        const [revision, baseline] = await Promise.all([
          apiClient.getReportRevision(checkId, selected, token),
          comparison ? apiClient.getReportRevision(checkId, comparison, token) : Promise.resolve(undefined),
        ]);
        if (cancelled) return;
        for (const [value, id] of [[revision, selected], [baseline, comparison]] as const) {
          if (value && (value.id !== id || value.snapshot.check.id !== checkId || value.snapshot.format_version !== 1)) {
            throw new Error('Unsupported or mismatched revision');
          }
        }
        setResult({ key: resultKey, revision, baseline });
      } catch { if (!cancelled) setDetailError(resultKey); }
    })();
    return () => { cancelled = true; };
  }, [checkId, selected, comparison, open, getToken, resultKey, detailRetry]);

  const visible = result?.key === resultKey ? result : null;
  const changes = visible?.baseline ? revisionChanges(visible.baseline.snapshot, visible.revision.snapshot) : null;
  const label = (r: RevisionSummary) => `${r.phase === 'before' ? 'Before' : 'After'} strengthening · ${parseServerDate(r.createdAt).toLocaleString()} · ${r.id}`;
  return <section className="border border-zinc-200 p-4 my-4" aria-label="Report revision history">
    <button type="button" aria-expanded={open} className="text-sm font-medium underline" onClick={() => {
      setSelected(''); setComparison(''); setResult(null); setList(null); setOpen(value => !value);
    }}>
      {open ? 'Close revision history' : 'Revision history'}
    </button>
    {open && <div className="mt-3 space-y-3 text-sm">
      <p>Read-only snapshots retained around strengthening. Selecting one does not replace the current report below. This is not a complete edit history.</p>
      {listError ? <p role="alert">Revision history could not be loaded. <button type="button" className="underline" onClick={() => setRetry(value => value + 1)}>Retry history</button></p>
        : list === null ? <p role="status">Loading revision history…</p>
        : !list.length ? <p>No retained revisions are available for this report. Earlier versions cannot be reconstructed from the current report.</p>
        : <>
          <label className="block">Revision to inspect
            <select className="block border p-2 w-full" value={selected} onChange={e => {
              const id = e.target.value; setSelected(id);
              const chosen = list.find(r => r.id === id);
              setComparison(chosen?.phase === 'after' ? list.find(r => r.operationId === chosen.operationId && r.phase === 'before')?.id || '' : '');
            }}><option value="">Choose a revision</option>{[...list].reverse().map(r => <option key={r.id} value={r.id}>{label(r)}</option>)}</select>
          </label>
          {selected && <label className="block">Compare from
            <select className="block border p-2 w-full" value={comparison} onChange={e => setComparison(e.target.value)}>
              <option value="">No comparison</option>{list.filter(r => r.id !== selected).map(r => <option key={r.id} value={r.id}>{label(r)}</option>)}
            </select>
          </label>}
          {selected && (detailError === resultKey ? <p role="alert">This revision could not be loaded. <button type="button" className="underline" onClick={() => setDetailRetry(value => value + 1)}>Retry revision</button></p>
            : !visible ? <p role="status">Loading retained revision…</p>
            : <article className="border-t pt-3 space-y-3" aria-label="Retained revision">
              <h3 className="font-medium break-all">Retained revision: {visible.revision.id}</h3>
              <p>{visible.revision.snapshot.manifest ? 'A signature was stored with this revision; it has not been verified by this viewer.' : 'No signature was stored with this revision.'} Signature coverage does not include every narrative word.</p>
              {changes && <div><h4 className="font-medium">Element and relationship changes from {visible.baseline!.id}</h4>
                {changes.length ? <ul className="list-disc pl-5">{changes.map((change, i) => <li key={i}>{change}</li>)}</ul>
                  : <p>No element or relationship changes were found. This comparison does not cover every report field.</p>}
              </div>}
              {visible.revision.snapshot.claims.map(claim => <section key={claim.id} className="border-t pt-3">
                <h4 className="font-medium">{claim.text}</h4>
                <details><summary className="cursor-pointer">Retained source ledger ({claim.evidence.length})</summary>
                  <ul className="list-disc pl-5">{claim.evidence.map((source, i) => {
                    const url = safeSourceUrl(source.url);
                    return <li key={source.id || source.evidence_id || i}>{url
                      ? <a className="underline" href={url} target="_blank" rel="noopener noreferrer">{source.title || source.url}</a>
                      : source.title || source.evidence_id || 'Source details unavailable'}</li>;
                  })}</ul>
                </details>
                {!claim.claimMap?.elements?.length && <p>No element map was retained for this claim.</p>}
                {claim.claimMap?.elements?.map(element => <div key={element.element_id} className="my-3 pl-3 border-l">
                  <p>{element.description} — {element.state || 'state unavailable'}</p>
                  {element.uncertainty && <p>{element.uncertainty}</p>}
                  {!element.evidence_refs?.length && <p>No linked evidence was retained.</p>}
                  {element.evidence_refs?.map(ref => {
                    const source = claim.evidence.find(e => (e.evidence_id || e.id) === ref.evidence_id);
                    const url = safeSourceUrl(source?.url);
                    return <div key={ref.evidence_id} className="mt-2">
                      <p>{url ? <a className="underline" href={url} target="_blank" rel="noopener noreferrer">{source?.title || ref.evidence_id}</a> : source?.title || ref.evidence_id}: {ref.relationship}</p>
                      {ref.reasoning && <p>{ref.reasoning}</p>}
                      {ref.citations?.map((citation, i) => <blockquote key={i} className="border-l pl-3 mt-1">{citation.quote}</blockquote>)}
                    </div>;
                  })}
                </div>)}
              </section>)}
            </article>)}
        </>}
    </div>}
  </section>;
}
