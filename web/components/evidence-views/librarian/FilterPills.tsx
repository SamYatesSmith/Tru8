'use client';

import { EvidenceTier, EvidenceType } from '@shared/types';

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

interface FilterPillsProps {
  activeTiers: Set<EvidenceTier>;
  activeTypes: Set<EvidenceType>;
  onToggleTier: (tier: EvidenceTier) => void;
  onToggleType: (type: EvidenceType) => void;
  onClearAll: () => void;
}

export function FilterPills({ activeTiers, activeTypes, onToggleTier, onToggleType, onClearAll }: FilterPillsProps) {
  const hasActiveFilters = activeTiers.size > 0 || activeTypes.size > 0;

  return (
    <div className="flex flex-wrap items-center gap-3 mb-8">
      <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400 mr-2">Filter</span>

      {TIER_OPTIONS.map(({ value, label }) => (
        <button
          key={value}
          onClick={() => onToggleTier(value)}
          className={`filter-pill px-3 py-1.5 border border-zinc-200 text-[10px] font-mono font-bold uppercase tracking-wider ${
            activeTiers.has(value) ? 'active' : 'text-zinc-500 hover:border-zinc-400'
          }`}
        >
          {label}
        </button>
      ))}

      <div className="w-[1px] h-4 bg-zinc-200 mx-1 hidden lg:block"></div>

      {TYPE_OPTIONS.map(({ value, label }) => (
        <button
          key={value}
          onClick={() => onToggleType(value)}
          className={`filter-pill px-3 py-1.5 border border-zinc-200 text-[10px] font-mono font-bold uppercase tracking-wider ${
            activeTypes.has(value) ? 'active' : 'text-zinc-500 hover:border-zinc-400'
          }`}
        >
          {label}
        </button>
      ))}

      <div className="flex-grow"></div>

      {hasActiveFilters && (
        <button
          onClick={onClearAll}
          className="font-mono text-[9px] uppercase tracking-widest text-zinc-400 hover:text-zinc-900"
        >
          Clear all
        </button>
      )}
    </div>
  );
}
