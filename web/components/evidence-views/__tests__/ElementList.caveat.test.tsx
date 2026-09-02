import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';

vi.mock('@/lib/analytics', () => ({ capture: vi.fn() }));
vi.mock('next/navigation', () => ({ useRouter: () => ({ push: vi.fn() }) }));

import { ElementList } from '../ElementList';
import type { ClaimElement } from '@shared/types';

/**
 * Fix 1 (2026-09-02) — the roster shows the mapper's caveat sentence, gated.
 * Design: audit/2026-09-02_fix1_element_caveat_render_design.md
 *
 * Three pins:
 *   1. A genuine limit on a SUPPORTED element renders as a grey NOTE row
 *      (the four send-week notes had to say "PDF-only" because it did not).
 *   2. An adjudication ("consistently refutes") renders NOTHING — verdict
 *      language must never reach a public page, whatever the PDF prints.
 *   3. A gap row (no evidence) never shows a note, even if the field is set.
 */
function element(overrides: Partial<ClaimElement>): ClaimElement {
  return {
    elementId: 'e1',
    description: 'The £22 million figure was the first-year outturn.',
    state: 'supported',
    uncertainty: null,
    evidenceRefs: [{ evidenceId: 'ev-1', relationship: 'supports', reasoning: 'x' }],
    basis: null,
    ...overrides,
  } as ClaimElement;
}

describe('ElementList — element caveat row', () => {
  it('renders a genuine limit as a grey NOTE row, verbatim', () => {
    const text = 'The £22 million figure is an estimated loss, not official outturn data.';
    const { getByTestId } = render(<ElementList elements={[element({ uncertainty: text })]} />);
    const note = getByTestId('element-caveat');
    expect(note.textContent).toContain(text);
    expect(note.textContent).toMatch(/^Note/);
    expect(note.getAttribute('title')).toBe(text);
    // No-verdict colour lock: grey only.
    expect(note.className).toContain('text-zinc-500');
    expect(note.className).not.toMatch(/amber|red|green|emerald|rose/);
  });

  it('renders nothing for an adjudication that restates the badge', () => {
    const { queryByTestId } = render(
      <ElementList
        elements={[
          element({
            elementId: 'e3',
            state: 'disputed',
            uncertainty:
              'The evidence consistently refutes this element, demonstrating greenhouse gas-induced climate change is the primary driver.',
          }),
        ]}
      />,
    );
    expect(queryByTestId('element-caveat')).toBeNull();
  });

  it('never shows a note on a gap row', () => {
    const { queryByTestId } = render(
      <ElementList
        elements={[element({ evidenceRefs: [], uncertainty: 'No evidence was retrieved for this element.' })]}
      />,
    );
    expect(queryByTestId('element-caveat')).toBeNull();
  });
});
