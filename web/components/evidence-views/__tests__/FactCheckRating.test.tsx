import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { FactCheckRating } from '../FactCheckRating';
import type { Evidence } from '@shared/types';

function ev(overrides: Partial<Evidence>): Evidence {
  return {
    id: '1',
    source: 'PolitiFact',
    url: 'https://politifact.com/x',
    title: 'A fact-check',
    snippet: '...',
    relevanceScore: 0.8,
    ...overrides,
  } as Evidence;
}

describe('FactCheckRating', () => {
  it('renders nothing for a non-fact-check source', () => {
    const { container } = render(<FactCheckRating evidence={ev({ isFactcheck: false })} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders nothing when the rating is missing', () => {
    const { container } = render(
      <FactCheckRating evidence={ev({ isFactcheck: true, factcheckPublisher: 'PolitiFact' })} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders nothing when the publisher is missing', () => {
    const { container } = render(
      <FactCheckRating evidence={ev({ isFactcheck: true, factcheckRating: 'False' })} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders an attributed publisher + rating for a confirmed fact-check', () => {
    const { container } = render(
      <FactCheckRating
        evidence={ev({ isFactcheck: true, factcheckPublisher: 'PolitiFact', factcheckRating: 'False' })}
      />,
    );
    const text = container.textContent || '';
    expect(text).toContain('PolitiFact');
    expect(text).toContain('False');
    // Attribution makes clear it's the publisher's call, not Tru8's.
    expect(text.toLowerCase()).toContain('their assessment');
  });

  it('uses no verdict colour classes (no green/red/amber)', () => {
    const { container } = render(
      <FactCheckRating
        evidence={ev({ isFactcheck: true, factcheckPublisher: 'X', factcheckRating: 'True' })}
      />,
    );
    const html = container.innerHTML;
    expect(html).not.toMatch(/(text|bg)-(green|red|amber|emerald|rose|yellow|orange)/);
  });
});
