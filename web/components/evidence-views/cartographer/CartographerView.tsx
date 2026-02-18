'use client';

import { useMemo, useCallback } from 'react';
import { Claim, Evidence, EvidenceTier, ClaimElement } from '@shared/types';
import { LandscapeSummaryStrip } from './LandscapeSummaryStrip';
import { CascadeLayout } from './CascadeLayout';
import { MobileCascade } from './MobileCascade';
import { ConvergenceDiamond } from './ConvergenceDiamond';
import { GapIndicator } from './GapIndicator';
import { ElementRoster } from './ElementRoster';

interface CartographerViewProps {
  scope: 'check' | 'claim';
  claims: Claim[];
  onSwitchToLibrarian?: () => void;
  onSwitchToInterpreter?: (elementIndex: number) => void;
}

export function CartographerView({ scope, claims, onSwitchToLibrarian, onSwitchToInterpreter }: CartographerViewProps) {
  const {
    evidenceByTier,
    edges,
    divergentIds,
    convergencePoints,
    gaps,
    elements,
    claimLabelMap,
    totalSources,
    primaryCount,
    reportingCount,
    commentaryCount,
  } = useMemo(() => {
    const seen = new Set<string>();
    const allEvidence: Evidence[] = [];
    const claimLabelMap = new Map<string, string>();
    const allElements: ClaimElement[] = [];

    // Collect evidence and build corroboration groups
    const corroborationGroups = new Map<number, { tiers: Set<EvidenceTier>; ids: string[] }>();

    // Track which elements have evidence for gap detection
    const elementsWithEvidence = new Set<string>();

    // Collect divergent evidence IDs (challenges on same element)
    const elementChallenges = new Map<string, string[]>();

    claims.forEach((claim, claimIdx) => {
      const evidence = claim.evidence || [];

      // Collect elements
      if (claim.claimMap?.elements) {
        for (const el of claim.claimMap.elements) {
          if (scope === 'claim' || !allElements.some((e) => e.elementId === el.elementId)) {
            allElements.push(el);
          }

          // Track challenges per element for divergence detection
          for (const ref of el.evidenceRefs || []) {
            elementsWithEvidence.add(el.elementId);
            if (ref.relationship === 'challenges') {
              const existing = elementChallenges.get(el.elementId) || [];
              existing.push(ref.evidenceId);
              elementChallenges.set(el.elementId, existing);
            }
          }
        }
      }

      for (const ev of evidence) {
        const evId = ev.evidenceId || ev.id;
        if (ev.receiptStatus === 'excluded') continue;

        if (scope === 'check' && seen.has(evId)) continue;
        seen.add(evId);
        allEvidence.push(ev);

        // Claim attribution for check-wide
        if (scope === 'check') {
          const label = `Claim ${String(claimIdx + 1).padStart(2, '0')}`;
          const existing = claimLabelMap.get(evId);
          claimLabelMap.set(evId, existing ? `${existing}, ${label}` : label);
        }

        // Track corroboration groups
        if (ev.corroborationGroupId != null) {
          const group = corroborationGroups.get(ev.corroborationGroupId) || { tiers: new Set(), ids: [] };
          group.tiers.add(ev.tier || 'commentary');
          group.ids.push(evId);
          corroborationGroups.set(ev.corroborationGroupId, group);
        }
      }
    });

    // Group evidence by tier
    const evidenceByTier: Record<EvidenceTier, Evidence[]> = { primary: [], reporting: [], commentary: [] };
    const evidenceTierMap = new Map<string, EvidenceTier>();

    for (const ev of allEvidence) {
      const tier = ev.tier || 'commentary';
      evidenceByTier[tier].push(ev);
      evidenceTierMap.set(ev.evidenceId || ev.id, tier);
    }

    // Build edges from corroboration groups spanning tiers
    const edges: Array<{ fromId: string; toId: string }> = [];
    const TIER_RANK: Record<EvidenceTier, number> = { primary: 0, reporting: 1, commentary: 2 };

    Array.from(corroborationGroups.values()).forEach((group) => {
      if (group.tiers.size < 2) return;

      // Sort IDs by tier rank
      const sorted = group.ids
        .map((id) => ({ id, rank: TIER_RANK[evidenceTierMap.get(id) || 'commentary'] }))
        .sort((a, b) => a.rank - b.rank);

      // Connect higher-tier items to lower-tier items
      for (let i = 0; i < sorted.length; i++) {
        for (let j = i + 1; j < sorted.length; j++) {
          if (sorted[i].rank < sorted[j].rank) {
            edges.push({ fromId: sorted[i].id, toId: sorted[j].id });
          }
        }
      }
    });

    // Convergence: corroboration groups with 3+ items from 2+ different sources
    let convergencePoints = 0;
    Array.from(corroborationGroups.values()).forEach((group) => {
      if (group.ids.length >= 3) convergencePoints++;
    });

    // Divergence: evidence IDs that challenge an element
    const divergentIds = new Set<string>();
    Array.from(elementChallenges.values()).forEach((ids) => {
      for (const id of ids) divergentIds.add(id);
    });

    // Gaps: elements with no evidence refs
    const gapElements = allElements.filter((el) => (el.evidenceRefs?.length || 0) === 0);

    return {
      evidenceByTier,
      edges,
      divergentIds,
      convergencePoints,
      gaps: gapElements,
      elements: allElements,
      claimLabelMap: scope === 'check' ? claimLabelMap : undefined,
      totalSources: allEvidence.length,
      primaryCount: evidenceByTier.primary.length,
      reportingCount: evidenceByTier.reporting.length,
      commentaryCount: evidenceByTier.commentary.length,
    };
  }, [claims, scope]);

  const handleNodeClick = useCallback((ev: Evidence) => {
    if (ev.url) {
      window.open(ev.url, '_blank', 'noopener,noreferrer');
    }
  }, []);

  return (
    <div>
      <LandscapeSummaryStrip
        totalSources={totalSources}
        primaryCount={primaryCount}
        reportingCount={reportingCount}
        commentaryCount={commentaryCount}
        convergencePoints={convergencePoints}
        gaps={gaps.length}
      />

      {/* Desktop: Dagre-ordered cascade */}
      <div className="hidden md:block">
        <CascadeLayout
          evidenceByTier={evidenceByTier}
          edges={edges}
          divergentIds={divergentIds}
          claimLabelMap={claimLabelMap}
          onNodeClick={handleNodeClick}
        />

        {convergencePoints > 0 && (
          <ConvergenceDiamond count={convergencePoints} />
        )}
      </div>

      {/* Mobile: CSS-only vertical stack */}
      <div className="md:hidden mb-16">
        <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-zinc-400 mb-8 border-b border-zinc-100 pb-2">
          Citation Cascade
        </div>
        <MobileCascade
          evidenceByTier={evidenceByTier}
          divergentIds={divergentIds}
          claimLabelMap={claimLabelMap}
          onNodeClick={handleNodeClick}
        />
      </div>

      {/* Gap indicators */}
      {gaps.length > 0 && (
        <div className="mb-8">
          <div className="font-mono text-[9px] uppercase tracking-widest text-zinc-400 mb-3">Evidence Gaps</div>
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
        <ElementRoster
          elements={elements}
          onElementClick={onSwitchToInterpreter}
        />
      )}

      {/* Switch to Librarian prompt */}
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
