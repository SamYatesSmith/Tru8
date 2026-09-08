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
