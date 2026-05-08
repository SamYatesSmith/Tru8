'use client';

interface ClaimSelectionToolbarProps {
  count: number;
  selectAllLabel?: string;
  onSelectAll: () => void;
  onClear: () => void;
}

export function ClaimSelectionToolbar({
  count,
  selectAllLabel = 'Select all',
  onSelectAll,
  onClear,
}: ClaimSelectionToolbarProps) {
  return (
    <div className="flex items-center justify-between mb-6">
      <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-zinc-400">
        Extracted Claims &middot; {count}
      </div>
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onSelectAll}
          className="font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:text-zinc-900 transition-colors"
        >
          {selectAllLabel}
        </button>
        <span className="text-zinc-200">|</span>
        <button
          type="button"
          onClick={onClear}
          className="font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:text-zinc-900 transition-colors"
        >
          Clear
        </button>
      </div>
    </div>
  );
}
