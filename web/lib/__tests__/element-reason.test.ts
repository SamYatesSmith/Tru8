import { describe, it, expect } from 'vitest';
import type { ClaimElement } from '@shared/types';
import { elementStateReason } from '../element-reason';
import { containsVerdictLanguage } from '../element-caveat';

function el(state: string, sd: Record<string, unknown> | null, refs = 1): ClaimElement {
  return {
    elementId: 'e1',
    description: 'x',
    state,
    uncertainty: null,
    evidenceRefs: Array.from({ length: refs }, (_, i) => ({ evidenceId: `ev-${i}`, relationship: 'context' })),
    basis: sd ? { state_derivation: sd } : undefined,
  } as unknown as ClaimElement;
}

// Derivations taken from stored public records graded 2026-09-24 (A− S2).
const CASES: [string, string, Record<string, unknown>, RegExp][] = [
  ['75ef5e70 e2', 'unresolved', { rule_applied: 'support_floor', supports_count: 1, challenges_count: 0, context_count: 2 }, /^One source supports this part; a supported reading needs one primary source/],
  ['26699bc7 e2', 'contextual', { rule_applied: 'context_only', supports_count: 0, challenges_count: 0, context_count: 5 }, /^No source here directly supports or challenges this part; 5 sources give context\.$/],
  ['540481b1 e1', 'disputed', { rule_applied: 'all_challenges', supports_count: 0, challenges_count: 3, context_count: 2 }, /^3 sources challenge this part; none supports it\.$/],
  ['close split', 'disputed', { rule_applied: 'close_split', supports_count: 2, challenges_count: 1 }, /^Sources divide on this part: 2 support, 1 challenges/],
  ['2x challenge', 'disputed', { rule_applied: 'challenges_dominant_2x', supports_count: 1, challenges_count: 3 }, /more than twice the weight/],
  ['grounds floor', 'unresolved', { rule_applied: 'grounds_support_floor', supports_count: 2 }, /^2 sources support this part/],
];

describe('elementStateReason — every non-supported card says why, from counts', () => {
  for (const [name, state, sd, re] of CASES) {
    it(name, () => {
      const r = elementStateReason(el(state, sd));
      expect(r).toMatch(re);
      // Never adjudicates: the reason must pass the same no-verdict gate as
      // model text (it is ours, so it must be cleaner, not exempt).
      expect(containsVerdictLanguage(r!)).toBe(false);
    });
  }

  it('says nothing for supported elements, gaps, or older checks with no derivation', () => {
    expect(elementStateReason(el('supported', { rule_applied: 'all_supports', supports_count: 3 }))).toBeNull();
    expect(elementStateReason(el('unresolved', { rule_applied: 'no_evidence' }, 0))).toBeNull();
    expect(elementStateReason(el('contextual', null))).toBeNull();
    expect(elementStateReason(el('disputed', { rule_applied: 'something_new' }))).toBeNull();
  });
});
