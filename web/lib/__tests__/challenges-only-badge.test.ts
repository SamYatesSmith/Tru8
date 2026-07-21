import { describe, it, expect } from 'vitest';
import { isChallengesOnly } from '@shared/constants';

// §4d fix 3: the pure decision behind the "− Challenged" badge. Both badge
// components (evidence-views + claim-map) and the PDF template key off it.
describe('isChallengesOnly', () => {
  const allChallenges = { state_derivation: { rule_applied: 'all_challenges' } };

  it('fires only for a disputed element derived from challenges alone', () => {
    expect(isChallengesOnly('disputed', allChallenges)).toBe(true);
  });

  it('is false for a mixed dispute (different rule)', () => {
    expect(isChallengesOnly('disputed', { state_derivation: { rule_applied: 'close_split' } })).toBe(
      false,
    );
  });

  it('is false for non-disputed states even with the rule present', () => {
    expect(isChallengesOnly('supported', allChallenges)).toBe(false);
    expect(isChallengesOnly('unresolved', allChallenges)).toBe(false);
  });

  it('is false when basis / rule is missing', () => {
    expect(isChallengesOnly('disputed', undefined)).toBe(false);
    expect(isChallengesOnly('disputed', {})).toBe(false);
    expect(isChallengesOnly('disputed', null)).toBe(false);
  });
});
