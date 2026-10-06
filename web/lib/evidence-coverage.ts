import type { CitedSourceGap, ClaimElement, ClaimMap } from '@shared/types';

/** Evidence presence is a retrieval measure, never a claim of resolution. */
export function hasMappedEvidence(element: ClaimElement): boolean {
  return (element.evidenceRefs?.length ?? 0) > 0;
}

export function needsEvidenceReview(element: ClaimElement): boolean {
  return hasMappedEvidence(element) && (
    element.state !== 'supported' ||
    !element.evidenceRefs.some(ref => ref.relationship === 'supports')
  );
}

/**
 * Cited originals the pool's sources name that are not in this record (the
 * cited-source gap note, Build B). Entries without a verbatim name and cue
 * are dropped: the note shows page text only, never a guess.
 */
export function citedSourceGaps(claimMap?: ClaimMap | null): CitedSourceGap[] {
  const missing = claimMap?.metadata?.citedSources?.missing;
  if (!Array.isArray(missing)) return [];
  return missing.filter(
    (m): m is CitedSourceGap =>
      !!m && typeof m.name === 'string' && m.name.trim() !== '' &&
      typeof m.cue === 'string' && m.cue.trim() !== '',
  );
}

/**
 * The one coverage measure behind the summary panel, the Gaps lens, its
 * coverage map and the honesty tests. `gaps` counts elements with no mapped
 * evidence PLUS cited originals not in this record; `elementGaps` is the
 * element-only figure. Coverage stays an element measure.
 */
export function evidenceCoverage(elements: ClaimElement[], cited: CitedSourceGap[] = []) {
  const withEvidence = elements.filter(hasMappedEvidence).length;
  const elementGaps = elements.length - withEvidence;
  return {
    gaps: elementGaps + cited.length,
    elementGaps,
    citedMissing: cited.length,
    needsReview: elements.filter(needsEvidenceReview).length,
    coverage: elements.length ? Math.round(100 * withEvidence / elements.length) : 0,
    withEvidence,
  };
}
