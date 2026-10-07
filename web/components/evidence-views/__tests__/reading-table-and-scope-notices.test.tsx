import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import type { Claim, Evidence } from '@shared/types';
import { ReadingTable } from '../librarian/ReadingTable';
import { SourceScopeNotices } from '../SourceScopeNotices';

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

it('states that no exact passage backs a relationship', () => {
  const ev = { id: 'source', url: 'https://example.org' } as Evidence;
  render(<ReadingTable evidence={ev} callNumber="P1" onClose={() => {}} elementDescriptions={[
    { elementId: 'e1', description: 'BUSY never occurs', relationship: 'challenges' },
  ]} />);
  expect(screen.getByText('An exact supporting passage is not available in this record.')).toBeTruthy();
});

it('shows scope-review limitations and the sources retained as context', () => {
  const claim = { claimMap: { metadata: {
    scopeReview: { candidate_pairs: 2, assessed_pairs: 1, uninspected_pairs: 1, status: 'needs_review', pairs: [{ element_id: 'e1', evidence_id: 'ev', status: 'scoped', reasoning: 'Different clinical outcome.' }] },
  }, elements: [{ elementId: 'e1', description: 'Prevention' }] }, evidence: [{ evidenceId: 'ev', title: 'Trial' }] } as unknown as Claim;
  const { container } = render(<SourceScopeNotices claim={claim} />);
  expect(container.textContent).toContain('1 relationships remain uninspected');
  expect(container.textContent).toContain('Retained as context: Trial.');
  expect(container.textContent).toContain('Different clinical outcome.');
});
