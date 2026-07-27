import type { ClaimMap } from '@shared/types';

/**
 * Is this claim's orientation line deliberately suppressed?
 *
 * A null `orientation` has TWO meanings and they must render differently:
 *
 *  - **suppressed** — the claim is an opinion, its elements are open QUESTIONS
 *    derived FROM that opinion, and summing them ("evidence predominantly
 *    supports all 4") reads as a verdict on the opinion. Tru8 deliberately says
 *    nothing here. Render NOTHING.
 *  - **absent** — derivation genuinely produced no line (no elements, no states).
 *    The existing fallback copy is correct there.
 *
 * Without this distinction the suppressed case renders fallback text — which is
 * worse than the verdict it replaced. `ClaimSummaryPanel` would have shown
 * "The gathered evidence doesn't clearly lean either way", i.e. false balance in
 * the slot we cleared precisely to avoid adjudicating.
 *
 * Backend counterpart: `apply_orientation` (claim_map_analyzer.py) — it sets the
 * prose to null on exactly this condition. Keep the two in step.
 *
 * Phase 1 mechanical honesty, 2026-07-27.
 * Design: audit/2026-07-27_phase1_mechanical_honesty_design.md
 */
export function isOrientationSuppressed(
  claimMap: Pick<ClaimMap, 'metadata'> | null | undefined
): boolean {
  return claimMap?.metadata?.grounds?.applied === true;
}
