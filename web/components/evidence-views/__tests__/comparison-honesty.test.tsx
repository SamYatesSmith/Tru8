import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import type { Comparison, CollisionRow } from '@shared/types';
import { comparisonInDisplayOrder } from '@/lib/comparison-display';
import { ComparisonResult } from '../compare/ComparisonResult';
import { CollisionTable } from '../compare/CollisionTable';

const comparison: Comparison = {
  id: 'pair', evidenceA: 'a', evidenceB: 'b', summaryA: 'Alpha summary', summaryB: 'Beta summary',
  divergence: 'The sources differ.', basisA: 'full', basisB: 'stored', wordsA: 321, wordsB: null,
  createdAt: null, collisions: [{ elementId: 'e1', a: 'supports', b: null, verdict: 'only_a' }],
};

describe('comparison fidelity', () => {
  it('keeps summaries, receipts and one-sided mappings with the selected source after reversal', () => {
    const displayed = comparisonInDisplayOrder(comparison, 'b');
    expect(displayed.evidenceA).toBe('b');
    expect(displayed.summaryA).toBe('Beta summary');
    expect(displayed.basisA).toBe('stored');
    expect(displayed.wordsA).toBeNull();
    expect(displayed.collisions[0]).toMatchObject({ a: null, b: 'supports', verdict: 'only_b' });
    expect(comparisonInDisplayOrder(displayed, 'a')).toEqual(comparison);
    const { container } = render(<ComparisonResult comparison={displayed} domainA="beta.test" domainB="alpha.test" />);
    expect(container.textContent).toContain('saved evidence mappings');
    expect(container.textContent).not.toContain('full article');
    expect(comparison.evidenceA).toBe('a');
  });

  it.each(['supports', 'challenges', 'context'] as const)('does not imply agreement when context meets %s, including an old API response', relationship => {
    const rows: CollisionRow[] = [{ elementId: 'e1', a: 'context', b: relationship, verdict: 'aligned' }];
    const { container } = render(<CollisionTable rows={rows} domainA="a" domainB="b" />);
    expect(container.textContent).not.toContain('ALIGNED');
    expect(container.textContent).not.toContain('SAME DIRECTION');
    expect(container.textContent).toContain(relationship === 'context' ? 'BOTH CONTEXT' : 'CONTEXT INVOLVED');
  });
});
