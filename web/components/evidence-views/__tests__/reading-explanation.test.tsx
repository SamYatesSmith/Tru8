import { render } from '@testing-library/react';
import { expect, it } from 'vitest';
import type { Evidence } from '@shared/types';
import { ReadingTable } from '../librarian/ReadingTable';

it('shows the relationship and interpretation, without presenting a paraphrase as a quotation', () => {
  const { container } = render(<ReadingTable evidence={{ id: 'ev', title: 'SQLite documentation', url: 'https://sqlite.org' } as Evidence}
    callNumber="P·DATA·01" onClose={() => {}}
    elementDescriptions={[{ elementId: 'e2', description: 'BUSY cannot occur', relationship: 'challenges', reasoning: 'The documentation describes BUSY exceptions.' }]} />);
  expect(container.textContent).toContain('challenges');
  expect(container.textContent).toContain('System interpretation: The documentation describes BUSY exceptions.');
  expect(container.textContent).toContain('exact supporting passage is not available');
  expect(container.querySelector('blockquote')).toBeNull();
  expect(document.activeElement).toHaveAttribute('aria-label', 'Source details');
});

it('withholds adjudicating interpretation on the public record but not from the owner', () => {
  const verdict = 'The evidence consistently refutes this element.';
  const descriptions = [{ elementId: 'e1', description: 'Rate is 3.75%', relationship: 'challenges' as const, reasoning: verdict }];
  const ev = { id: 'ev', title: 'Source', url: 'https://example.org' } as Evidence;
  const pub = render(<ReadingTable evidence={ev} callNumber="P1" onClose={() => {}} elementDescriptions={descriptions} readOnly />);
  expect(pub.container.textContent).not.toContain(verdict);
  expect(pub.container.textContent).toContain('withheld from the public record');
  expect(pub.container.textContent).not.toContain('No relationship explanation was saved');
  pub.unmount();
  const owner = render(<ReadingTable evidence={ev} callNumber="P1" onClose={() => {}} elementDescriptions={descriptions} />);
  expect(owner.container.textContent).toContain(`System interpretation: ${verdict}`);
});

it('quotes only captured excerpts and keeps generated facts separate', () => {
  const evidence = { id: 'ev', title: 'Source', url: 'https://example.org', textProvenance: {
    version: 1, capture_kind: 'extracted_text', captured_at: '2026-09-08T12:00:00Z',
    extraction_sha256: 'abc', extraction_characters: 2000, retained_characters: 25,
    original_snippet: 'Original search snippet', derived_text: 'Generated interpretation',
    passages: [{ id: 'p1', start: 1800, end: 1825, text: 'SQLite can return BUSY.', matched_element_ids: ['e1'] }],
  }} as Evidence;
  const { container } = render(<ReadingTable evidence={evidence} callNumber="P·DATA·01" onClose={() => {}} elementDescriptions={[]} />);
  expect(container.querySelector('blockquote')?.textContent).toBe('SQLite can return BUSY.');
  expect(container.textContent).toContain('Model-generated facts — not quotations');
  expect(container.textContent).toContain('They have not been linked to the relationships above.');
});
