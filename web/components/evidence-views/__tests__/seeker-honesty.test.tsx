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

  it('does not count empty evidence twice or treat a missing state as resolved', () => {
    expect(evidenceCoverage([element('unresolved'), element('', 'supports')])).toEqual({
      gaps: 1, needsReview: 1, coverage: 50, withEvidence: 1,
    });
    expect(evidenceCoverage([]).coverage).toBe(0);
  });
});
