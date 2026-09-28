/**
 * Notables selection — which source headlines the digest for each direction.
 *
 * A− S3 (2026-09-28): the headline was the supporter with the highest raw
 * retrieval relevance, and it was the wrong source on 13 of 19 re-measured
 * records (a Medium essay, a journalist's profile page, a carbon calculator,
 * the claimant's own newsletter). Scored against the graders' named best
 * sources on the 15 records with a support: relevance 3/15; this rule 9/15.
 * Record: audit/2026-09-28_notables_selection.md.
 *
 * Order, identical for supports and challenges (invariant #7):
 *   1. not a platform, reprint or rewrite host, and not an opinion piece;
 *   2. the most elements it bears on in that direction;
 *   3. tier (primary, reporting, commentary) — classification, not a score;
 *   4. retrieval relevance;
 *   5. an exact tie goes to the earlier publication (an original over a later
 *      rewrite: FT 12 Sep over memeburn 16 Sep on record 77a6669f). As the
 *      main tie-break, ahead of relevance, the date scored 7/15, so it only
 *      breaks exact ties.
 */
import type { EvidenceRelationship } from '@shared/types';

interface NotableEvidence {
  id: string;
  evidenceId?: string;
  url?: string;
  source?: string;
  tier?: string | null;
  evidenceType?: string | null;
  relevanceScore?: number | null;
  publishedDate?: string | null;
}

interface ElementRefs {
  evidenceRefs?: { evidenceId: string; relationship: EvidenceRelationship }[];
}

// Platforms and rewrite/reprint hosts: the page a reader lands on is not the
// source's own publication (muckrack profiles, resultsense rewrites, social posts).
const SECONDHAND_HOST =
  /(?:^|\.)(?:medium\.com|substack\.com|muckrack\.com|resultsense\.com|rocketnews\.com|msn\.com|yahoo\.com|newsbreak\.com|flipboard\.com|ground\.news|facebook\.com|instagram\.com|x\.com|twitter\.com|reddit\.com|youtube\.com|tiktok\.com|linkedin\.com|threads\.(?:com|net)|quora\.com)$/i;

const TIER_RANK: Record<string, number> = { primary: 0, reporting: 1, commentary: 2 };

function hostOf(url?: string): string {
  if (!url) return '';
  try {
    return new URL(url).hostname.toLowerCase().replace(/^www\./, '');
  } catch {
    return '';
  }
}

export function isSecondhand(ev: NotableEvidence): boolean {
  return SECONDHAND_HOST.test(hostOf(ev.url)) || ev.evidenceType === 'opinion';
}

/** The headline source for one direction, or undefined when none bears that way. */
export function pickNotable<T extends NotableEvidence>(
  evidence: T[],
  elements: ElementRefs[],
  direction: 'supports' | 'challenges'
): T | undefined {
  const reach = new Map<string, number>();
  for (const el of elements) {
    const seen = new Set<string>();
    for (const ref of el.evidenceRefs || []) {
      if (ref.relationship !== direction || seen.has(ref.evidenceId)) continue;
      seen.add(ref.evidenceId);
      reach.set(ref.evidenceId, (reach.get(ref.evidenceId) || 0) + 1);
    }
  }
  const candidates = evidence.filter((ev) => (reach.get(ev.evidenceId || ev.id) || 0) > 0);
  if (candidates.length === 0) return undefined;
  const key = (ev: T): number[] => [
    isSecondhand(ev) ? 1 : 0,
    -(reach.get(ev.evidenceId || ev.id) || 0),
    TIER_RANK[ev.tier || 'commentary'] ?? 3,
    -(ev.relevanceScore ?? 0),
    ev.publishedDate ? Date.parse(ev.publishedDate) || Number.MAX_SAFE_INTEGER : Number.MAX_SAFE_INTEGER,
  ];
  return candidates.reduce((best, ev) => {
    const a = key(ev);
    const b = key(best);
    for (let i = 0; i < a.length; i++) {
      if (a[i] !== b[i]) return a[i] < b[i] ? ev : best;
    }
    return best;
  });
}
