'use client';

export type SortField = 'date' | 'source' | 'tier' | 'element';

interface SortControlProps {
  value: SortField;
  onChange: (field: SortField) => void;
}

const SORT_LABELS: Record<SortField, string> = {
  date: 'Date',
  source: 'Source',
  tier: 'Tier',
  element: 'Element',
};

export function SortControl({ value, onChange }: SortControlProps) {
  return (
    <span className="text-zinc-400 font-normal">
      Sort:{' '}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as SortField)}
        className="font-mono text-[10px] uppercase tracking-widest text-zinc-400 bg-transparent border-none cursor-pointer focus:outline-none hover:text-zinc-900"
      >
        {Object.entries(SORT_LABELS).map(([key, label]) => (
          <option key={key} value={key}>
            {label}
          </option>
        ))}
      </select>
    </span>
  );
}
