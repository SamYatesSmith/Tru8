import { describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/react';
import type { Claim, ClaimElement } from '@shared/types';
import { evidenceCoverage } from '@/lib/evidence-coverage';

vi.mock('@/lib/api', () => ({ apiClient: {} }));
vi.mock('@/lib/analytics', () => ({ capture: vi.fn() }));
vi.mock('../seeker/BountyField', () => ({ BountyField: () => null }));
vi.mock('../seeker/ResearchButton', () => ({ ResearchButton: () => null }));
import { SeekerView } from '../seeker/SeekerView';

function element(state: string, relationship?: string): ClaimElement {
  return {
    elementId: state, description: `${state} question`, state,
    evidenceRefs: relationship ? [{ evidenceId: 'source', relationship }] : [],
  } as ClaimElement;
}

describe('evidence presence is not resolution', () => {
  it('keeps the Sweden causal uncertainty and disputed ranking visible at 100% coverage', () => {
    const elements = [element('supported', 'supports'), element('contextual', 'context'), element('disputed', 'challenges')];
    expect(evidenceCoverage(elements)).toEqual({ gaps: 0, needsReview: 2, coverage: 100, withEvidence: 3 });
    const claim = { claimMap: { elements }, evidence: [] } as unknown as Claim;
    const { container } = render(<SeekerView claim={claim} readOnly />);
    expect(container.textContent).toContain('contextual question');
    expect(container.textContent).toContain('disputed question');
    expect(container.textContent).not.toContain('settled');
    expect(container.textContent).not.toContain('Resolved Elements');
  });

  it('treats a passage review that never ran as no unknowns, and one that did not finish as unknowns', () => {
    const settled = [element('supported', 'supports')];
    const notRun = { claimMap: { elements: settled, metadata: { passageReview: { status: 'not_run', candidate_pairs: 0, assessed_pairs: 0, uninspected_pairs: 0, pairs: [] } } }, evidence: [] } as unknown as Claim;
    const needsReview = { claimMap: { elements: settled, metadata: { passageReview: { status: 'needs_review', candidate_pairs: 2, assessed_pairs: 1, uninspected_pairs: 1, pairs: [] } } }, evidence: [] } as unknown as Claim;
    // readOnly keeps the explore fetch off; the notice copy is the observable.
    expect(render(<SeekerView claim={notRun} readOnly />).container.textContent).not.toContain('did not finish');
    expect(render(<SeekerView claim={needsReview} readOnly />).container.textContent).toContain('1 eligible pairs remain uninspected');
  });

  it('does not count empty evidence twice or treat a missing state as resolved', () => {
    expect(evidenceCoverage([element('unresolved'), element('', 'supports')])).toEqual({
      gaps: 1, needsReview: 1, coverage: 50, withEvidence: 1,
    });
    expect(evidenceCoverage([]).coverage).toBe(0);
  });
});
