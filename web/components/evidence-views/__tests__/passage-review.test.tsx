import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import type { Claim, Evidence } from '@shared/types';
import { ReadingTable } from '../librarian/ReadingTable';
import { PassageReviewNotice } from '../PassageReviewNotice';

it('keeps publication precision and separates capture from effective time', () => {
  const ev = { id: 'source', url: 'https://example.org', publishedDate: '2025',
    textProvenance: { version: 1, captured_at: '2026-09-08T10:00:00Z', passages: [] } } as unknown as Evidence;
  render(<ReadingTable evidence={ev} callNumber="P1" onClose={() => {}} elementDescriptions={[]} />);
  expect(screen.getByText('Publication date: 2025')).toBeTruthy();
  expect(screen.queryByText(/1 Jan 2025/)).toBeNull();
  expect(screen.getByText(/not when the reported facts took effect/)).toBeTruthy();
});

it('discloses a missing publication date without substituting the capture date', () => {
  const ev = { id: 'source', url: 'https://example.org' } as Evidence;
  render(<ReadingTable evidence={ev} callNumber="P1" onClose={() => {}} elementDescriptions={[]} />);
  expect(screen.getByText(/Publication date unavailable/)).toBeTruthy();
});

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

it('shows scope limitations and does not claim a superseded mapping was retained', () => {
  const claim = { claimMap: { metadata: {
    passageReview: { candidate_pairs: 1, assessed_pairs: 1, uninspected_pairs: 0, status: 'needs_review', pairs: [{ element_id: 'e1', evidence_id: 'ev', status: 'conflict', proposed_relationship: 'context' }] },
    scopeReview: { candidate_pairs: 2, assessed_pairs: 1, uninspected_pairs: 1, status: 'needs_review', pairs: [{ element_id: 'e1', evidence_id: 'ev', status: 'scoped', reasoning: 'Different clinical outcome.' }] },
  }, elements: [{ elementId: 'e1', description: 'Prevention' }] }, evidence: [{ evidenceId: 'ev', title: 'Trial' }] } as unknown as Claim;
  const { container } = render(<PassageReviewNotice claim={claim} />);
  expect(container.textContent).toContain('1 relationships remain uninspected');
  expect(container.textContent).toContain('Different clinical outcome.');
  expect(container.textContent).toContain('later scope review retained this source as context');
  expect(container.textContent).not.toContain('The earlier mapping has been retained.');
});
