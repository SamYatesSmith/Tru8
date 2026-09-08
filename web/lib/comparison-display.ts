import type { Comparison } from '@shared/types';

/** Keep the cache canonical while presenting every side-specific field in slot order. */
export function comparisonInDisplayOrder(comparison: Comparison, evidenceA: string): Comparison {
  if (comparison.evidenceA === evidenceA || comparison.evidenceB !== evidenceA) return comparison;
  return {
    ...comparison,
    evidenceA: comparison.evidenceB,
    evidenceB: comparison.evidenceA,
    summaryA: comparison.summaryB,
    summaryB: comparison.summaryA,
    basisA: comparison.basisB,
    basisB: comparison.basisA,
    wordsA: comparison.wordsB,
    wordsB: comparison.wordsA,
    collisions: comparison.collisions.map(row => ({
      ...row,
      a: row.b,
      b: row.a,
      verdict: row.verdict === 'only_a' ? 'only_b' : row.verdict === 'only_b' ? 'only_a' : row.verdict,
    })),
  };
}
