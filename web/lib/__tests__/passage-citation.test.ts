import { expect, it } from 'vitest';
import type { Evidence, PassageCitation } from '@shared/types';
import { citationText } from '../passage-citation';

const evidence = { textProvenance: { version: 1, extraction_sha256: 'version', passages: [
  { id: 'p', start: 100, end: 108, text: '🙂 café x' },
] }} as Evidence;
const citation: PassageCitation = { passage_id: 'p', quote: 'café', start: 102, end: 106, extraction_sha256: 'version' };

it('uses Unicode offsets and requires the exact stored text and version', () => {
  expect(citationText(evidence, citation)).toBe('café');
  expect(citationText(evidence, { ...citation, extraction_sha256: 'older' })).toBeNull();
  expect(citationText(evidence, { ...citation, quote: 'cafe' })).toBeNull();
  expect(citationText(evidence, { ...citation, passage_id: 'different' })).toBeNull();
  expect(citationText(evidence, { ...citation, start: 101 })).toBeNull();
});
