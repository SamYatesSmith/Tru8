/**
 * Evidence date provenance helpers (F2 Phase B).
 *
 * The backend labels where each evidence item's published date came from
 * (Evidence.date_basis / API `dateBasis`). Search engines sometimes
 * synthesise a date from a URL upload path (a 2000-era PDF under
 * /uploads/2026/04/ reported as Apr 2026) — those arrive labelled
 * 'url_inferred_suspect'. Surfaces show them with a neutral hint and the
 * timeline treats them as undated. Labelling only — never hidden.
 *
 * Design: audit/2026-07-03_f1f2_design_review.md (founder-approved).
 */

import type { Evidence } from '@shared/types';

export const DATE_HINT_TEXT = 'reported by host';
export const DATE_HINT_TOOLTIP =
  'Date reported by the hosting site — not confirmed by the document itself.';

/** True when the date is likely the host's upload date, not publication. */
export function isSuspectDate(
  evidence: Pick<Evidence, 'dateBasis'>
): boolean {
  return evidence.dateBasis === 'url_inferred_suspect';
}

/**
 * Date for timeline placement — suspect dates are treated as undated so the
 * Chronologist axis only plots dates we can stand behind (founder decision 4).
 * Returns null for missing, unparseable, or suspect dates.
 */
export function timelineDate(
  evidence: Pick<Evidence, 'publishedDate' | 'dateBasis'>
): Date | null {
  if (!evidence.publishedDate || isSuspectDate(evidence)) return null;
  const parsed = new Date(evidence.publishedDate);
  return isNaN(parsed.getTime()) ? null : parsed;
}
