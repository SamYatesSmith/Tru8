/** Shared utility functions for evidence views. */

import type { EvidenceTier, EvidenceRelationship } from '@shared/types';

export function extractDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
}

/**
 * Tidy an evidence title for display. Search providers (Serper/Google) hand us
 * titles already cut at ~54 characters with a trailing ellipsis, often followed
 * by a redundant " - Site" / " | Site" suffix (we show the domain separately).
 *
 * We drop the orphaned site suffix but KEEP a single "…" (2026-08-25). Deleting
 * the marker made a provider-truncated title read as a deliberate full stop —
 * "Britain braces for unprecedented water restrictions as" looks like a whole
 * headline rather than the fragment it is, and the reader has no way to tell a
 * complete title from a cut one. That is hidden curation of the display
 * (invariant #5: every exclusion has a receipt); the ellipsis IS the receipt.
 *
 * Measured on the replay corpus: 34.3% of provider titles (209/609) arrive
 * already truncated, median 54 chars — so this is the common case, not an edge.
 *
 * We cannot recover the dropped words here. That is the fetcher's job
 * (`EvidenceExtractor._extract_title_from_html`, og:title → twitter:title →
 * <title>), which cannot run when the page blocks us and retrieval falls back
 * to the search snippet (`retrieve.py` snippet-fallback path). What this can do
 * is not pretend the fragment is the whole thing.
 *
 * Clean titles (no ellipsis) are returned untouched.
 */
export function cleanTitle(title?: string | null): string {
  if (!title) return '';
  const out = title
    .trim()
    // trailing "… - Site" / "... | Site" — keep the marker, drop the suffix
    .replace(/\s*(?:\.{2,}|…)\s*[-|–—]\s*[^-|–—]+$/, '…')
    // normalise any trailing "..." / " …" to one tight "…"
    .replace(/\s*(?:\.{2,}|…)\s*$/, '…')
    .trim();
  // A title that is nothing but a truncation marker carries no information —
  // let the caller's "Untitled source" fallback take over. (Deliberately not a
  // \p{L} class: this tsconfig targets pre-ES6, where the /u flag won't compile.)
  return /[^\s.…]/.test(out) ? out : '';
}

export function formatShortDate(date: Date): string {
  return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

export function formatDateStr(dateStr?: string): string {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  } catch {
    return dateStr;
  }
}

export function getFaviconUrl(url: string): string {
  try {
    const hostname = new URL(url).hostname;
    // sz=64 though icons render at 12-16px: retina displays paint 2-3 device
    // px per CSS px, and Google's service upscales a 16px source to smaller
    // sz values — both read as the pixelation reported 2026-08-26. 64 is the
    // largest size the service reliably serves; the browser downscales crisply.
    return `https://www.google.com/s2/favicons?domain=${hostname}&sz=64`;
  } catch {
    return '';
  }
}

const TIER_COLORS: Record<string, string> = {
  primary: '#EA580C',
  reporting: '#3F3F46',
  commentary: '#A1A1AA',
};

export function getTierColor(tier?: string): string {
  return TIER_COLORS[tier || 'commentary'] || TIER_COLORS.commentary;
}

/**
 * Count evidence by tier, defaulting an unset/null tier to `commentary`
 * (matches CartographerView's bucketing). Used by the claim Summary panel's
 * source-mix line.
 */
export function tierCounts(
  evidence: { tier?: EvidenceTier | null }[]
): Record<EvidenceTier, number> {
  const counts: Record<EvidenceTier, number> = { primary: 0, reporting: 0, commentary: 0 };
  for (const ev of evidence) {
    counts[ev.tier || 'commentary'] += 1;
  }
  return counts;
}

/* ── Evidence-stance helpers (Evidence Digest, 2026-06-30) ─────────────────
 * Stance lives on the ClaimMap evidence_refs (the locked source of truth), not
 * on the Evidence object. These mirror LibrarianView's relationshipRefs model
 * so the digest's distribution bar is consistent with how Evidence filters.
 */

interface ElementLike {
  evidenceRefs?: { evidenceId: string; relationship: EvidenceRelationship }[];
}

/** evidenceId → distinct relationships across ALL elements (an item can carry
 * more than one, exactly like LibrarianView's relationshipSummaryMap). */
export function relationshipByEvidence(
  elements: ElementLike[]
): Map<string, EvidenceRelationship[]> {
  const sets = new Map<string, Set<EvidenceRelationship>>();
  for (const el of elements) {
    for (const ref of el.evidenceRefs || []) {
      const s = sets.get(ref.evidenceId) || new Set<EvidenceRelationship>();
      s.add(ref.relationship);
      sets.set(ref.evidenceId, s);
    }
  }
  const out = new Map<string, EvidenceRelationship[]>();
  sets.forEach((s, id) => out.set(id, Array.from(s)));
  return out;
}

/** True if an evidence item carries at least one ref of the given relationship
 * — exactly the predicate LibrarianView uses to filter, so a digest band's
 * count equals the filtered Evidence list a user sees when they click it. */
export function hasRelationship(
  rels: EvidenceRelationship[] | undefined,
  stance: EvidenceRelationship
): boolean {
  return !!rels && rels.includes(stance);
}

/**
 * Distribution of mapped evidence across the three stances (the bar). Counts by
 * MEMBERSHIP (an item with both supports + challenges is counted in BOTH bands)
 * so each band's count matches clicking it through to the filtered Evidence
 * lens. `total` is the count of DISTINCT mapped items; with overlap the three
 * bands can sum above `total` (rare — most items carry a single relationship).
 */
export function stanceCounts(
  evidence: { id: string; evidenceId?: string }[],
  relMap: Map<string, EvidenceRelationship[]>
): { supports: number; challenges: number; context: number; total: number } {
  const c = { supports: 0, challenges: 0, context: 0, total: 0 };
  for (const ev of evidence) {
    const rels = relMap.get(ev.evidenceId || ev.id);
    if (!rels || rels.length === 0) continue;
    c.total += 1;
    for (const r of rels) c[r] += 1;
  }
  return c;
}
