'use client';

import { useState, useMemo } from 'react';
import { Claim, Evidence, EvidenceTier, ClaimElement } from '@shared/types';
import { LandscapeSummaryStrip } from './LandscapeSummaryStrip';
import { EvidenceMap, type ElementMapping } from './EvidenceMap';
import { GapIndicator } from './GapIndicator';
import { ElementRoster } from './ElementRoster';

// --- Mobile helpers ---

function getDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return '';
  }
}

function getFaviconUrl(url: string): string {
  const domain = getDomain(url);
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

const MOBILE_TIER_CONFIG: Record<EvidenceTier, { label: string; colour: string; borderClass: string }> = {
  primary:    { label: 'Primary Sources',  colour: 'var(--tier1-accent)', borderClass: 'border-l-[var(--tier1-accent)]' },
  reporting:  { label: 'Reporting',        colour: '#3F3F46',            borderClass: 'border-l-zinc-700' },
  commentary: { label: 'Commentary',       colour: '#A1A1AA',            borderClass: 'border-l-zinc-400' },
};

// --- Main Component ---

interface CartographerViewProps {
  scope: 'check' | 'claim';
  claims: Claim[];
  onSwitchToLibrarian?: () => void;
}

export function CartographerView({ scope, claims, onSwitchToLibrarian }: CartographerViewProps) {
  const [expandedMobileId, setExpandedMobileId] = useState<string | null>(null);

  const {
    evidenceByTier,
    gaps,
    elements,
    claimLabelMap,
    evidenceElementMap,
    totalSources,
    primaryCount,
    reportingCount,
    commentaryCount,
  } = useMemo(() => {
    const seen = new Set<string>();
    const allEvidence: Evidence[] = [];
    const claimLabelMap = new Map<string, string>();
    const allElements: ClaimElement[] = [];

    claims.forEach((claim, claimIdx) => {
      const evidence = claim.evidence || [];

      // Collect elements
      if (claim.claimMap?.elements) {
        for (const el of claim.claimMap.elements) {
          if (scope === 'claim' || !allElements.some((e) => e.elementId === el.elementId)) {
            allElements.push(el);
          }
        }
      }

      for (const ev of evidence) {
        const evId = ev.evidenceId || ev.id;
        if (ev.receiptStatus === 'excluded') continue;
        if (scope === 'check' && seen.has(evId)) continue;
        seen.add(evId);
        allEvidence.push(ev);

        // Claim attribution for check-wide scope
        if (scope === 'check') {
          const label = `Claim ${String(claimIdx + 1).padStart(2, '0')}`;
          const existing = claimLabelMap.get(evId);
          claimLabelMap.set(evId, existing ? `${existing}, ${label}` : label);
        }
      }
    });

    // Group by tier
    const evidenceByTier: Record<EvidenceTier, Evidence[]> = { primary: [], reporting: [], commentary: [] };
    for (const ev of allEvidence) {
      const tier = ev.tier || 'commentary';
      evidenceByTier[tier].push(ev);
    }

    // Gaps: elements with no evidence refs
    const gapElements = allElements.filter((el) => (el.evidenceRefs?.length || 0) === 0);

    // Build reverse map: evidenceId -> element mappings
    const evidenceElementMap = new Map<string, ElementMapping[]>();
    allElements.forEach((el, globalIdx) => {
      for (const ref of el.evidenceRefs || []) {
        const existing = evidenceElementMap.get(ref.evidenceId) || [];
        existing.push({
          elementIndex: globalIdx,
          elementDescription: el.description,
          relationship: ref.relationship as 'supports' | 'challenges' | 'context',
        });
        evidenceElementMap.set(ref.evidenceId, existing);
      }
    });

    return {
      evidenceByTier,
      gaps: gapElements,
      elements: allElements,
      claimLabelMap: scope === 'check' ? claimLabelMap : undefined,
      evidenceElementMap,
      totalSources: allEvidence.length,
      primaryCount: evidenceByTier.primary.length,
      reportingCount: evidenceByTier.reporting.length,
      commentaryCount: evidenceByTier.commentary.length,
    };
  }, [claims, scope]);

  return (
    <div>
      <LandscapeSummaryStrip
        totalSources={totalSources}
        primaryCount={primaryCount}
        reportingCount={reportingCount}
        commentaryCount={commentaryCount}
      />

      {/* Desktop: Force-directed evidence map */}
      <div className="hidden md:block mb-12">
        <EvidenceMap
          evidenceByTier={evidenceByTier}
          elements={elements}
          evidenceElementMap={evidenceElementMap}
          claimLabelMap={claimLabelMap}
        />
      </div>

      {/* Mobile: Tier-grouped evidence nodes */}
      <div className="md:hidden mb-12">
        {(['primary', 'reporting', 'commentary'] as EvidenceTier[]).map((tier) => {
          const items = evidenceByTier[tier];
          if (items.length === 0) return null;
          const config = MOBILE_TIER_CONFIG[tier];
          const expandedInTier = items.find(
            (ev) => (ev.evidenceId || ev.id) === expandedMobileId,
          );

          return (
            <div key={tier} className="mb-6">
              {/* Tier header */}
              <div className="flex items-center gap-2 mb-3">
                <div className="w-3 h-[3px] shrink-0" style={{ background: config.colour }} />
                <span
                  className="font-mono text-[10px] uppercase tracking-widest font-semibold"
                  style={{ color: config.colour }}
                >
                  {config.label}
                </span>
                <span className="font-mono text-[10px] text-zinc-300">{items.length}</span>
              </div>

              {/* Node grid — centred, uniform 44px, element badges */}
              <div className="flex flex-wrap gap-4 justify-center">
                {items.map((ev) => {
                  const evId = ev.evidenceId || ev.id;
                  const isExpanded = expandedMobileId === evId;
                  const mappings = evidenceElementMap.get(evId) || [];
                  const elBadge =
                    mappings.length > 0
                      ? mappings
                          .map((m) => String(m.elementIndex + 1).padStart(2, '0'))
                          .join('\u00B7')
                      : '';

                  return (
                    <div key={evId} className="flex flex-col items-center gap-1">
                      <button
                        onClick={() =>
                          setExpandedMobileId(isExpanded ? null : evId)
                        }
                        className="relative flex items-center justify-center w-11 h-11"
                        aria-label={`${ev.source}: ${ev.title}`}
                      >
                        <div
                          className="absolute inset-0 rounded-full border-2"
                          style={{ borderColor: config.colour }}
                        />
                        <div className="absolute inset-[2px] rounded-full bg-white overflow-hidden flex items-center justify-center">
                          <span className="absolute font-mono font-semibold text-zinc-300 text-[13px]">
                            {(ev.source || '?')[0].toUpperCase()}
                          </span>
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={getFaviconUrl(ev.url)}
                            alt=""
                            className="absolute inset-0 w-full h-full object-cover"
                            onError={(e) => {
                              (e.target as HTMLImageElement).style.display =
                                'none';
                            }}
                          />
                        </div>
                        {isExpanded && (
                          <div
                            className="absolute rounded-full border"
                            style={{
                              inset: -3,
                              borderColor: config.colour,
                              opacity: 0.3,
                            }}
                          />
                        )}
                      </button>
                      {/* Element badge — shows which elements this source addresses */}
                      {elBadge && (
                        <span className="font-mono text-[8px] text-zinc-400 leading-none">
                          {elBadge}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Expanded detail card — outside flex flow, centred */}
              {expandedInTier && (() => {
                const ev = expandedInTier;
                const evId = ev.evidenceId || ev.id;
                const mappings = evidenceElementMap.get(evId) || [];
                return (
                  <div className="mt-3 border border-zinc-200 bg-white p-3 mx-auto max-w-[320px]">
                    <div
                      className="font-mono text-[9px] uppercase tracking-widest mb-1"
                      style={{ color: config.colour }}
                    >
                      {ev.source}
                    </div>
                    <div className="text-[12px] text-zinc-900 font-medium leading-snug mb-1.5">
                      {ev.title}
                    </div>
                    {ev.publishedDate && (
                      <div className="text-[10px] text-zinc-400 font-mono mb-2">
                        {formatDate(ev.publishedDate)}
                      </div>
                    )}
                    {mappings.length > 0 && (
                      <div className="border-t border-zinc-100 pt-1.5 mb-2">
                        <div className="font-mono text-[9px] uppercase tracking-widest text-zinc-400 mb-1">
                          Addresses
                        </div>
                        {mappings.map((m) => (
                          <div
                            key={m.elementIndex}
                            className="text-[11px] text-zinc-500 mb-0.5"
                          >
                            Element{' '}
                            {String(m.elementIndex + 1).padStart(2, '0')}
                            <span className="text-zinc-400"> &mdash; </span>
                            <span className="text-zinc-400">
                              {m.elementDescription}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                    {claimLabelMap?.get(evId) && (
                      <div className="text-[9px] text-zinc-400 font-mono uppercase tracking-wider mb-2">
                        {claimLabelMap.get(evId)}
                      </div>
                    )}
                    <a
                      href={ev.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-mono text-[10px] uppercase tracking-widest text-zinc-500 hover:text-zinc-900 transition-colors"
                    >
                      Visit source &rarr;
                    </a>
                  </div>
                );
              })()}
            </div>
          );
        })}
      </div>

      {/* Not Yet Found */}
      {gaps.length > 0 && (
        <div className="mb-8">
          <div className="font-mono text-xs font-bold uppercase tracking-widest text-zinc-500 mb-3">
            Not Yet Found
          </div>
          <div className="flex flex-wrap gap-3">
            {gaps.map((el, i) => {
              const elIndex = elements.indexOf(el);
              return (
                <GapIndicator
                  key={el.elementId}
                  elementDescription={el.description}
                  elementNumber={elIndex >= 0 ? elIndex + 1 : i + 1}
                />
              );
            })}
          </div>
        </div>
      )}

      {/* Element Roster */}
      {elements.length > 0 && (
        <ElementRoster elements={elements} />
      )}

      {/* Switch to Librarian */}
      <div className="text-center pt-8 border-t border-zinc-100">
        <button
          onClick={onSwitchToLibrarian}
          className="font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:text-zinc-900 transition-colors inline-flex items-center gap-2"
        >
          Explore the full collection <span className="text-sm">&rarr;</span>
        </button>
      </div>
    </div>
  );
}
