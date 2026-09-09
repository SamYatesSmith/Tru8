import { describe, expect, it } from 'vitest';
import { interpretationNote, MISSING_NOTE, WITHHELD_NOTE } from '../system-interpretation';

/**
 * "System interpretation" is model-written free text (per-reference
 * `reasoning`, scope-review `reasoning`) rendered on the public record since
 * the 2026-09 evidence-quality work. It shares the Fix 1 verdict test: the
 * public page fails closed, the owner's dashboard shows the sentence as saved.
 */
const LIMITS = [
  'The documentation describes BUSY exceptions in section 9.',
  'The source studies progression in diagnosed patients, not prevention of onset.',
  'Reports the composite endpoint; the excerpt does not state the 20% figure.',
];
const ADJUDICATIONS = [
  'The evidence consistently refutes this element.',
  'This source proves the claim is correct.',
  'Strong evidence confirms the stated reduction.',
  'The article is a fact-check that debunks the figure.',
];

describe('interpretationNote', () => {
  it('shows genuine limits on both surfaces', () => {
    for (const text of LIMITS) {
      expect(interpretationNote(text, true)).toBe(text);
      expect(interpretationNote(text, false)).toBe(text);
    }
  });
  it('withholds adjudicating wording on the public record only, and says so', () => {
    for (const text of ADJUDICATIONS) {
      expect(interpretationNote(text, true)).toBe(WITHHELD_NOTE);
      expect(interpretationNote(text, false)).toBe(text);
    }
  });
  it('never presents a withheld sentence as a missing one', () => {
    expect(WITHHELD_NOTE).not.toBe(MISSING_NOTE);
    expect(interpretationNote('', true)).toBe(MISSING_NOTE);
    expect(interpretationNote(undefined, true)).toBe(MISSING_NOTE);
    expect(interpretationNote('  null ', false)).toBe('null');
  });
});
