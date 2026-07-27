import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';

vi.mock('@/lib/analytics', () => ({ capture: vi.fn() }));
vi.mock('next/navigation', () => ({ useRouter: () => ({ push: vi.fn() }) }));

import { ClaimSummaryPanel } from '../ClaimSummaryPanel';
import { ClaimOverviewCard } from '../overview/ClaimOverviewCard';
import { ClaimSectionCard } from '../overview/ClaimSectionCard';
import { ClarityResponseCard } from '@/app/dashboard/check/[id]/components/clarity-response-card';
import { isOrientationSuppressed } from '@/lib/orientation';
import type { Claim } from '@shared/types';

/**
 * Phase 1 mechanical honesty (2026-07-27) — permanent pin for the SUPPRESSED
 * orientation slot. Design: audit/2026-07-27_phase1_mechanical_honesty_design.md
 *
 * These strings are the whole point. When a claim is an opinion the backend
 * nulls the orientation prose deliberately, and the fallback copy must NOT fire:
 *
 *   "No orientation available."                          -> reads as a failure
 *   "doesn't clearly lean either way"                    -> FALSE BALANCE, in the
 *      exact slot we cleared to stop Tru8 adjudicating an opinion. This is the
 *      same invariant breach as the verdict it replaced, pointing the other way.
 *   "Analysis pending"                                   -> a COMPLETED check
 *      labelled unfinished (clarity/question path).
 *
 * Without this file nothing stops someone reinstating them.
 */

const SUPPRESSED_META = {
  metadata: { grounds: { applied: true, converged: true, element_count: 2 } },
};

function ev(id: string) {
  return {
    id,
    source: 'example.com',
    url: `https://example.com/${id}`,
    title: `Source ${id}`,
    snippet: '...',
    relevanceScore: 0.5,
    receiptStatus: 'shown',
  };
}

/**
 * MUST carry mapped evidence. ClaimSummaryPanel's false-balance line sits behind
 * `evidenceCount > 0 && barTotal > 0`, and `barTotal` counts evidence reachable
 * through element `evidenceRefs`. An empty fixture short-circuits to null BEFORE
 * the guarded branch, so the pin passes for the wrong reason and would not catch
 * a reinstated fallback. (Caught by independent verification, 2026-07-27 — the
 * first version of this file was vacuous on exactly the string that matters
 * most.) Mutation matrix in the design doc records that all four surfaces fire.
 */
function opinionClaim(orientation: string | null = null): Claim {
  return {
    id: 'c1',
    text: 'The rollout was a triumph',
    evidence: [ev('e1'), ev('e2')],
    claimMap: {
      claimId: 'c1',
      normalisedClaim: 'The rollout was a triumph',
      claimType: 'normative_flagged',
      elements: [
        {
          elementId: 'el1',
          description: 'What were the stated targets?',
          state: 'unresolved',
          evidenceRefs: [
            { evidenceId: 'e1', relationship: 'supports' },
            { evidenceId: 'e2', relationship: 'context' },
          ],
        },
      ],
      orientation,
      ...SUPPRESSED_META,
    },
  } as unknown as Claim;
}

function factualClaim(orientation: string | null): Claim {
  return {
    id: 'c2',
    text: 'The fire killed 72 people',
    evidence: [],
    claimMap: {
      claimId: 'c2',
      normalisedClaim: 'The fire killed 72 people',
      claimType: 'empirical',
      elements: [],
      orientation,
      metadata: { elementCount: 0 },
    },
  } as unknown as Claim;
}

const FALLBACKS = [
  'No orientation available.',
  "doesn't clearly lean either way",
  'clearly lean either way',
  'Analysis pending',
];

describe('isOrientationSuppressed', () => {
  it('is true only when the grounds stage rebuilt the elements', () => {
    expect(isOrientationSuppressed(opinionClaim().claimMap)).toBe(true);
    expect(isOrientationSuppressed(factualClaim('x').claimMap)).toBe(false);
    expect(isOrientationSuppressed(undefined)).toBe(false);
    expect(isOrientationSuppressed(null)).toBe(false);
  });
});

describe('suppressed orientation renders NOTHING', () => {
  it('ClaimSummaryPanel emits no fallback copy', () => {
    const { container } = render(
      <ClaimSummaryPanel claim={opinionClaim()} position={0} />
    );
    for (const s of FALLBACKS) expect(container.textContent).not.toContain(s);
  });

  it('ClaimOverviewCard emits no fallback copy', () => {
    const { container } = render(
      <ClaimOverviewCard claim={opinionClaim()} position={0} checkId="chk" />
    );
    expect(container.textContent).not.toContain('No orientation available.');
  });

  it('ClaimSectionCard emits no fallback copy', () => {
    const { container } = render(
      <ClaimSectionCard claim={opinionClaim()} position={0} onExplore={() => {}} />
    );
    expect(container.textContent).not.toContain('No orientation available.');
  });

  it('ClaimSummaryPanel emits no FALSE BALANCE line — the highest-value string', () => {
    // Guard removed => "The gathered evidence doesn't clearly lean either way".
    // That is the Version B breach: false balance in the slot we cleared to stop
    // Tru8 adjudicating an opinion.
    const { container } = render(
      <ClaimSummaryPanel claim={opinionClaim()} position={0} />
    );
    // Fixture-realism guard. Everything above is a NEGATIVE assertion, so an
    // emptied fixture would satisfy them all by rendering nothing and the pin
    // would go quiet — the exact vacuous failure this file was rewritten to
    // fix. "Sources mapped" only renders when barTotal > 0, i.e. when the
    // evidenceRefs actually resolve, which is the precondition for reaching
    // the guarded branch at all. If someone trims opinionClaim() back, this
    // fails loudly instead of passing for the wrong reason.
    expect(container.textContent).toContain('Sources mapped');
    expect(container.textContent).not.toContain('clearly lean either way');
    expect(container.textContent).not.toContain('not yet mapped');
  });

  it('ClarityResponseCard does not label a completed check "Analysis pending"', () => {
    const claim = opinionClaim();
    const { container } = render(
      <ClarityResponseCard
        userQuery="Was the rollout a triumph?"
        relatedClaims={[0]}
        claims={[{ position: 0, text: claim.text, claimMap: claim.claimMap }]}
      />
    );
    expect(container.textContent).toContain('The rollout was a triumph');
    expect(container.textContent).not.toContain('Analysis pending');
  });

  it('suppression beats a stale non-null orientation string', () => {
    const stale = 'Of 4 elements examined, retrieved evidence predominantly supports all 4.';
    const { container } = render(
      <ClaimOverviewCard claim={opinionClaim(stale)} position={0} checkId="chk" />
    );
    expect(container.textContent).not.toContain('predominantly supports');
  });
});

describe('absent-but-not-suppressed keeps the existing fallback', () => {
  it('ClaimOverviewCard still explains a genuinely missing line', () => {
    const { container } = render(
      <ClaimOverviewCard claim={factualClaim(null)} position={0} checkId="chk" />
    );
    expect(container.textContent).toContain('No orientation available.');
  });

  it('ClaimSectionCard still explains a genuinely missing line', () => {
    const { container } = render(
      <ClaimSectionCard claim={factualClaim(null)} position={0} onExplore={() => {}} />
    );
    expect(container.textContent).toContain('No orientation available.');
  });

  it('a factual claim still renders its prose', () => {
    const prose = 'Of 2 elements examined, retrieved evidence predominantly supports all 2.';
    const { container } = render(
      <ClaimSectionCard claim={factualClaim(prose)} position={0} onExplore={() => {}} />
    );
    expect(container.textContent).toContain('predominantly supports all 2');
  });
});
