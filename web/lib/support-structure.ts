import type { EvidenceSideStructure } from '@shared/types';

/**
 * Presentation-layer flag over the structure the pipeline produced for one
 * side (supports or challenges) of a claim sub-element.
 *
 * It describes the SOURCES — never the claim's truth — and only fires when a
 * side looks weak. Healthy or empty sides return null (no note shown). The
 * pipeline stays judgment-free; the thin/echo thresholds live here so they can
 * be tuned without a re-run.
 */
export type QualityNoteKind = 'echo' | 'thin';

export interface QualityNote {
  kind: QualityNoteKind;
  label: string;
  detail: string;
}

export function evidenceQualityNote(
  s: EvidenceSideStructure | undefined | null,
): QualityNote | null {
  if (!s || !s.count) return null;

  const d = s.derivation || { originals: 0, derivative_count: 0 };

  // Echo: apparent breadth is mostly re-reporting a single original source.
  if (d.originals >= 1 && d.derivative_count >= 2) {
    return {
      kind: 'echo',
      label: 'Mostly one source repeated',
      detail: 'Several of these sources repeat a single original report.',
    };
  }

  const tc = s.tier_counts || { primary: 0, reporting: 0, commentary: 0 };
  const commentaryOnly = (tc.primary || 0) === 0 && (tc.reporting || 0) === 0;
  const singleOutlet = s.count >= 2 && s.distinct_domains <= 1;

  // Thin: low-grade sourcing only, or several items from a single outlet.
  if (commentaryOnly) {
    return {
      kind: 'thin',
      label: 'Thin sourcing',
      detail: 'Only commentary-grade sources — no primary or reporting evidence.',
    };
  }
  if (singleOutlet) {
    return {
      kind: 'thin',
      label: 'Thin sourcing',
      detail: 'All from a single website.',
    };
  }

  return null;
}
