'use client';

import { useMemo } from 'react';
import { Claim, Evidence } from '@shared/types';
import { TemporalInsightStrip } from './TemporalInsightStrip';
import { TimelineAxis } from './TimelineAxis';
import { TimelineNode } from './TimelineNode';
import { TimelineCluster } from './TimelineCluster';
import { UndatedSidebar } from './UndatedSidebar';
import { MobileTimeline } from './MobileTimeline';
import { ChronologistProvenanceNote } from './ChronologistProvenanceNote';

// Check-wide scope: colour by claim (5-colour palette)
const CLAIM_COLORS = [
  'var(--accent)',   // orange
  '#3B82F6',         // blue-500
  '#8B5CF6',         // violet-500
  '#10B981',         // emerald-500
  '#F59E0B',         // amber-500
];

// Per-claim scope: colour by evidence relationship to elements
const RELATIONSHIP_COLORS: Record<string, string> = {
  supports: 'var(--disposition-supports)',
  challenges: 'var(--disposition-challenges)',
  context: 'var(--disposition-context)',
};

// --- Exported types consumed by child components ---

export interface DatedItem {
  evidence: Evidence;
  date: Date;
  color: string;
  label: string;
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

function extractDomain(url: string): string {
  try { return new URL(url).hostname.replace(/^www\./, ''); } catch { return url; }
}

function formatShortDate(date: Date): string {
  return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
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

/** Determine the dominant relationship for an evidence item within a claim. */
function getPrimaryRelationship(evidenceId: string, claim: Claim): string {
  const counts: Record<string, number> = { supports: 0, challenges: 0, context: 0 };
  for (const el of claim.claimMap?.elements || []) {
    for (const ref of el.evidenceRefs || []) {
      if (ref.evidenceId === evidenceId) {
        counts[ref.relationship || 'context']++;
      }
    }
  }
  return Object.entries(counts).reduce(
    (max, [rel, count]) => (count > max[1] ? [rel, count] : max),
    ['context', 0] as [string, number],
  )[0];
}

// --- Component ---

interface ChronologistViewProps {
  scope: 'check' | 'claim';
  claims: Claim[];
  onSwitchToLibrarian?: () => void;
}

export function ChronologistView({ scope, claims, onSwitchToLibrarian }: ChronologistViewProps) {
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

    // 2. Partition dated vs undated
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

    // 3. Threshold check (≥50% must have dates)
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
        clusterCount: 0,
        gapCount: 0,
      };
    }

    // 4. Sort by date, determine bounds
    dated.sort((a, b) => a.date.getTime() - b.date.getTime());
    const earliest = dated[0].date;
    const latest = dated[dated.length - 1].date;

    // 5. Assign colours
    const coloredDated: DatedItem[] = dated.map(({ evidence, date, claimIdx }) => {
      const evId = evidence.evidenceId || evidence.id;
      let color: string;
      let label: string;

      if (scope === 'check') {
        color = CLAIM_COLORS[claimIdx % CLAIM_COLORS.length];
        label = `Claim ${String(claimIdx + 1).padStart(2, '0')}`;
      } else {
        const rel = getPrimaryRelationship(evId, claims[0]);
        color = RELATIONSHIP_COLORS[rel] || RELATIONSHIP_COLORS.context;
        label = rel.charAt(0).toUpperCase() + rel.slice(1);
      }

      return { evidence, date, color, label, position: 0, yLevel: 0 };
    });

    // 6. Group by calendar date
    const groups = new Map<string, DatedItem[]>();
    for (const item of coloredDated) {
      const key = item.date.toISOString().slice(0, 10);
      const group = groups.get(key) || [];
      group.push(item);
      groups.set(key, group);
    }

    // 7. Separate positioned items vs clusters (3+ on same day)
    const items: DatedItem[] = [];
    const clusters: ClusterItem[] = [];

    Array.from(groups.values()).forEach((group) => {
      const pos = getPosition(group[0].date, earliest, latest);

      if (group.length >= 3) {
        clusters.push({
          date: group[0].date,
          items: group.map((g, i) => ({ ...g, position: pos, yLevel: i })),
          position: pos,
          dominantColor: group[0].color,
        });
      } else {
        group.forEach((item, i) => {
          items.push({ ...item, position: pos, yLevel: i });
        });
      }
    });

    // 8. Generate axis ticks
    const ticks = generateTicks(earliest, latest);

    // 9. Detect gaps (30+ days between consecutive evidence)
    const gaps: GapZone[] = [];
    for (let i = 1; i < dated.length; i++) {
      const diffDays = (dated[i].date.getTime() - dated[i - 1].date.getTime()) / (1000 * 60 * 60 * 24);
      if (diffDays > 30) {
        gaps.push({
          startPos: getPosition(dated[i - 1].date, earliest, latest),
          endPos: getPosition(dated[i].date, earliest, latest),
        });
      }
    }

    // 10. Today marker (only if within or just past range)
    const today = new Date();
    let todayPosition: number | null = null;
    if (today >= earliest && today <= latest) {
      todayPosition = getPosition(today, earliest, latest);
    } else if (today > latest) {
      // Show at 100% if today is past the latest date (within reason)
      const daysPast = (today.getTime() - latest.getTime()) / (1000 * 60 * 60 * 24);
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
      clusterCount: clusters.length,
      gapCount: gaps.length,
    };
  }, [claims, scope]);

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
        clusterCount={data.clusterCount}
        gapCount={data.gapCount}
      />

      {/* Desktop: horizontal timeline + undated sidebar */}
      <div className="hidden md:flex gap-6 mb-8">
        <div className="flex-grow min-w-0">
          {/* Timeline content area */}
          <div className="relative" style={{ minHeight: '200px' }}>
            {/* Gap zones */}
            {data.gaps.map((gap, i) => (
              <div
                key={`gap-${i}`}
                className="absolute top-0 bottom-8 bg-zinc-50/50 border-x border-dashed border-zinc-200"
                style={{ left: `${gap.startPos}%`, width: `${gap.endPos - gap.startPos}%` }}
              />
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

            {/* Individual nodes */}
            {data.items.map((item, i) => (
              <div
                key={`node-${i}`}
                className="absolute"
                style={{
                  left: `${item.position}%`,
                  bottom: `${32 + item.yLevel * 28}px`,
                  transform: 'translateX(-50%)',
                }}
              >
                <TimelineNode
                  color={item.color}
                  title={item.evidence.title || 'Untitled'}
                  domain={extractDomain(item.evidence.url)}
                  date={formatShortDate(item.date)}
                  tier={item.evidence.tier}
                  url={item.evidence.url}
                  label={item.label}
                />
              </div>
            ))}

            {/* Clusters */}
            {data.clusters.map((cluster, i) => (
              <div
                key={`cluster-${i}`}
                className="absolute"
                style={{
                  left: `${cluster.position}%`,
                  bottom: '28px',
                  transform: 'translateX(-50%)',
                }}
              >
                <TimelineCluster
                  count={cluster.items.length}
                  items={cluster.items}
                  dominantColor={cluster.dominantColor}
                />
              </div>
            ))}
          </div>

          {/* Axis */}
          <TimelineAxis ticks={data.ticks} />
        </div>

        {/* Undated sidebar */}
        {data.undated.length > 0 && (
          <UndatedSidebar evidence={data.undated} />
        )}
      </div>

      {/* Mobile: vertical timeline */}
      <div className="md:hidden mb-8">
        <MobileTimeline
          items={data.items}
          clusters={data.clusters}
          undated={data.undated}
        />
      </div>

      <ChronologistProvenanceNote />
    </div>
  );
}
