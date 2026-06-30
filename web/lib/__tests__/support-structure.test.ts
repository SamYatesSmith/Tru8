import { describe, it, expect } from 'vitest';
import { evidenceQualityNote } from '../support-structure';
import type { EvidenceSideStructure } from '@shared/types';

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
});
