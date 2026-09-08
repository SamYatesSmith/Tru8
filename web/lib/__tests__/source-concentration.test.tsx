import { expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { Claim } from '@shared/types';
import { PassageReviewNotice } from '@/components/evidence-views/PassageReviewNotice';

it('explains repeated publishers without presenting them as independent sources', () => {
  const claim = { claimMap: { metadata: { sourceConcentration: {
    basis: 'mapped_documents_by_domain', mapped_documents: 5,
    domains: [{ domain: 'docs.example', documents: 4 }, { domain: 'other.example', documents: 1 }],
    independence: 'not_established',
  } } } } as Claim;
  render(<PassageReviewNotice claim={claim} />);
  expect(screen.getByText(/4 mapped documents from docs.example/)).toBeTruthy();
  expect(screen.getByText(/not necessarily independent evidence/)).toBeTruthy();
});

it('does not invent concentration information for historical records', () => {
  const { container } = render(<PassageReviewNotice claim={{ claimMap: { metadata: {} } } as Claim} />);
  expect(container.textContent).toBe('');
});
