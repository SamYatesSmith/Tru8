/** Shared utility functions for evidence views. */

import type { EvidenceTier } from '@shared/types';

export function extractDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
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
