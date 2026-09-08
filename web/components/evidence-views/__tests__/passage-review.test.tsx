import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import type { Claim, Evidence } from '@shared/types';
import { ReadingTable } from '../librarian/ReadingTable';
import { PassageReviewNotice } from '../PassageReviewNotice';

it('shows linked quotation under its relationship without certifying the interpretation', () => {
  const citation = { passage_id: 'p', quote: 'BUSY can occur.', start: 0, end: 15, extraction_sha256: 'hash' };
  const ev = { id: 'source', url: 'https://example.org', textProvenance: { version: 1, extraction_sha256: 'hash',
    passages: [{ id: 'p', start: 0, end: 15, text: 'BUSY can occur.' }] }} as Evidence;
  render(<ReadingTable evidence={ev} callNumber="P1" onClose={() => {}} elementDescriptions={[
    { elementId: 'e1', description: 'BUSY never occurs', relationship: 'challenges', citations: [citation] },
  ]} />);
  expect(screen.getByText(/relationship remains a system interpretation/)).toBeTruthy();
  expect(screen.queryByText('An exact supporting passage is not available in this record.')).toBeNull();
});

it('keeps uninspected pairs and conflicting interpretations visible', () => {
  const claim = { claimMap: { metadata: { passageReview: { candidate_pairs: 14, assessed_pairs: 10, uninspected_pairs: 4,
    status: 'needs_review', pairs: [{ element_id: 'e1', evidence_id: 'ev', status: 'conflict', proposed_relationship: 'challenges' }] } },
    elements: [{ elementId: 'e1', description: 'No exceptions' }] }, evidence: [{ evidenceId: 'ev', title: 'Documentation' }] } as Claim;
  const { container } = render(<PassageReviewNotice claim={claim} />);
  expect(container.textContent).toContain('4 eligible pairs remain uninspected');
  expect(container.textContent).toContain('conflicting with the earlier mapping');
});
