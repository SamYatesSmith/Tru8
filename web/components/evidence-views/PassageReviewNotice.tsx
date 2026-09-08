import type { Claim } from '@shared/types';
import { FactApplicabilityNotice } from './FactApplicabilityNotice';

export function PassageReviewNotice({ claim }: { claim: Claim }) {
  const concentration = claim.claimMap?.metadata?.sourceConcentration;
  const concentrationNotice = concentration && concentration.domains.some(d => d.documents > 1) ?
    <p className="border border-zinc-200 bg-zinc-50 p-3 mb-4 text-xs text-zinc-600">Publisher concentration: {concentration.domains.filter(d => d.documents > 1).map(d => `${d.documents} mapped documents from ${d.domain}`).join('; ')}. Documents from one domain are not necessarily independent evidence. Source classifications are unchanged by these counts.</p> : null;
  const review = claim.claimMap?.metadata?.passageReview;
  const scope = claim.claimMap?.metadata?.scopeReview;
  const scopeNotice = scope ? <section aria-label="Evidence scope review" className="border border-zinc-200 bg-zinc-50 p-3 mb-4 text-xs text-zinc-600">
    <p>Scope review: {scope.assessed_pairs} of {scope.candidate_pairs} directional relationships inspected. This is a system interpretation of supplied text, not independent verification.</p>
    {scope.uninspected_pairs > 0 && <p>{scope.uninspected_pairs} relationships remain uninspected; earlier mappings remain visible.</p>}
    {['failed', 'interrupted', 'invalid_response'].includes(scope.status) && <p>Scope review did not finish successfully.</p>}
    {scope.pairs.filter(p => p.status === 'scoped').map((p, i) => <p key={i} className="mt-1">Retained as context: {claim.evidence?.find(e => (e.evidenceId || e.id) === p.evidence_id)?.title || p.evidence_id}. {p.reasoning}</p>)}
  </section> : null;
  if (!review) return <>{concentrationNotice}<FactApplicabilityNotice claim={claim} />{scopeNotice}</>;
  const conflicts = review.pairs.filter(p => p.status === 'conflict');
  return <>{concentrationNotice}<FactApplicabilityNotice claim={claim} />{scopeNotice}<section aria-label="Passage review coverage" className="border border-zinc-200 bg-zinc-50 p-3 mb-4 text-xs text-zinc-600">
    <p>Passage review: {review.assessed_pairs} of {review.candidate_pairs} eligible source/element pairs inspected. This is a bounded review of retained excerpts, not an exhaustive document check.</p>
    {review.uninspected_pairs > 0 && <p className="mt-1">{review.uninspected_pairs} eligible pairs remain uninspected.</p>}
    {['failed', 'interrupted', 'invalid_response'].includes(review.status) && <p className="mt-1">Passage review did not finish successfully. Earlier mappings remain visible.</p>}
    {conflicts.map((pair, i) => {
      const element = claim.claimMap?.elements.find(e => e.elementId === pair.element_id);
      const source = claim.evidence?.find(e => (e.evidenceId || e.id) === pair.evidence_id);
      const subsequentlyScoped = scope?.pairs.some(p => p.element_id === pair.element_id && p.evidence_id === pair.evidence_id && p.status === 'scoped');
      return <p key={i} className="mt-2">Review needed: {source?.title || pair.evidence_id} was read as “{pair.proposed_relationship}” for “{element?.description || pair.element_id}”, conflicting with the earlier mapping. {subsequentlyScoped ? 'A later scope review retained this source as context; the earlier interpretation remains in the audit record.' : 'The earlier mapping has been retained.'}</p>;
    })}
  </section></>;
}
