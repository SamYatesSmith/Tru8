import { describe, it, expect } from 'vitest';
import { computeDiagnosticValues } from '../diagnostic-value';
import type { Claim, EvidenceRelationship } from '@tru8/shared/types';

// Minimal claim builder matching the Claim interface.
// Returning Claim explicitly so call sites pass the type check; without
// the annotation TS infers a structural literal which doesn't satisfy
// Claim (claimMap optional fields, evidenceRefs strictly typed).
function makeClaim(elements: Array<{
  elementId: string;
  evidenceRefs: Array<{ evidenceId: string; relationship: EvidenceRelationship }>;
}>): Claim {
  return {
    id: 'claim-1',
    checkId: 'check-1',
    text: 'Test claim',
    evidence: [],
    position: 1,
    claimMap: {
      claimId: 'claim-1',
      normalisedClaim: 'Test claim',
      claimType: 'empirical',
      elements: elements.map((e) => ({
        ...e,
        description: 'Element text',
        state: 'unresolved',
        uncertainty: null,
      })),
      orientation: 'Test orientation',
      metadata: {
        decompositionModel: 'test-model',
        mappingModel: 'test-model',
        elementCount: elements.length,
        completedAt: null,
      },
    },
  };
}

describe('computeDiagnosticValues', () => {
  it('returns empty result for no claims', () => {
    const result = computeDiagnosticValues([]);
    expect(result.values.size).toBe(0);
    expect(result.highCount).toBe(0);
    expect(result.totalCount).toBe(0);
    expect(result.hasDiagnosticVariance).toBe(false);
  });

  it('returns empty result for claims without claimMap', () => {
    const claim = { id: 'c1', checkId: 'ch1', text: 'test', evidence: [], position: 1 };
    const result = computeDiagnosticValues([claim as any]);
    expect(result.values.size).toBe(0);
  });

  it('assigns 1.0 to evidence that both supports and challenges', () => {
    const claim = makeClaim([
      {
        elementId: 'e1',
        evidenceRefs: [{ evidenceId: 'ev1', relationship: 'supports' }],
      },
      {
        elementId: 'e2',
        evidenceRefs: [{ evidenceId: 'ev1', relationship: 'challenges' }],
      },
    ]);

    const result = computeDiagnosticValues([claim]);
    expect(result.values.get('ev1')).toBe(1.0);
    expect(result.highCount).toBe(1);
    expect(result.hasDiagnosticVariance).toBe(true);
  });

  it('assigns 0.6 to evidence linked to one element with directional relationship', () => {
    const claim = makeClaim([
      {
        elementId: 'e1',
        evidenceRefs: [{ evidenceId: 'ev1', relationship: 'supports' }],
      },
    ]);

    const result = computeDiagnosticValues([claim]);
    expect(result.values.get('ev1')).toBe(0.6);
    expect(result.highCount).toBe(0); // 0.6 < 0.7
  });

  it('assigns 0.1 to context-only evidence', () => {
    const claim = makeClaim([
      {
        elementId: 'e1',
        evidenceRefs: [{ evidenceId: 'ev1', relationship: 'context' }],
      },
      {
        elementId: 'e2',
        evidenceRefs: [{ evidenceId: 'ev1', relationship: 'context' }],
      },
    ]);

    const result = computeDiagnosticValues([claim]);
    expect(result.values.get('ev1')).toBe(0.1);
  });

  it('assigns 0.2 to evidence with same relationship across multiple elements', () => {
    const claim = makeClaim([
      {
        elementId: 'e1',
        evidenceRefs: [{ evidenceId: 'ev1', relationship: 'supports' }],
      },
      {
        elementId: 'e2',
        evidenceRefs: [{ evidenceId: 'ev1', relationship: 'supports' }],
      },
    ]);

    const result = computeDiagnosticValues([claim]);
    expect(result.values.get('ev1')).toBe(0.2);
  });

  it('tracks hasDiagnosticVariance correctly', () => {
    // No challenges → false
    const claimNoChallenge = makeClaim([
      {
        elementId: 'e1',
        evidenceRefs: [{ evidenceId: 'ev1', relationship: 'supports' }],
      },
    ]);
    expect(computeDiagnosticValues([claimNoChallenge]).hasDiagnosticVariance).toBe(false);

    // With challenges → true
    const claimWithChallenge = makeClaim([
      {
        elementId: 'e1',
        evidenceRefs: [{ evidenceId: 'ev1', relationship: 'challenges' }],
      },
    ]);
    expect(computeDiagnosticValues([claimWithChallenge]).hasDiagnosticVariance).toBe(true);
  });

  it('handles multiple claims and deduplicates evidence across them', () => {
    const claim1 = makeClaim([
      {
        elementId: 'e1',
        evidenceRefs: [{ evidenceId: 'ev-shared', relationship: 'supports' }],
      },
    ]);
    const claim2 = makeClaim([
      {
        elementId: 'e2',
        evidenceRefs: [
          { evidenceId: 'ev-shared', relationship: 'challenges' },
          { evidenceId: 'ev-unique', relationship: 'supports' },
        ],
      },
    ]);

    const result = computeDiagnosticValues([claim1, claim2]);
    expect(result.values.get('ev-shared')).toBe(1.0); // supports + challenges
    expect(result.values.get('ev-unique')).toBe(0.6); // single directional
    expect(result.totalCount).toBe(2);
  });
});
