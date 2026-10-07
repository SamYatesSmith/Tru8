import type { Claim } from '@shared/types';
import { interpretationNote } from '@/lib/system-interpretation';

/** Publisher concentration and the relationship scope review, above the
 *  evidence of a claim. (Was PassageReviewNotice until 2026-10-07, when the
 *  passage-review and fact-applicability candidates were removed.) */
export function SourceScopeNotices({ claim, readOnly }: { claim: Claim; readOnly?: boolean }) {
  const concentration = claim.claimMap?.metadata?.sourceConcentration;
  const concentrationNotice = concentration && concentration.domains.some(d => d.documents > 1) ?
    <p className="border border-zinc-200 bg-zinc-50 p-3 mb-4 text-xs text-zinc-600">Publisher concentration: {concentration.domains.filter(d => d.documents > 1).map(d => `${d.documents} mapped documents from ${d.domain}`).join('; ')}. Documents from one domain are not necessarily independent evidence. Source classifications are unchanged by these counts.</p> : null;
  const scope = claim.claimMap?.metadata?.scopeReview;
  const scopeNotice = scope ? <section aria-label="Evidence scope review" className="border border-zinc-200 bg-zinc-50 p-3 mb-4 text-xs text-zinc-600">
    <p>Scope review: {scope.assessed_pairs} of {scope.candidate_pairs} directional relationships inspected. This is a system interpretation of supplied text, not independent verification.</p>
    {scope.uninspected_pairs > 0 && <p>{scope.uninspected_pairs} relationships remain uninspected; earlier mappings remain visible.</p>}
    {['failed', 'interrupted', 'invalid_response'].includes(scope.status) && <p>Scope review did not finish successfully.</p>}
    {scope.pairs.filter(p => p.status === 'scoped').map((p, i) => <p key={i} className="mt-1">Retained as context: {claim.evidence?.find(e => (e.evidenceId || e.id) === p.evidence_id)?.title || p.evidence_id}. {interpretationNote(p.reasoning, readOnly)}</p>)}
  </section> : null;
  return <>{concentrationNotice}{scopeNotice}</>;
}
