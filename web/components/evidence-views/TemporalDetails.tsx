import type { Evidence } from '@shared/types';
import { citationText } from '@/lib/passage-citation';

const LABELS = { effective_start: 'Effective from', effective_end: 'Effective until', as_of: 'As of' };

export function TemporalDetails({ evidence }: { evidence: Evidence }) {
  const temporal = evidence.textProvenance?.temporal;
  if (temporal?.version !== 1) return null;
  return (
    <section aria-label="Time applicability" className="mb-4 space-y-2 text-[11px] text-zinc-600">
      <h3 className="font-mono uppercase text-zinc-500">Time applicability</h3>
      <p>Applicability to this claim is unestablished. Date statements below are unreviewed source wording; they may describe historical, planned or unrelated facts.</p>
      {temporal.publication.precision === 'unknown' && temporal.publication.supplied_value && (
        <p>The original precision of the publication date is unknown.</p>
      )}
      {temporal.statements.length === 0 && <p>No explicit effective-date or “as of” statement was retained. This does not establish that the source has none.</p>}
      {temporal.statements.map((statement, index) => {
        const quote = citationText(evidence, statement.citation);
        const passage = evidence.textProvenance?.passages.find(p => p.id === statement.citation.passage_id);
        return <div key={index}>
          {quote ? <>
            <p>{LABELS[statement.kind]}: {statement.stated_date} · Unreviewed</p>
            <blockquote className="border-l-2 border-zinc-300 pl-3 whitespace-pre-wrap">{quote}</blockquote>
            <details><summary className="cursor-pointer">Read surrounding passage</summary>
              <p className="mt-2 whitespace-pre-wrap">{passage?.text}</p>
            </details>
          </> : <p>The captured passage for this date statement is unavailable.</p>}
        </div>;
      })}
      {temporal.unretained_candidates > 0 && <p>{temporal.unretained_candidates} additional date statements exceeded the retention limit.</p>}
      <p>Only retained excerpts were scanned. A start date alone does not establish that a value is still in force.</p>
    </section>
  );
}
