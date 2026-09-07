import type { ClaimElement } from '@shared/types';

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

export function evidenceCoverage(elements: ClaimElement[]) {
  const withEvidence = elements.filter(hasMappedEvidence).length;
  return {
    gaps: elements.length - withEvidence,
    needsReview: elements.filter(needsEvidenceReview).length,
    coverage: elements.length ? Math.round(100 * withEvidence / elements.length) : 0,
    withEvidence,
  };
}
