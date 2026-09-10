'use client';

import { EvidenceTier, EvidenceType, EvidenceRelationship } from '@shared/types';
import { SegmentedRow } from './SegmentedRow';

/**
 * The Evidence lens's filters (fresh approach, 2026-09-10 — after two cuts
 * the founder called "not co-ordinated" and then "garbled and jumbled").
 *
 * Three SegmentedRows — TIER / TYPE / LEANS — each a caption cell plus equal
 * cells filling the full width, exactly the view selector's shape. No dead
 * space to the right, no orphan cell: TYPE wraps into two equal rows of three
 * on a phone and is six across from `md`. The ledger's own controls
 * (highlight, sort) use the same row, so the whole block under the heatmap is
 * one instrument.
 *
 * A status line beneath, in the view selector's caption position, says what
 * the list now shows and offers Clear. "Leans" is an organising axis, never
 * an argument: no verdict colour, no traffic light.
 */

const TIER_OPTIONS: { value: EvidenceTier; label: string }[] = [
  { value: 'primary', label: 'Primary' },
  { value: 'reporting', label: 'Reporting' },
  { value: 'commentary', label: 'Commentary' },
];

const TYPE_OPTIONS: { value: EvidenceType; label: string }[] = [
  { value: 'data', label: 'Data' },
  { value: 'official_statement', label: 'Official' },
  { value: 'news_reporting', label: 'News' },
  { value: 'analysis', label: 'Analysis' },
  { value: 'opinion', label: 'Opinion' },
  { value: 'academic', label: 'Academic' },
];

const RELATIONSHIP_OPTIONS: { value: EvidenceRelationship; label: string }[] = [
  { value: 'supports', label: 'Supports' },
  { value: 'challenges', label: 'Challenges' },
  { value: 'context', label: 'Context' },
];

interface FilterPillsProps {
  activeTiers: Set<EvidenceTier>;
  activeTypes: Set<EvidenceType>;
  activeRelationships: Set<EvidenceRelationship>;
  onToggleTier: (tier: EvidenceTier) => void;
  onToggleType: (type: EvidenceType) => void;
  onToggleRelationship: (rel: EvidenceRelationship) => void;
  onClearAll: () => void;
  /** Sources passing the current filters / sources in the landscape. Drives the status line. */
  shownCount: number;
  totalCount: number;
}

export function FilterPills({
  activeTiers,
  activeTypes,
  activeRelationships,
  onToggleTier,
  onToggleType,
  onToggleRelationship,
  onClearAll,
  shownCount,
  totalCount,
}: FilterPillsProps) {
  const hasActiveFilters = activeTiers.size > 0 || activeTypes.size > 0 || activeRelationships.size > 0;

  const pick = <T extends string>(options: { value: T; label: string }[], set: Set<T>) =>
    options.filter((o) => set.has(o.value)).map((o) => o.label).join(', ');
  const activeSummary: { axis: string; values: string }[] = [];
  if (activeTiers.size > 0) activeSummary.push({ axis: 'Tier', values: pick(TIER_OPTIONS, activeTiers) });
  if (activeTypes.size > 0) activeSummary.push({ axis: 'Type', values: pick(TYPE_OPTIONS, activeTypes) });
  if (activeRelationships.size > 0) activeSummary.push({ axis: 'Leans', values: pick(RELATIONSHIP_OPTIONS, activeRelationships) });

  return (
    <section aria-label="Filter the ledger" className="mb-6">
      <div className="border border-zinc-300">
        <SegmentedRow label="Tier" ariaLabel="Tier filter" options={TIER_OPTIONS} active={activeTiers} onSelect={onToggleTier} />
        <SegmentedRow label="Type" ariaLabel="Type filter" options={TYPE_OPTIONS} active={activeTypes} onSelect={onToggleType} cols="grid-cols-3 md:grid-cols-6" />
        <SegmentedRow label="Leans" ariaLabel="Leans filter" options={RELATIONSHIP_OPTIONS} active={activeRelationships} onSelect={onToggleRelationship} />
      </div>

      {/* The view selector's caption position: one line, plain words. */}
      <p role="status" className="mt-2 flex flex-wrap items-baseline gap-x-2 gap-y-0.5 text-xs text-zinc-500 min-h-[1.25rem]">
        {hasActiveFilters ? (
          <>
            <span>
              Showing <span className="font-medium text-zinc-700">{shownCount}</span> of {totalCount}{' '}
              {totalCount === 1 ? 'source' : 'sources'}
            </span>
            {activeSummary.map(({ axis, values }) => (
              <span key={axis}>
                <span aria-hidden className="text-zinc-300">· </span>
                <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">{axis} </span>
                <span className="text-zinc-700">{values}</span>
              </span>
            ))}
            <button
              type="button"
              onClick={onClearAll}
              className="ml-auto font-mono text-[9px] uppercase tracking-widest text-zinc-400 hover:text-[var(--accent)] transition-colors cursor-pointer"
            >
              Clear all
            </button>
          </>
        ) : (
          <span>
            Select any cells to narrow the ledger — {totalCount} {totalCount === 1 ? 'source' : 'sources'} shown.
          </span>
        )}
      </p>
    </section>
  );
}
