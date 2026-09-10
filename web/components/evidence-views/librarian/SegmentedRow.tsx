'use client';

/**
 * SegmentedRow — the Evidence lens's ONE control shape (2026-09-10).
 *
 * A caption cell on the left, then equal-width cells filling the rest of the
 * row, edge to edge — the view selector's idiom, applied to every control
 * under the heatmap (filters, highlight, sort) so the block reads as one
 * instrument rather than three different widgets. Cells are equal on every
 * screen; a row with many cells wraps into equal thirds on a phone via
 * `cols` (e.g. `grid-cols-3 md:grid-cols-6`). Borders collapse with the
 * `-ml-px -mt-px` trick so a wrapped line keeps its top edge.
 *
 * Active = filled dark (fill + white + weight — never a stance colour; the
 * orange dot on the highlight row is a wayfinding accent).
 */
export interface SegmentOption<T extends string> {
  value: T;
  label: string;
  /** Optional leading mark (e.g. the highlight row's dot). */
  mark?: React.ReactNode;
}

interface SegmentedRowProps<T extends string> {
  label: string;
  options: SegmentOption<T>[];
  /** Which cells are active. Multi-select rows pass a Set; single-select rows a Set of one. */
  active: Set<T>;
  onSelect: (value: T) => void;
  /** Tailwind grid columns for the cell area (phone first). Default: one column per option. */
  cols?: string;
  /** ARIA name for the group. */
  ariaLabel?: string;
}

const DEFAULT_COLS: Record<number, string> = {
  1: 'grid-cols-1',
  2: 'grid-cols-2',
  3: 'grid-cols-3',
  4: 'grid-cols-4',
  5: 'grid-cols-5',
  6: 'grid-cols-6',
};

export function SegmentedRow<T extends string>({ label, options, active, onSelect, cols, ariaLabel }: SegmentedRowProps<T>) {
  return (
    <div role="group" aria-label={ariaLabel ?? label} className="flex border-t border-zinc-300 first:border-t-0">
      <span className="w-[4.5rem] shrink-0 flex items-center px-3 bg-zinc-50 border-r border-zinc-300 font-mono text-[9px] uppercase tracking-widest text-zinc-500 select-none">
        {label}
      </span>
      <div className={`flex-1 grid ${cols ?? DEFAULT_COLS[options.length] ?? 'grid-cols-3'} pl-px pt-px`}>
        {options.map(({ value, label: optionLabel, mark }) => {
          const isActive = active.has(value);
          return (
            <button
              key={value}
              type="button"
              aria-pressed={isActive}
              onClick={() => onSelect(value)}
              className={`-ml-px -mt-px relative min-h-[40px] px-2 border border-zinc-200 inline-flex items-center justify-center gap-1.5 font-mono text-[10px] uppercase tracking-wider text-center transition-colors cursor-pointer ${
                isActive
                  ? 'z-10 bg-zinc-900 text-white border-zinc-900 font-bold'
                  : 'bg-white text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900'
              }`}
            >
              {mark}
              {optionLabel}
            </button>
          );
        })}
      </div>
    </div>
  );
}
