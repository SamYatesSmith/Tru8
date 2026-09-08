import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import type { Claim } from '@shared/types';
import { PassageReviewNotice } from '../PassageReviewNotice';

it('shows date exclusions even when passage review did not run', () => {
  const claim = { claimMap: { elements: [{ elementId: 'e1', description: 'Historical setting',
    evidenceRefs: [{ evidenceId: 'ev', relationship: 'context' }],
    basis: { fact_applicability: { target_day: '2031-04-12', scan_scope: 'retained_passages', scoped_count: 1,
      scoped: [{ evidence_id: 'ev', was: 'supports', target_day: '2031-04-12', reason: 'Unestablished' }] } } }] },
    evidence: [{ evidenceId: 'ev', title: 'Operational record' }] } as unknown as Claim;
  render(<PassageReviewNotice claim={claim} />);
  expect(screen.getByRole('region', { name: 'Fact date applicability' })).toBeTruthy();
  expect(screen.getByText(/Operational record: applicability on 2031-04-12 is unestablished/)).toBeTruthy();
  expect(screen.getByText(/does not mean the fact is false/)).toBeTruthy();
});

it('does not invent a date-applicability receipt for an older report', () => {
  const { container } = render(<PassageReviewNotice claim={{ claimMap: { elements: [] } } as unknown as Claim} />);
  expect(container.textContent).toBe('');
});

it('does not present an earlier exclusion as current after a relationship changes', () => {
  const claim = { claimMap: { elements: [{ elementId: 'e1',
    evidenceRefs: [{ evidenceId: 'ev', relationship: 'supports' }],
    basis: { fact_applicability: { scoped: [{ evidence_id: 'ev' }] } },
  }] } } as unknown as Claim;
  const { container } = render(<PassageReviewNotice claim={claim} />);
  expect(container.textContent).toBe('');
});
