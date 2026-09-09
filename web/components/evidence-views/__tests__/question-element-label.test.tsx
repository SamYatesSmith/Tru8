import { render } from '@testing-library/react';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { QUESTION_STATE_LABELS, isQuestionElement } from '@shared/constants';
import { ElementStateBadge } from '../ElementStateBadge';

/**
 * Astra finding 8 (2026-09-07), still present on the 2026-09-09 regrade: the EV
 * claim's grounds elements are open questions ("What do lifecycle analyses
 * indicate …?") and read "+ Supported". A question cannot be supported; evidence
 * addresses it. The enum, styling and arithmetic are untouched — only the word.
 */
describe('question-shaped elements read Addressed, not Supported', () => {
  const question = 'What do lifecycle analyses indicate about electric cars compared to petrol cars?';
  const assertion = 'Electric cars emit less carbon over their lifecycle than petrol cars.';

  it('detects a question by its interrogative form only', () => {
    expect(isQuestionElement(question)).toBe(true);
    expect(isQuestionElement(question + '  ')).toBe(true);
    expect(isQuestionElement(assertion)).toBe(false);
    expect(isQuestionElement(undefined)).toBe(false);
  });

  it.each([
    ['supported', 'Addressed'],
    ['disputed', 'Contested'],
    ['contextual', 'Context only'],
    ['unresolved', 'Open'],
  ] as const)('renders %s as %s for a question, unchanged for an assertion', (state, word) => {
    const q = render(<ElementStateBadge state={state} description={question} />);
    expect(q.container.textContent).toContain(word);
    expect(q.container.textContent?.toLowerCase()).not.toContain('supported');
    q.unmount();
    const a = render(<ElementStateBadge state={state} description={assertion} />);
    expect(a.container.textContent).not.toContain(word);
  });

  it('an explicit label such as Gap still wins', () => {
    const { container } = render(<ElementStateBadge state="unresolved" label="Gap" description={question} />);
    expect(container.textContent).toContain('Gap');
    expect(container.textContent).not.toContain('Open');
  });

  it('is parity-locked with the PDF label table in backend checks.py', () => {
    const py = readFileSync(resolve(__dirname, '../../../../backend/app/api/v1/checks.py'), 'utf-8');
    const block = py.slice(py.indexOf('QUESTION_STATE_LABELS = {'), py.indexOf('}', py.indexOf('QUESTION_STATE_LABELS = {')));
    for (const [state, word] of Object.entries(QUESTION_STATE_LABELS)) {
      expect(block).toContain(`"${state}": "${word}"`);
    }
  });
});
