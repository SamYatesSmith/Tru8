'use client';

import { EvidenceTier, EvidenceType, EvidenceRelationship } from '@shared/types';

/**
 * The Evidence lens's filter panel (reworked 2026-09-10, second pass —
 * founder: the three free-floating strips "still do not look co-ordinated").
 *
 * ONE full-width bordered panel, three rows, one per axis. Every row is the
 * same shape — a fixed-width caption column on the left, pills filling the
 * rest — so the captions stack in a column and every row shares the same
 * left and right edge with the heatmap above and the ledger below. Rows are
 * divided by a rule; pills inside a row touch (shared borders). When anything
 * is active a fourth row states what the list now shows and offers Clear.
 *
 * The diagnostic switch is NOT here: it is a way of reading the ledger, not
 * a filter, so it lives in the ledger's own header beside Sort.
 *
 * The "Leans" axis is an organising axis, never an argument: no verdict
 * colour, no traffic light.
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
  /** Sources passing the current filters / sources in the landscape. Drives the status row. */
  shownCount: number;
  totalCount: number;
}

/** One axis row: caption column + pills. Borders between pills are collapsed
 *  with `-ml-px -mt-px` per pill (the view selector's idiom), so a wrapped
 *  second line of pills keeps its top edge. */
function FilterRow<T extends string>({
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
    <div role="group" aria-label={`${label} filter`} className="grid grid-cols-[4.5rem_1fr] border-t border-zinc-200 first:border-t-0">
      <span className="flex items-center px-3 bg-zinc-50 border-r border-zinc-200 font-mono text-[9px] uppercase tracking-widest text-zinc-400 select-none">
        {label}
      </span>
      <div className="flex flex-wrap pt-px pl-px">
        {options.map(({ value, label: optionLabel }) => {
          const isActive = active.has(value);
          return (
            <button
              key={value}
              type="button"
              aria-pressed={isActive}
              onClick={() => onToggle(value)}
              className={`-ml-px -mt-px relative px-3 min-h-[36px] border-t border-r border-zinc-200 font-mono text-[10px] uppercase tracking-wider transition-colors cursor-pointer ${
                isActive
                  ? 'z-10 bg-zinc-900 text-white border-zinc-900'
                  : 'text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900'
              }`}
            >
              {optionLabel}
            </button>
          );
        })}
      </div>
    </div>
  );
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

  // The status row names each active axis in the panel's own words and order.
  const activeSummary: { axis: string; values: string }[] = [];
  const pick = <T extends string>(options: { value: T; label: string }[], set: Set<T>) =>
    options.filter((o) => set.has(o.value)).map((o) => o.label).join(', ');
  if (activeTiers.size > 0) activeSummary.push({ axis: 'Tier', values: pick(TIER_OPTIONS, activeTiers) });
  if (activeTypes.size > 0) activeSummary.push({ axis: 'Type', values: pick(TYPE_OPTIONS, activeTypes) });
  if (activeRelationships.size > 0) activeSummary.push({ axis: 'Leans', values: pick(RELATIONSHIP_OPTIONS, activeRelationships) });

  return (
    <section aria-label="Filter the ledger" className="mb-6 border border-zinc-200 overflow-hidden">
      <FilterRow label="Tier" options={TIER_OPTIONS} active={activeTiers} onToggle={onToggleTier} />
      <FilterRow label="Type" options={TYPE_OPTIONS} active={activeTypes} onToggle={onToggleType} />
      <FilterRow label="Leans" options={RELATIONSHIP_OPTIONS} active={activeRelationships} onToggle={onToggleRelationship} />

      {hasActiveFilters && (
        <div
          role="status"
          className="grid grid-cols-[4.5rem_1fr] border-t border-zinc-200"
        >
          <span className="flex items-center px-3 bg-zinc-50 border-r border-zinc-200 font-mono text-[9px] uppercase tracking-widest text-[var(--accent)] select-none">
            Showing
          </span>
          <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1 px-3 py-2 text-[11px] text-zinc-600">
            <span>
              <span className="font-medium text-zinc-900">{shownCount}</span> of {totalCount}{' '}
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
        </div>
      )}
    </section>
  );
}
