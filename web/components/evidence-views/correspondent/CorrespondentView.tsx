'use client';

import { useState, useMemo } from 'react';
import { Claim, Evidence, EvidenceTier } from '@shared/types';
import { CorrespondentSummary } from './CorrespondentSummary';
import { SourceCard } from './SourceCard';
import { SourceGaps } from './SourceGaps';

function getDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return '';
  }
}

function getFaviconUrl(domain: string): string {
  return domain ? `https://www.google.com/s2/favicons?domain=${domain}&sz=32` : '';
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  } catch {
    return '';
  }
}

function addUnique<T>(arr: T[], item: T): T[] {
  if (!arr.includes(item)) arr.push(item);
  return arr;
}

interface DomainGroup {
  domain: string;
  evidenceItems: Evidence[];
  tier: EvidenceTier;
  claimIndices: number[];
  elementIds: string[];
  dateRange: string;
}

const TIER_ORDER: Record<EvidenceTier, number> = { primary: 0, reporting: 1, commentary: 2 };
const TIER_GROUPS: EvidenceTier[] = ['primary', 'reporting', 'commentary'];

const TIER_DIVIDER_LABELS: Record<EvidenceTier, string> = {
  primary: 'PRIMARY DOMAINS',
  reporting: 'REPORTING DOMAINS',
  commentary: 'COMMENTARY DOMAINS',
};

const TIER_DIVIDER_COLOURS: Record<EvidenceTier, string> = {
  primary: 'text-[#EA580C]',
  reporting: 'text-[#3F3F46]',
  commentary: 'text-[#A1A1AA]',
};

interface CorrespondentViewProps {
  scope: 'check' | 'claim';
  claims: Claim[];
}

export function CorrespondentView({ scope, claims }: CorrespondentViewProps) {
  const [expandedDomain, setExpandedDomain] = useState<string | null>(null);

  const { domainGroups, tierGrouped, gaps, summary, elementDomainMap } = useMemo(() => {
    const seen = new Set<string>();
    const allEvidence: Evidence[] = [];
    const evidenceClaimMap = new Map<string, number[]>();
    const evidenceElementMap = new Map<string, string[]>();

    // Collect all evidence, deduped for check-wide
    claims.forEach((claim, claimIdx) => {
      const evidence = claim.evidence || [];

      // Build element → evidence mapping
      if (claim.claimMap?.elements) {
        for (const element of claim.claimMap.elements) {
          for (const ref of element.evidenceRefs || []) {
            const existing = evidenceElementMap.get(ref.evidenceId) || [];
            addUnique(existing, element.elementId);
            evidenceElementMap.set(ref.evidenceId, existing);
          }
        }
      }

      for (const ev of evidence) {
        const evId = ev.evidenceId || ev.id;
        if (ev.receiptStatus === 'excluded') continue;
        if (scope === 'check' && seen.has(evId)) continue;
        seen.add(evId);
        allEvidence.push(ev);

        // Track claim attribution
        const claimArr = evidenceClaimMap.get(evId) || [];
        addUnique(claimArr, claimIdx);
        evidenceClaimMap.set(evId, claimArr);
      }
    });

    // Group by domain
    const domainMap = new Map<string, DomainGroup>();

    for (const ev of allEvidence) {
      const evId = ev.evidenceId || ev.id;
      const domain = getDomain(ev.url) || ev.source || 'unknown';
      const existing = domainMap.get(domain);

      if (existing) {
        existing.evidenceItems.push(ev);
        const claimIndices = evidenceClaimMap.get(evId);
        if (claimIndices) claimIndices.forEach((i) => addUnique(existing.claimIndices, i));
        const elementIds = evidenceElementMap.get(evId);
        if (elementIds) elementIds.forEach((id) => addUnique(existing.elementIds, id));
      } else {
        domainMap.set(domain, {
          domain,
          evidenceItems: [ev],
          tier: ev.tier || 'commentary',
          claimIndices: [...(evidenceClaimMap.get(evId) || [])],
          elementIds: [...(evidenceElementMap.get(evId) || [])],
          dateRange: '',
        });
      }
    }

    // Compute dominant tier and date range for each domain
    const domainGroups: DomainGroup[] = [];
    for (const group of Array.from(domainMap.values())) {
      // Dominant tier: most common
      const tierCounts: Record<string, number> = {};
      for (const ev of group.evidenceItems) {
        const t = ev.tier || 'commentary';
        tierCounts[t] = (tierCounts[t] || 0) + 1;
      }
      let maxCount = 0;
      let dominantTier: EvidenceTier = 'commentary';
      for (const [tier, count] of Object.entries(tierCounts)) {
        if (count > maxCount || (count === maxCount && TIER_ORDER[tier as EvidenceTier] < TIER_ORDER[dominantTier])) {
          maxCount = count;
          dominantTier = tier as EvidenceTier;
        }
      }
      group.tier = dominantTier;

      // Date range
      const dates = group.evidenceItems
        .map((ev) => ev.publishedDate)
        .filter(Boolean)
        .map((d) => new Date(d!).getTime())
        .filter((t) => !isNaN(t));
      if (dates.length > 0) {
        const min = Math.min(...dates);
        const max = Math.max(...dates);
        if (min === max) {
          group.dateRange = formatDate(new Date(min).toISOString());
        } else {
          group.dateRange = `${formatDate(new Date(min).toISOString())} \u2013 ${formatDate(new Date(max).toISOString())}`;
        }
      }

      domainGroups.push(group);
    }

    // Sort domains within each tier by evidence count desc
    domainGroups.sort((a, b) => {
      const tierDiff = TIER_ORDER[a.tier] - TIER_ORDER[b.tier];
      if (tierDiff !== 0) return tierDiff;
      return b.evidenceItems.length - a.evidenceItems.length;
    });

    // Group by tier
    const tierGrouped: Record<EvidenceTier, DomainGroup[]> = { primary: [], reporting: [], commentary: [] };
    for (const group of domainGroups) {
      tierGrouped[group.tier].push(group);
    }

    // Sole source detection: for each element, which domains contribute?
    const elementDomainMap = new Map<string, string[]>();
    for (const group of domainGroups) {
      for (const elId of group.elementIds) {
        const domainArr = elementDomainMap.get(elId) || [];
        addUnique(domainArr, group.domain);
        elementDomainMap.set(elId, domainArr);
      }
    }

    // Gap analysis
    const gaps: { type: string; message: string }[] = [];

    // No primary sources
    if (tierGrouped.primary.length === 0 && allEvidence.length > 0) {
      gaps.push({
        type: 'no_primary',
        message: 'No primary sources in this landscape \u2014 all evidence is second-hand or commentary',
      });
    }

    // Sole source elements
    for (const [elId, domainArr] of Array.from(elementDomainMap.entries())) {
      if (domainArr.length === 1) {
        const singleDomain = domainArr[0];
        let elDesc = elId;
        for (const claim of claims) {
          const el = claim.claimMap?.elements?.find((e) => e.elementId === elId);
          if (el) {
            const idx = claim.claimMap!.elements.indexOf(el);
            elDesc = `Element ${String(idx + 1).padStart(2, '0')}`;
            break;
          }
        }
        gaps.push({
          type: 'sole_source',
          message: `All evidence for ${elDesc} comes from a single domain (${singleDomain})`,
        });
      }
    }

    // No academic sources
    const hasAcademic = allEvidence.some((ev) => ev.evidenceType === 'academic');
    if (!hasAcademic && allEvidence.length > 0) {
      gaps.push({
        type: 'no_academic',
        message: 'No academic or peer-reviewed sources found',
      });
    }

    // Single type
    const typeSet = new Set<string>();
    for (const ev of allEvidence) typeSet.add(ev.evidenceType || 'news_reporting');
    if (typeSet.size === 1 && allEvidence.length > 1) {
      const TYPE_LABELS: Record<string, string> = {
        data: 'data', official_statement: 'official statements', news_reporting: 'news reporting',
        analysis: 'analysis', opinion: 'opinion', academic: 'academic',
      };
      const singleType = Array.from(typeSet)[0];
      gaps.push({
        type: 'single_type',
        message: `All evidence is ${TYPE_LABELS[singleType] || singleType} \u2014 no type diversity`,
      });
    }

    // Summary
    const summary = {
      uniqueDomains: domainGroups.length,
      totalEvidence: allEvidence.length,
      primaryDomains: tierGrouped.primary.length,
      reportingDomains: tierGrouped.reporting.length,
      commentaryDomains: tierGrouped.commentary.length,
      domains: domainGroups.map((g) => ({
        name: g.domain,
        count: g.evidenceItems.length,
        tier: g.tier,
      })),
    };

    return { domainGroups, tierGrouped, gaps, summary, elementDomainMap };
  }, [claims, scope]);

  if (domainGroups.length === 0) {
    return (
      <div className="border border-dashed border-zinc-200 p-8 text-center">
        <span className="font-mono text-[11px] text-zinc-400">
          No evidence available for source diversity analysis
        </span>
      </div>
    );
  }

  // Build sole-source labels per domain
  function getSoleSourceLabels(group: DomainGroup): string[] {
    const labels: string[] = [];
    for (const elId of group.elementIds) {
      const domainArr = elementDomainMap.get(elId);
      if (domainArr && domainArr.length === 1) {
        for (const claim of claims) {
          const el = claim.claimMap?.elements?.find((e) => e.elementId === elId);
          if (el) {
            const idx = claim.claimMap!.elements.indexOf(el);
            labels.push(`Element ${String(idx + 1).padStart(2, '0')}`);
            break;
          }
        }
      }
    }
    return labels;
  }

  // Build claim-coverage label (element refs now render as chips via ElementRefs)
  function getClaimCoverage(group: DomainGroup): string {
    const claimLabels = [...group.claimIndices]
      .sort((a, b) => a - b)
      .map((i) => `Claim ${String(i + 1).padStart(2, '0')}`);
    return claimLabels.length > 0 ? `Speaks to ${claimLabels.join(', ')}` : '';
  }

  return (
    <div>
      <CorrespondentSummary {...summary} />

      {TIER_GROUPS.map((tier) => {
        const group = tierGrouped[tier];
        if (group.length === 0) return null;

        return (
          <div key={tier} className="mb-8">
            {/* Shelf divider */}
            <div className="flex items-center gap-3 mb-4">
              <div className="flex-1 h-px bg-zinc-200" />
              <span className={`font-mono text-[10px] font-bold uppercase tracking-widest ${TIER_DIVIDER_COLOURS[tier]}`}>
                {TIER_DIVIDER_LABELS[tier]} ({group.length})
              </span>
              <div className="flex-1 h-px bg-zinc-200" />
            </div>

            <div className="space-y-3">
              {group.map((g) => (
                <SourceCard
                  key={g.domain}
                  domain={g.domain}
                  faviconUrl={getFaviconUrl(g.domain)}
                  tier={g.tier}
                  evidenceCount={g.evidenceItems.length}
                  evidenceTitles={g.evidenceItems.map((ev) => ev.title)}
                  claimCoverage={getClaimCoverage(g)}
                  elementIds={g.elementIds}
                  dateRange={g.dateRange}
                  soleSourceFor={getSoleSourceLabels(g)}
                  isExpanded={expandedDomain === g.domain}
                  onClick={() => setExpandedDomain((prev) => (prev === g.domain ? null : g.domain))}
                  scope={scope}
                />
              ))}
            </div>
          </div>
        );
      })}

      <SourceGaps gaps={gaps} />
    </div>
  );
}
