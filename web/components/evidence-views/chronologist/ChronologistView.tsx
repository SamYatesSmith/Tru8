'use client';

import { useMemo, useState, useCallback } from 'react';
import { Claim, Evidence } from '@shared/types';
import { extractDomain, formatShortDate, getTierColor } from '../shared-utils';
import { TemporalInsightStrip } from './TemporalInsightStrip';
import { TimelineAxis } from './TimelineAxis';
import { TimelineNode } from './TimelineNode';
import { TimelineCluster } from './TimelineCluster';
import { UndatedSidebar } from './UndatedSidebar';
import { MobileTimeline } from './MobileTimeline';
import { EvidenceDetailCard } from './EvidenceDetailCard';
import { ChronologistProvenanceNote } from './ChronologistProvenanceNote';

// Tier-based dot sizes and vertical band offsets
const TIER_DOT_SIZES: Record<string, number> = { primary: 22, reporting: 20, commentary: 18 };
const TIER_LABELS: Record<string, string> = { primary: 'Primary', reporting: 'Reporting', commentary: 'Commentary' };
// Vertical bands: primary at top, reporting middle, commentary near axis
const TIER_BAND_OFFSET: Record<string, number> = { primary: 110, reporting: 65, commentary: 32 };

// --- Exported types consumed by child components ---

export interface DatedItem {
  evidence: Evidence;
  date: Date;
  color: string;
  tierLabel: string;
  dotSize: number;
  position: number;
  yLevel: number;
}

export interface ClusterItem {
  date: Date;
  items: DatedItem[];
  position: number;
  dominantColor: string;
}

export interface TickMark {
  label: string;
  position: number;
}

interface GapZone {
  startPos: number;
  endPos: number;
}

// --- Utility functions ---

function getPosition(date: Date, earliest: Date, latest: Date): number {
  const range = latest.getTime() - earliest.getTime();
  if (range === 0) return 50;
  return ((date.getTime() - earliest.getTime()) / range) * 100;
}

function generateTicks(earliest: Date, latest: Date): TickMark[] {
  const rangeMonths = (latest.getTime() - earliest.getTime()) / (1000 * 60 * 60 * 24 * 30);
  const ticks: TickMark[] = [];

  let step: number;
  if (rangeMonths < 12) step = 1;
  else if (rangeMonths < 36) step = 3;
  else step = 12;

  const current = new Date(earliest.getFullYear(), earliest.getMonth(), 1);

  while (current <= latest) {
    const pos = getPosition(current, earliest, latest);
    if (pos >= 0 && pos <= 100) {
      const label = step >= 12
        ? current.getFullYear().toString()
        : current.toLocaleDateString('en-GB', { month: 'short', year: '2-digit' });
      ticks.push({ label, position: pos });
    }
    current.setMonth(current.getMonth() + step);
  }

  return ticks;
}

/** Return the tier colour of the highest-priority tier in a group. */
function getDominantTierColor(items: DatedItem[]): string {
  if (items.some(i => i.evidence.tier === 'primary')) return getTierColor('primary');
  if (items.some(i => i.evidence.tier === 'reporting')) return getTierColor('reporting');
  return getTierColor('commentary');
}

// --- Component ---

interface ChronologistViewProps {
  scope: 'check' | 'claim';
  claims: Claim[];
  onSwitchToLibrarian?: () => void;
}

export function ChronologistView({ scope, claims, onSwitchToLibrarian }: ChronologistViewProps) {
  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null);

  const handleNodeClick = useCallback((evidence: Evidence) => {
    setSelectedEvidence(prev => {
      const prevId = prev?.evidenceId || prev?.id;
      const newId = evidence.evidenceId || evidence.id;
      return prevId === newId ? null : evidence;
    });
  }, []);

  const data = useMemo(() => {
    // 1. Pool evidence (dedup for check-wide)
    const seen = new Set<string>();
    const allEvidence: Array<{ evidence: Evidence; claimIdx: number }> = [];

    claims.forEach((claim, claimIdx) => {
      for (const ev of claim.evidence || []) {
        if (ev.receiptStatus === 'excluded') continue;
        const evId = ev.evidenceId || ev.id;
        if (scope === 'check' && seen.has(evId)) continue;
        seen.add(evId);
        allEvidence.push({ evidence: ev, claimIdx });
      }
    });

    // 2. Build element maps for detail card
    const elementMap = new Map<string, string[]>();
    const elementDescriptionMap = new Map<string, string>();

    for (const claim of claims) {
      for (const el of claim.claimMap?.elements || []) {
        elementDescriptionMap.set(el.elementId, el.description);
        for (const ref of el.evidenceRefs || []) {
          const existing = elementMap.get(ref.evidenceId) || [];
          if (!existing.includes(el.elementId)) {
            existing.push(el.elementId);
          }
          elementMap.set(ref.evidenceId, existing);
        }
      }
    }

    // 3. Partition dated vs undated
    const dated: Array<{ evidence: Evidence; date: Date; claimIdx: number }> = [];
    const undated: Evidence[] = [];

    for (const { evidence, claimIdx } of allEvidence) {
      if (evidence.publishedDate) {
        const parsed = new Date(evidence.publishedDate);
        if (!isNaN(parsed.getTime())) {
          dated.push({ evidence, date: parsed, claimIdx });
          continue;
        }
      }
      undated.push(evidence);
    }

    // 4. Threshold check (≥50% must have dates)
    const total = allEvidence.length;
    const datedCount = dated.length;
    const belowThreshold = total > 0 && datedCount / total < 0.5;

    if (belowThreshold || dated.length === 0) {
      return {
        belowThreshold: true,
        datedCount,
        total,
        items: [] as DatedItem[],
        clusters: [] as ClusterItem[],
        undated,
        ticks: [] as TickMark[],
        gaps: [] as GapZone[],
        todayPosition: null as number | null,
        earliest: null as Date | null,
        latest: null as Date | null,
        gapCount: 0,
        elementMap,
        elementDescriptionMap,
      };
    }

    // 5. Sort by date, determine bounds
    dated.sort((a, b) => a.date.getTime() - b.date.getTime());
    const earliest = dated[0].date;
    const latest = dated[dated.length - 1].date;

    // Padded bounds: extend to start of earliest month and end of latest month
    // so extreme dots aren't flush with container edges and axis covers full range
    const paddedEarliest = new Date(earliest.getFullYear(), earliest.getMonth(), 1);
    const paddedLatest = new Date(latest.getFullYear(), latest.getMonth() + 1, 1);

    // 6. Assign tier-based colours (same logic for both scopes)
    const coloredDated: DatedItem[] = dated.map(({ evidence, date }) => {
      const tier = evidence.tier || 'commentary';
      const color = getTierColor(tier);
      const tierLabel = TIER_LABELS[tier] || 'Commentary';
      const dotSize = TIER_DOT_SIZES[tier] || 7;

      return { evidence, date, color, tierLabel, dotSize, position: 0, yLevel: 0 };
    });

    // 7. Group by calendar date
    const groups = new Map<string, DatedItem[]>();
    for (const item of coloredDated) {
      const key = item.date.toISOString().slice(0, 10);
      const group = groups.get(key) || [];
      group.push(item);
      groups.set(key, group);
    }

    // 8. Separate positioned items vs clusters (3+ on same day)
    const items: DatedItem[] = [];
    const clusters: ClusterItem[] = [];

    Array.from(groups.values()).forEach((group) => {
      const pos = getPosition(group[0].date, paddedEarliest, paddedLatest);

      if (group.length >= 3) {
        clusters.push({
          date: group[0].date,
          items: group.map((g, i) => ({ ...g, position: pos, yLevel: i })),
          position: pos,
          dominantColor: getDominantTierColor(group),
        });
      } else {
        group.forEach((item, i) => {
          items.push({ ...item, position: pos, yLevel: i });
        });
      }
    });

    // 9. Generate axis ticks (using padded bounds so axis covers full range)
    const ticks = generateTicks(paddedEarliest, paddedLatest);

    // 10. Detect gaps (30+ days between consecutive evidence)
    const gaps: GapZone[] = [];
    for (let i = 1; i < dated.length; i++) {
      const diffDays = (dated[i].date.getTime() - dated[i - 1].date.getTime()) / (1000 * 60 * 60 * 24);
      if (diffDays > 30) {
        gaps.push({
          startPos: getPosition(dated[i - 1].date, paddedEarliest, paddedLatest),
          endPos: getPosition(dated[i].date, paddedEarliest, paddedLatest),
        });
      }
    }

    // 11. Today marker (only if within or just past range)
    const today = new Date();
    let todayPosition: number | null = null;
    if (today >= paddedEarliest && today <= paddedLatest) {
      todayPosition = getPosition(today, paddedEarliest, paddedLatest);
    } else if (today > paddedLatest) {
      const daysPast = (today.getTime() - paddedLatest.getTime()) / (1000 * 60 * 60 * 24);
      if (daysPast < 60) todayPosition = 100;
    }

    return {
      belowThreshold: false,
      datedCount,
      total,
      items,
      clusters,
      undated,
      ticks,
      gaps,
      todayPosition,
      earliest,
      latest,
      gapCount: gaps.length,
      elementMap,
      elementDescriptionMap,
    };
  }, [claims, scope]);

  // Derive element descriptions for the selected evidence
  const activeElementDescriptions = useMemo(() => {
    if (!selectedEvidence) return [];
    const evId = selectedEvidence.evidenceId || selectedEvidence.id;
    const elIds = data.elementMap.get(evId) || [];
    return elIds.map(eid => ({
      elementId: eid,
      description: data.elementDescriptionMap.get(eid) || '',
    }));
  }, [selectedEvidence, data.elementMap, data.elementDescriptionMap]);

  const selectedEvidenceId = selectedEvidence
    ? (selectedEvidence.evidenceId || selectedEvidence.id)
    : undefined;

  // --- Below threshold state ---
  if (data.belowThreshold) {
    return (
      <div className="py-12 text-center border border-dashed border-zinc-200 bg-zinc-50/30">
        <p className="font-mono text-[11px] text-zinc-500 mb-2">
          Insufficient date information for timeline.
        </p>
        <p className="font-mono text-[10px] text-zinc-400 mb-4">
          {data.datedCount} of {data.total} sources have publication dates.
        </p>
        {onSwitchToLibrarian && (
          <button
            onClick={onSwitchToLibrarian}
            className="font-mono text-[10px] uppercase tracking-widest text-[var(--accent)] hover:underline"
          >
            Switch to the Librarian to explore all sources
          </button>
        )}
      </div>
    );
  }

  // --- Main render ---
  return (
    <div>
      {/* Summary strip */}
      <TemporalInsightStrip
        earliest={data.earliest!}
        latest={data.latest!}
        datedCount={data.datedCount}
        totalCount={data.total}
        gapCount={data.gapCount}
      />

      {/* Desktop: horizontal timeline + undated sidebar */}
      <div className="hidden md:flex gap-6 mb-8">
        <div className="flex-grow min-w-0">
          {/* Timeline content area — tier bands: primary top, reporting middle, commentary near axis */}
          <div className="relative" style={{ minHeight: '160px' }}>
            {/* Tier band labels (left edge watermarks) */}
            <span className="absolute left-0 font-mono text-[8px] uppercase tracking-widest text-zinc-200 pointer-events-none" style={{ bottom: `${TIER_BAND_OFFSET.primary}px` }}>Pri</span>
            <span className="absolute left-0 font-mono text-[8px] uppercase tracking-widest text-zinc-200 pointer-events-none" style={{ bottom: `${TIER_BAND_OFFSET.reporting}px` }}>Rep</span>
            <span className="absolute left-0 font-mono text-[8px] uppercase tracking-widest text-zinc-200 pointer-events-none" style={{ bottom: `${TIER_BAND_OFFSET.commentary}px` }}>Com</span>

            {/* Faint tier band dividers */}
            <div className="absolute left-0 right-0 border-t border-dashed border-zinc-100" style={{ bottom: `${TIER_BAND_OFFSET.primary - 10}px` }} />
            <div className="absolute left-0 right-0 border-t border-dashed border-zinc-100" style={{ bottom: `${TIER_BAND_OFFSET.reporting - 10}px` }} />

            {/* Gap zones with label */}
            {data.gaps.map((gap, i) => (
              <div
                key={`gap-${i}`}
                className="absolute top-0 bottom-8 bg-zinc-50/50 border-x border-dashed border-zinc-200 flex items-center justify-center"
                style={{ left: `${gap.startPos}%`, width: `${gap.endPos - gap.startPos}%` }}
              >
                <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-300">Gap</span>
              </div>
            ))}

            {/* Today marker */}
            {data.todayPosition !== null && (
              <div className="absolute top-0 bottom-0" style={{ left: `${data.todayPosition}%` }}>
                <div className="w-[1px] h-full border-l border-dashed border-zinc-400" />
                <span className="absolute -top-1 -translate-x-1/2 font-mono text-[8px] uppercase tracking-widest text-zinc-400">
                  Today
                </span>
              </div>
            )}

            {/* Individual nodes — positioned vertically by tier band */}
            {data.items.map((item, i) => {
              const tier = item.evidence.tier || 'commentary';
              const bandOffset = TIER_BAND_OFFSET[tier] || TIER_BAND_OFFSET.commentary;
              return (
                <div
                  key={`node-${i}`}
                  className="absolute"
                  style={{
                    left: `${item.position}%`,
                    bottom: `${bandOffset + item.yLevel * 24}px`,
                    transform: 'translateX(-50%)',
                  }}
                >
                  <TimelineNode
                    evidence={item.evidence}
                    color={item.color}
                    tierLabel={item.tierLabel}
                    dotSize={item.dotSize}
                    domain={extractDomain(item.evidence.url)}
                    date={formatShortDate(item.date)}
                    isSelected={selectedEvidenceId === (item.evidence.evidenceId || item.evidence.id)}
                    positionPct={item.position}
                    onClick={() => handleNodeClick(item.evidence)}
                  />
                </div>
              );
            })}

            {/* Clusters — positioned at their dominant tier band */}
            {data.clusters.map((cluster, i) => {
              const dominantTier = cluster.items.some(it => it.evidence.tier === 'primary') ? 'primary'
                : cluster.items.some(it => it.evidence.tier === 'reporting') ? 'reporting'
                : 'commentary';
              const bandOffset = TIER_BAND_OFFSET[dominantTier] || TIER_BAND_OFFSET.commentary;
              return (
                <div
                  key={`cluster-${i}`}
                  className="absolute"
                  style={{
                    left: `${cluster.position}%`,
                    bottom: `${bandOffset}px`,
                    transform: 'translateX(-50%)',
                  }}
                >
                  <TimelineCluster
                    count={cluster.items.length}
                    items={cluster.items}
                    dominantColor={cluster.dominantColor}
                    onNodeClick={handleNodeClick}
                    selectedEvidenceId={selectedEvidenceId}
                    positionPct={cluster.position}
                  />
                </div>
              );
            })}
          </div>

          {/* Axis */}
          <TimelineAxis ticks={data.ticks} />
        </div>

        {/* Undated sidebar */}
        {data.undated.length > 0 && (
          <UndatedSidebar evidence={data.undated} onCardClick={handleNodeClick} />
        )}
      </div>

      {/* Mobile: vertical timeline */}
      <div className="md:hidden mb-8">
        <MobileTimeline
          items={data.items}
          clusters={data.clusters}
          undated={data.undated}
          onCardClick={handleNodeClick}
        />
      </div>

      {/* Evidence detail card */}
      {selectedEvidence && (
        <EvidenceDetailCard
          evidence={selectedEvidence}
          elementDescriptions={activeElementDescriptions}
          onClose={() => setSelectedEvidence(null)}
        />
      )}

      <ChronologistProvenanceNote hasUndated={data.undated.length > 0} />
    </div>
  );
}
