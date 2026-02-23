import { Claim } from '@shared/types';

export interface DiagnosticResult {
  values: Map<string, number>;
  hasDiagnosticVariance: boolean;
  highCount: number;
  totalCount: number;
}

/**
 * ACH-inspired diagnostic value computation.
 *
 * For each evidence item, examines its relationships across all elements to
 * determine how much it differentiates between competing interpretations.
 *
 * Evidence that both supports AND challenges different elements has maximum
 * diagnostic value. Evidence that only provides context has minimal value.
 */
export function computeDiagnosticValues(claims: Claim[]): DiagnosticResult {
  // Collect all (element_id, relationship) pairs per evidence_id
  const evidenceRelations = new Map<string, Array<{ elementId: string; relationship: string }>>();
  let hasChallenges = false;

  for (const claim of claims) {
    if (!claim.claimMap?.elements) continue;
    for (const element of claim.claimMap.elements) {
      for (const ref of element.evidenceRefs || []) {
        const existing = evidenceRelations.get(ref.evidenceId) || [];
        existing.push({ elementId: element.elementId, relationship: ref.relationship });
        evidenceRelations.set(ref.evidenceId, existing);
        if (ref.relationship === 'challenges') hasChallenges = true;
      }
    }
  }

  const values = new Map<string, number>();
  let highCount = 0;

  Array.from(evidenceRelations.entries()).forEach(([evidenceId, relations]) => {
    const hasSupports = relations.some((r) => r.relationship === 'supports');
    const hasChallengesRel = relations.some((r) => r.relationship === 'challenges');
    const hasOnlyContext = relations.every((r) => r.relationship === 'context');

    let value: number;

    if (hasSupports && hasChallengesRel) {
      // Actively differentiates between competing states
      value = 1.0;
    } else if (relations.length === 1 && !hasOnlyContext) {
      // Linked to 1 element only, with directional relationship
      value = 0.6;
    } else if (hasOnlyContext) {
      // Background information, not directional
      value = 0.1;
    } else {
      // Same relationship for all elements — no diagnostic power
      value = 0.2;
    }

    values.set(evidenceId, value);
    if (value > 0.7) highCount++;
  });

  return {
    values,
    hasDiagnosticVariance: hasChallenges,
    highCount,
    totalCount: values.size,
  };
}
