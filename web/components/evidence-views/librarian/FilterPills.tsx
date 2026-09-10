'use client';

import { EvidenceTier, EvidenceType, EvidenceRelationship } from '@shared/types';

/**
 * The Evidence lens's filter bar (reworked 2026-09-10 — founder: "not
 * particularly clear", all screen sizes).
 *
 * Before: twelve identical pills in one wrapping row, the only structure two
 * hairline dividers hidden below `lg`, a Diagnostic toggle orphaned beneath,
 * and no feedback on what the filters had done to the list. Three different
 * questions read as one list, and the wrap split a group wherever the width
 * happened to fall.
 *
 * Now: THREE LABELLED GROUPS that wrap as units — one segmented strip per axis
 * (caption cell + touching pills, shared borders like the view selector) —
 * the diagnostic switch on the same row, right-aligned, labelled for what it
 * does (a view mode, not a filter), and ONE STATUS LINE under the bar whenever
 * anything is active: "Showing 7 of 13 sources · Tier Primary · Leans
 * Supports · Clear all". Captions use the guide's words (Tier / Type) plus
 * "Leans" for the disposition axis — an organising axis, never an argument:
 * no verdict colour, no traffic light.
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
  /** The diagnostic-weighting view switch. Absent when the check has no diagnostic variance. */
  diagnostic?: { active: boolean; onToggle: () => void };
}

/** One axis: a caption cell followed by its pills, borders collapsed into a
 *  single strip (`-ml-px -mt-px` per cell, as the view selector does), so the
 *  group reads as ONE control and a wrapped row keeps its top border. */
function FilterGroup<T extends string>({
  label,
  options,
  active,
  onToggle,
}: {
  label: string;
  options: { value: T; label: string }[];
  active: Set<T>;
  onToggle: (value: T) => void;
}) {
  return (
    <div role="group" aria-label={`${label} filter`} className="flex flex-wrap pl-px pt-px max-w-full">
      <span className="-ml-px -mt-px inline-flex items-center px-2.5 min-h-[32px] border border-zinc-200 bg-zinc-50 font-mono text-[9px] uppercase tracking-widest text-zinc-400 select-none">
        {label}
      </span>
      {options.map(({ value, label: optionLabel }) => {
        const isActive = active.has(value);
        return (
          <button
            key={value}
            type="button"
            aria-pressed={isActive}
            onClick={() => onToggle(value)}
            className={`-ml-px -mt-px relative px-3 min-h-[32px] border font-mono text-[10px] uppercase tracking-wider transition-colors cursor-pointer ${
              isActive
                ? 'z-10 bg-zinc-900 text-white border-zinc-900'
                : 'bg-white text-zinc-600 border-zinc-200 hover:text-zinc-900 hover:border-zinc-400 hover:z-10'
            }`}
          >
            {optionLabel}
          </button>
        );
      })}
    </div>
  );
}

const TIER_LABEL = Object.fromEntries(TIER_OPTIONS.map((o) => [o.value, o.label])) as Record<EvidenceTier, string>;
const TYPE_LABEL = Object.fromEntries(TYPE_OPTIONS.map((o) => [o.value, o.label])) as Record<EvidenceType, string>;
const REL_LABEL = Object.fromEntries(RELATIONSHIP_OPTIONS.map((o) => [o.value, o.label])) as Record<EvidenceRelationship, string>;

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
  diagnostic,
}: FilterPillsProps) {
  const hasActiveFilters = activeTiers.size > 0 || activeTypes.size > 0 || activeRelationships.size > 0;

  // The status line names each active axis in the bar's own words, in the
  // bar's own order, so the reader can see at a glance why the list is short.
  const activeSummary: { axis: string; values: string }[] = [];
  if (activeTiers.size > 0) activeSummary.push({ axis: 'Tier', values: TIER_OPTIONS.filter((o) => activeTiers.has(o.value)).map((o) => TIER_LABEL[o.value]).join(', ') });
  if (activeTypes.size > 0) activeSummary.push({ axis: 'Type', values: TYPE_OPTIONS.filter((o) => activeTypes.has(o.value)).map((o) => TYPE_LABEL[o.value]).join(', ') });
  if (activeRelationships.size > 0) activeSummary.push({ axis: 'Leans', values: RELATIONSHIP_OPTIONS.filter((o) => activeRelationships.has(o.value)).map((o) => REL_LABEL[o.value]).join(', ') });

  return (
    <div className="mb-6">
      <div className="flex flex-wrap items-start gap-x-4 gap-y-3">
        <FilterGroup label="Tier" options={TIER_OPTIONS} active={activeTiers} onToggle={onToggleTier} />
        <FilterGroup label="Type" options={TYPE_OPTIONS} active={activeTypes} onToggle={onToggleType} />
        <FilterGroup label="Leans" options={RELATIONSHIP_OPTIONS} active={activeRelationships} onToggle={onToggleRelationship} />

        {/* A view mode, not a filter: right-aligned on the same row from `sm`,
            its own line on a phone. Orange dot when on — a wayfinding accent,
            never a stance. */}
        {diagnostic && (
          <button
            type="button"
            aria-pressed={diagnostic.active}
            onClick={diagnostic.onToggle}
            title="Weight the ledger by how much each source helps tell the claim's possibilities apart"
            className={`basis-full sm:basis-auto sm:ml-auto inline-flex items-center justify-center gap-2 px-3 min-h-[32px] border font-mono text-[10px] uppercase tracking-widest transition-colors cursor-pointer ${
              diagnostic.active
                ? 'bg-zinc-900 text-white border-zinc-900'
                : 'bg-white text-zinc-500 border-zinc-200 hover:text-zinc-900 hover:border-zinc-400'
            }`}
          >
            <span aria-hidden className={`w-2 h-2 rounded-full ${diagnostic.active ? 'bg-[var(--accent)]' : 'bg-zinc-300'}`} />
            Diagnostic weighting
          </button>
        )}
      </div>

      {hasActiveFilters && (
        <div
          role="status"
          className="mt-3 flex flex-wrap items-baseline gap-x-2 gap-y-1 border-l-2 border-[var(--accent)] pl-3 py-0.5 text-[11px] text-zinc-600"
        >
          <span>
            Showing <span className="font-medium text-zinc-900">{shownCount}</span> of {totalCount}{' '}
            {totalCount === 1 ? 'source' : 'sources'}
          </span>
          {activeSummary.map(({ axis, values }) => (
            <span key={axis} className="inline-flex items-baseline gap-1.5">
              <span aria-hidden className="text-zinc-300">·</span>
              <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">{axis}</span>
              <span>{values}</span>
            </span>
          ))}
          <button
            type="button"
            onClick={onClearAll}
            className="ml-auto font-mono text-[9px] uppercase tracking-widest text-zinc-400 hover:text-zinc-900 transition-colors cursor-pointer"
          >
            Clear all
          </button>
        </div>
      )}
    </div>
  );
}
