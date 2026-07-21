import { describe, it, expect } from 'vitest';
import { evidenceQualityNote, elementIsThin, thinElementCount } from '../support-structure';
import type { ClaimElement, ElementBasis, ElementState, EvidenceSideStructure } from '@shared/types';

function side(p: Partial<EvidenceSideStructure>): EvidenceSideStructure {
  return {
    count: 0,
    distinct_domains: 0,
    tier_counts: { primary: 0, reporting: 0, commentary: 0 },
    derivation: { originals: 0, derivative_count: 0 },
    ...p,
  };
}

describe('evidenceQualityNote', () => {
  it('returns null for missing / empty sides', () => {
    expect(evidenceQualityNote(undefined)).toBeNull();
    expect(evidenceQualityNote(null)).toBeNull();
    expect(evidenceQualityNote(side({ count: 0 }))).toBeNull();
  });

  it('flags ECHO when breadth re-reports one original', () => {
    const note = evidenceQualityNote(
      side({
        count: 3,
        distinct_domains: 3,
        tier_counts: { primary: 1, reporting: 2, commentary: 0 },
        derivation: { originals: 1, derivative_count: 2 },
      }),
    );
    expect(note?.kind).toBe('echo');
    expect(note?.label).toBe('Mostly one source repeated');
  });

  it('flags THIN when only commentary-grade sources', () => {
    const note = evidenceQualityNote(
      side({
        count: 4,
        distinct_domains: 2,
        tier_counts: { primary: 0, reporting: 0, commentary: 4 },
      }),
    );
    expect(note?.kind).toBe('thin');
    expect(note?.label).toBe('Thin sourcing');
  });

  it('flags THIN when several items all from one website', () => {
    const note = evidenceQualityNote(
      side({
        count: 3,
        distinct_domains: 1,
        tier_counts: { primary: 0, reporting: 3, commentary: 0 },
      }),
    );
    expect(note?.kind).toBe('thin');
  });

  it('returns null for healthy support (several independent good sources)', () => {
    const note = evidenceQualityNote(
      side({
        count: 3,
        distinct_domains: 3,
        tier_counts: { primary: 1, reporting: 2, commentary: 0 },
        derivation: { originals: 0, derivative_count: 0 },
      }),
    );
    expect(note).toBeNull();
  });

  it('does not flag a single primary/reporting source as thin', () => {
    const note = evidenceQualityNote(
      side({
        count: 1,
        distinct_domains: 1,
        tier_counts: { primary: 1, reporting: 0, commentary: 0 },
      }),
    );
    // singleOutlet needs count>=2; one good source is not "thin".
    expect(note).toBeNull();
  });

  it('classifies a side missing distinct_domains as single-outlet thin (parity)', () => {
    // distinct_domains absent -> (s.distinct_domains || 0) -> 0 -> single-outlet,
    // matching the backend `... or 0`. Real data always includes it (the type
    // forbids omission); this locks the two ports on malformed/legacy payloads.
    const partial = {
      count: 3,
      tier_counts: { primary: 0, reporting: 3, commentary: 0 },
      derivation: { originals: 0, derivative_count: 0 },
    } as unknown as EvidenceSideStructure;
    expect(evidenceQualityNote(partial)?.kind).toBe('thin');
  });

  it('reads a publisher-platform single outlet differently from a lone website', () => {
    // Parity twin: backend test_thin_support.py::test_portfolio_single_outlet_note_wording
    const portfolio = evidenceQualityNote(
      side({
        count: 3,
        distinct_domains: 1,
        sole_domain: 'nature.com',
        tier_counts: { primary: 0, reporting: 3, commentary: 0 },
      }),
    );
    expect(portfolio?.detail).toBe(
      'All via a single publisher platform, which may host multiple journals.',
    );

    const plain = evidenceQualityNote(
      side({
        count: 3,
        distinct_domains: 1,
        sole_domain: 'example.com',
        tier_counts: { primary: 0, reporting: 3, commentary: 0 },
      }),
    );
    expect(plain?.detail).toBe('All from a single website.');
  });

  it('does not throw on a side missing the derivation object', () => {
    // Defensive: real pipeline data always includes derivation, but a
    // truncated/legacy payload must not crash the render.
    const partial = {
      count: 4,
      distinct_domains: 2,
      tier_counts: { primary: 0, reporting: 0, commentary: 4 },
    } as unknown as EvidenceSideStructure;
    expect(() => evidenceQualityNote(partial)).not.toThrow();
    expect(evidenceQualityNote(partial)?.kind).toBe('thin');
  });

  it('echo takes priority over thin', () => {
    const note = evidenceQualityNote(
      side({
        count: 3,
        distinct_domains: 1,
        tier_counts: { primary: 1, reporting: 0, commentary: 2 },
        derivation: { originals: 1, derivative_count: 2 },
      }),
    );
    expect(note?.kind).toBe('echo');
  });

  it('flags REPETITION — same wording, >=3 on side, >=2 domains, no primary (F4)', () => {
    const note = evidenceQualityNote(
      side({
        count: 3,
        distinct_domains: 3,
        tier_counts: { primary: 0, reporting: 2, commentary: 1 },
        repetition: { max_cluster_on_side: 3, distinct_domains: 3 },
      }),
    );
    expect(note?.kind).toBe('repetition');
    expect(note?.label).toBe('Same wording, no primary');
  });

  it('suppresses REPETITION when the side has its own primary', () => {
    const note = evidenceQualityNote(
      side({
        count: 4,
        distinct_domains: 3,
        tier_counts: { primary: 1, reporting: 2, commentary: 1 },
        repetition: { max_cluster_on_side: 3, distinct_domains: 3 },
      }),
    );
    // No echo/thin either → null.
    expect(note).toBeNull();
  });

  it('does not flag REPETITION below the on-side threshold (2 < 3)', () => {
    const note = evidenceQualityNote(
      side({
        count: 3,
        distinct_domains: 2,
        tier_counts: { primary: 0, reporting: 2, commentary: 1 },
        repetition: { max_cluster_on_side: 2, distinct_domains: 2 },
      }),
    );
    expect(note).toBeNull();
  });

  it('repetition takes priority over thin (commentary-only side that also repeats)', () => {
    const note = evidenceQualityNote(
      side({
        count: 3,
        distinct_domains: 3,
        tier_counts: { primary: 0, reporting: 0, commentary: 3 },
        repetition: { max_cluster_on_side: 3, distinct_domains: 3 },
      }),
    );
    expect(note?.kind).toBe('repetition');
  });
});

// Mirrors backend tests/unit/pipeline/test_thin_support.py::element_is_thin so
// the digest trigger and the `research-thin` endpoint agree on "thin".
function elem(
  refCount: number,
  state: ElementState | null,
  basis?: ElementBasis,
): ClaimElement {
  return {
    elementId: 'e1',
    description: 'd',
    evidenceRefs: Array.from({ length: refCount }, (_, i) => ({
      evidenceId: `x${i}`,
      relationship: 'supports' as const,
    })),
    state,
    uncertainty: null,
    ...(basis ? { basis } : {}),
  };
}

const HEALTHY_BASIS: ElementBasis = {
  support_structure: side({
    count: 3,
    distinct_domains: 3,
    tier_counts: { primary: 1, reporting: 2, commentary: 0 },
  }),
  challenge_structure: side({ count: 0 }),
};

const THIN_BASIS: ElementBasis = {
  support_structure: side({
    count: 4,
    distinct_domains: 1,
    tier_counts: { primary: 0, reporting: 0, commentary: 4 },
  }),
  challenge_structure: side({ count: 0 }),
};

const REPETITION_BASIS: ElementBasis = {
  support_structure: side({
    count: 4,
    distinct_domains: 3,
    tier_counts: { primary: 0, reporting: 3, commentary: 1 },
    repetition: { max_cluster_on_side: 3, distinct_domains: 3 },
  }),
  challenge_structure: side({ count: 0 }),
};

describe('elementIsThin', () => {
  it('excludes a gap (no mapped sources)', () => {
    expect(elementIsThin(elem(0, 'unresolved'))).toBe(false);
  });

  it('excludes disputed even with few refs', () => {
    expect(elementIsThin(elem(2, 'disputed'))).toBe(false);
  });

  it('flags few refs (<=2)', () => {
    expect(elementIsThin(elem(2, 'supported'))).toBe(true);
    expect(elementIsThin(elem(1, 'supported'))).toBe(true);
  });

  it('flags unresolved / null state', () => {
    expect(elementIsThin(elem(5, 'unresolved'))).toBe(true);
    expect(elementIsThin(elem(5, null))).toBe(true);
  });

  it('flags a well-counted element whose sourcing carries a note', () => {
    expect(elementIsThin(elem(4, 'supported', THIN_BASIS))).toBe(true);
  });

  it('flags a repetition-only element as toppable (F4)', () => {
    expect(elementIsThin(elem(4, 'supported', REPETITION_BASIS))).toBe(true);
  });

  it('does NOT flag a well-covered element', () => {
    expect(elementIsThin(elem(3, 'supported', HEALTHY_BASIS))).toBe(false);
    expect(elementIsThin(elem(4, 'contextual', HEALTHY_BASIS))).toBe(false);
  });
});

describe('thinElementCount', () => {
  it('counts only the thin elements', () => {
    const elements = [
      elem(0, 'unresolved'), // gap → not counted
      elem(2, 'supported'), // few refs → thin
      elem(2, 'disputed'), // disputed → not counted
      elem(3, 'supported', HEALTHY_BASIS), // well-covered → not counted
      elem(5, 'unresolved'), // unresolved → thin
    ];
    expect(thinElementCount(elements)).toBe(2);
  });
});
