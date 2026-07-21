import type { ClaimElement, ElementBasis, EvidenceSideStructure } from '@shared/types';

/**
 * Presentation-layer flag over the structure the pipeline produced for one
 * side (supports or challenges) of a claim sub-element.
 *
 * It describes the SOURCES — never the claim's truth — and only fires when a
 * side looks weak. Healthy or empty sides return null (no note shown). The
 * pipeline stays judgment-free; the thin/echo thresholds live here so they can
 * be tuned without a re-run.
 */
export type QualityNoteKind = 'echo' | 'repetition' | 'thin';

export interface QualityNote {
  kind: QualityNoteKind;
  label: string;
  detail: string;
}

// Publisher platforms hosting many independent journals under one domain.
// Parity-locked with PORTFOLIO_HOSTS in support_structure.py (§4d fix 5).
const PORTFOLIO_HOSTS = new Set([
  'nature.com',
  'sciencedirect.com',
  'springer.com',
  'onlinelibrary.wiley.com',
  'tandfonline.com',
  'academic.oup.com',
  'journals.plos.org',
]);

export function evidenceQualityNote(
  s: EvidenceSideStructure | undefined | null,
): QualityNote | null {
  if (!s || !s.count) return null;

  const d = s.derivation || { originals: 0, derivative_count: 0 };
  const tc = s.tier_counts || { primary: 0, reporting: 0, commentary: 0 };

  // Echo: apparent breadth is mostly re-reporting a single original source.
  if (d.originals >= 1 && d.derivative_count >= 2) {
    return {
      kind: 'echo',
      label: 'Mostly one source repeated',
      detail: 'Several of these sources repeat a single original report.',
    };
  }

  // Repetition (F4): several sources on this side recite the same wording
  // across ≥2 domains, with no primary source here — a talking point.
  const rep = s.repetition || { max_cluster_on_side: 0, distinct_domains: 0 };
  if (
    rep.max_cluster_on_side >= 3 &&
    rep.distinct_domains >= 2 &&
    (tc.primary || 0) === 0
  ) {
    return {
      kind: 'repetition',
      label: 'Same wording, no primary',
      detail: 'Several sources share the same wording; no primary source found behind them.',
    };
  }

  const commentaryOnly = (tc.primary || 0) === 0 && (tc.reporting || 0) === 0;
  // (s.distinct_domains || 0) mirrors the backend's `... or 0` so a malformed /
  // legacy side missing the field classifies identically across both ports.
  const singleOutlet = s.count >= 2 && (s.distinct_domains || 0) <= 1;

  // Thin: low-grade sourcing only, or several items from a single outlet.
  if (commentaryOnly) {
    return {
      kind: 'thin',
      label: 'Thin sourcing',
      detail: 'Only commentary-grade sources — no primary or reporting evidence.',
    };
  }
  if (singleOutlet) {
    // A publisher platform (Nature, ScienceDirect …) hosts many independent
    // journals under one domain — not the same as one website. Parity twin of
    // PORTFOLIO_HOSTS in support_structure.py.
    if (PORTFOLIO_HOSTS.has(s.sole_domain || '')) {
      return {
        kind: 'thin',
        label: 'Thin sourcing',
        detail: 'All via a single publisher platform, which may host multiple journals.',
      };
    }
    return {
      kind: 'thin',
      label: 'Thin sourcing',
      detail: 'All from a single website.',
    };
  }

  return null;
}

/** True when EITHER side of the element carries a thin/echo note. */
export function elementHasQualityNote(basis: ElementBasis | undefined | null): boolean {
  if (!basis) return false;
  return (
    evidenceQualityNote(basis.support_structure) !== null ||
    evidenceQualityNote(basis.challenge_structure) !== null
  );
}

/**
 * Does this element show a "top-up" trigger? A THIN element the user can pull
 * more evidence into — NOT a gap (the Seeker owns 0-source elements).
 *
 * MUST stay in lock-step with the backend `element_is_thin`
 * (`backend/app/pipeline/support_structure.py`), which the claim-level
 * "Strengthen this claim" endpoint uses to pick which elements to top up — so
 * the button never appears on an element the endpoint wouldn't strengthen, and
 * never hides on one it would.
 *
 * Thin iff ≥1 mapped source AND state is not `disputed` AND any of:
 *   - ≤ 2 mapped sources, OR
 *   - state is `unresolved` / unset, OR
 *   - either side carries a thin/echo note.
 */
export function elementIsThin(element: ClaimElement): boolean {
  const refs = element.evidenceRefs || [];
  if (refs.length === 0) return false; // gap → Seeker's territory
  if (element.state === 'disputed') return false; // evidence-rich, contested
  if (refs.length <= 2) return true;
  if (element.state == null || element.state === 'unresolved') return true;
  if (elementHasQualityNote(element.basis)) return true;
  return false;
}

/** Count of thin elements — drives the claim-level button's visibility/label. */
export function thinElementCount(elements: ClaimElement[]): number {
  return elements.reduce((n, el) => n + (elementIsThin(el) ? 1 : 0), 0);
}
