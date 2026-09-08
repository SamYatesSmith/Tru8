import type { Claim } from '@shared/types';
import { FactApplicabilityNotice } from './FactApplicabilityNotice';

export function PassageReviewNotice({ claim }: { claim: Claim }) {
  const review = claim.claimMap?.metadata?.passageReview;
  if (!review) return <FactApplicabilityNotice claim={claim} />;
  const conflicts = review.pairs.filter(p => p.status === 'conflict');
  return <><FactApplicabilityNotice claim={claim} /><section aria-label="Passage review coverage" className="border border-zinc-200 bg-zinc-50 p-3 mb-4 text-xs text-zinc-600">
    <p>Passage review: {review.assessed_pairs} of {review.candidate_pairs} eligible source/element pairs inspected. This is a bounded review of retained excerpts, not an exhaustive document check.</p>
    {review.uninspected_pairs > 0 && <p className="mt-1">{review.uninspected_pairs} eligible pairs remain uninspected.</p>}
    {['failed', 'interrupted', 'invalid_response'].includes(review.status) && <p className="mt-1">Passage review did not finish successfully. Earlier mappings remain visible.</p>}
    {conflicts.map((pair, i) => {
      const element = claim.claimMap?.elements.find(e => e.elementId === pair.element_id);
      const source = claim.evidence?.find(e => (e.evidenceId || e.id) === pair.evidence_id);
      return <p key={i} className="mt-2">Review needed: {source?.title || pair.evidence_id} was read as “{pair.proposed_relationship}” for “{element?.description || pair.element_id}”, conflicting with the earlier mapping. The earlier mapping has been retained.</p>;
    })}
  </section></>;
}
