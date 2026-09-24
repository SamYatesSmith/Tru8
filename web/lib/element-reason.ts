import type { ClaimElement } from '@shared/types';

/**
 * Element state reason: one mechanical sentence saying WHY a non-supported
 * card reads as it does, built only from the stored `basis.state_derivation`
 * counts (no model text).
 *
 * Why it exists (A− S2, 2026-09-24): 11 of 19 graded records had an
 * unresolved / contextual / disputed card with no reason on the page. The
 * mapper's `uncertainty` sentence is often absent, or is suppressed by the
 * Fix 1 verdict gate (`element-caveat.ts`), and sometimes reads as support
 * (Kennedy 75ef5e70: "Sources cite the 5-year seasonal norm around 83%…"
 * under UNRESOLVED, where the real reason was the support floor).
 *
 * Counts and relationships only. The subject is the SOURCES, never the
 * claim. Never states which side is right. Returns null for supported
 * elements, for gaps (the GAP label already says it), and for older checks
 * with no derivation.
 */

interface StateDerivation {
  rule_applied?: string;
  supports_count?: number;
  challenges_count?: number;
  context_count?: number;
}

function n(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
}

export function elementStateReason(element: ClaimElement): string | null {
  const state = element.state;
  if (!state || state === 'supported') return null;
  if ((element.evidenceRefs?.length ?? 0) === 0) return null;

  const sd = (element.basis?.state_derivation ?? null) as StateDerivation | null;
  if (!sd || typeof sd.rule_applied !== 'string') return null;

  const s = sd.supports_count ?? 0;
  const c = sd.challenges_count ?? 0;
  const ctx = sd.context_count ?? 0;

  switch (sd.rule_applied) {
    case 'context_only':
      return `No source here directly supports or challenges this part; ${n(ctx, 'source gives', 'sources give')} context.`;
    case 'support_floor':
    case 'grounds_support_floor':
      // Floor = weight 3: one primary source, or the equivalent across tiers.
      return `${s === 1 ? 'One source supports' : `${s} sources support`} this part; a supported reading needs one primary source or the equivalent weight across tiers.`;
    case 'all_challenges':
      return `${n(c, 'source challenges', 'sources challenge')} this part; none supports it.`;
    case 'challenges_dominant_2x':
      return `Challenging sources (${c}) carry more than twice the weight of supporting ones (${s}) on this part, weighted by tier.`;
    case 'close_split':
      return `Sources divide on this part: ${s} ${s === 1 ? 'supports' : 'support'}, ${c} ${c === 1 ? 'challenges' : 'challenge'}, and neither side clearly outweighs the other.`;
    default:
      return null;
  }
}
