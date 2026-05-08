export interface ClaimForSelection {
  position: number;
  text: string;
  claimType: string;
  significanceRank: number;
}

/**
 * V1 plan locked decision (2026-05-06): cap selection at 3 claims.
 * Above this the mapper / quality framework degrade to mediocre on
 * variety dimensions. Raise in Phase 2 only after we have evidence
 * Bug A is robust at 4. UI cap is "soft" in the sense that the
 * backend would accept up to 12 claims — the cap is a UX-side rail.
 */
export const MAX_SELECTABLE_CLAIMS = 3;
