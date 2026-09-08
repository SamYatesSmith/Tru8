import type { Claim } from '@shared/types';

export function FactApplicabilityNotice({ claim }: { claim: Claim }) {
  const elements = (claim.claimMap?.elements || []).map(element => ({
    element,
    entries: (element.basis?.fact_applicability?.scoped || []).filter(entry =>
      element.evidenceRefs?.some(ref => ref.evidenceId === entry.evidence_id && ref.relationship === 'context')),
  })).filter(item => item.entries.length);
  if (!elements.length) return null;
  return <section aria-label="Fact date applicability" className="border border-zinc-200 bg-zinc-50 p-3 mb-4 text-xs text-zinc-600">
    <p>Some sources remain as context because their retained text does not establish when the relevant fact applied. Publication and capture dates do not establish this.</p>
    {elements.map(({ element, entries }) => <div key={element.elementId} className="mt-2">
      <p>{element.description}</p>
      {entries.map((entry, i) => {
        const source = claim.evidence?.find(e => (e.evidenceId || e.id) === entry.evidence_id);
        return <p key={i}>{source?.title || entry.evidence_id}: applicability on {entry.target_day} is unestablished in retained text.</p>;
      })}
    </div>)}
    <p className="mt-2">This does not mean the fact is false or that the complete source lacks the information.</p>
  </section>;
}
