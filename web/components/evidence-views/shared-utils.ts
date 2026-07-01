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
 * titles already truncated with a trailing ellipsis, often followed by a
 * redundant " - Site" / " | Site" suffix (we show the domain separately). We
 * can't recover the dropped words, but we can strip the lazy trailing "…" and
 * the orphaned site suffix so a title reads "…triggered seismicity" cleanly
 * rather than "…triggered seismicity … - Science". Clean titles (no ellipsis)
 * are left untouched — this only removes a dangling truncation marker.
 */
export function cleanTitle(title?: string | null): string {
  if (!title) return '';
  return title
    .trim()
    // trailing "… - Site" / "... | Site" (ellipsis + orphaned site suffix)
    .replace(/\s*(?:\.{2,}|…)\s*[-|–—]\s*[^-|–—]+$/, '')
    // bare trailing ellipsis
    .replace(/\s*(?:\.{2,}|…)\s*$/, '')
    .trim();
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
    return `https://www.google.com/s2/favicons?domain=${hostname}&sz=32`;
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
