import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import type { Evidence } from '@shared/types';
import { TemporalDetails } from '../TemporalDetails';
import { ReadingTable } from '../librarian/ReadingTable';

function evidence(): Evidence {
  return { id: 'source', url: 'https://example.org', publishedDate: '2025-01-01',
    textProvenance: { version: 1, extraction_sha256: 'hash', passages: [
      { id: 'p', start: 0, end: 44, text: 'Old rate effective from 8 May 2025. Superseded.' },
    ], temporal: { version: 1, publication: { supplied_value: '2025', representation: 'supplied_string', precision: 'year' },
      applicability_status: 'unestablished', scan_scope: 'retained_passages', candidate_count: 1, unretained_candidates: 0,
      statements: [{ kind: 'effective_start', stated_date: '2025-05-08', review_status: 'unreviewed',
        citation: { passage_id: 'p', quote: 'effective from 8 May 2025', start: 9, end: 34, extraction_sha256: 'hash' } }],
    } } } as unknown as Evidence;
}

it('shows original publication precision after storage normalised it', () => {
  render(<ReadingTable evidence={evidence()} callNumber="P1" onClose={() => {}} elementDescriptions={[]} />);
  expect(screen.getByText('Publication date: 2025')).toBeTruthy();
  expect(screen.queryByText(/Publication date: 1 Jan/)).toBeNull();
});

it('keeps effective-date candidates unreviewed with surrounding context', () => {
  render(<TemporalDetails evidence={evidence()} />);
  expect(screen.getByText(/Applicability to this claim is unestablished/)).toBeTruthy();
  expect(screen.getByText(/2025-05-08 · Unreviewed/)).toBeTruthy();
  expect(screen.getByText('Old rate effective from 8 May 2025. Superseded.')).toBeTruthy();
});

it('does not show a date as grounded when the captured version differs', () => {
  const ev = evidence();
  ev.textProvenance!.extraction_sha256 = 'changed';
  render(<TemporalDetails evidence={ev} />);
  expect(screen.getByText(/captured passage for this date statement is unavailable/)).toBeTruthy();
  expect(screen.queryByText(/2025-05-08/)).toBeNull();
});

it('does not backfill temporal claims for legacy records', () => {
  const { container } = render(<TemporalDetails evidence={{ id: 'old' } as Evidence} />);
  expect(container.textContent).toBe('');
});
