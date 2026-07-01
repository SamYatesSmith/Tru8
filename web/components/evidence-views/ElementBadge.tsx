/**
 * ElementBadge — the element reference token.
 *
 * A circular, orange-ringed number that introduces each sub-element in the digest
 * roster and re-appears wherever that element is cited across the report, so a
 * reader can follow "Element 03" by sight. The circle deliberately rhymes with the
 * source favicons (a first-class, recurring entity), and orange is the app's
 * wayfinding/interaction accent — NEVER a stance/verdict colour (no-verdict lock).
 *
 * `n` is the element's 1-based position within its claim, which matches every lens
 * at claim-detail altitude (element ids are `e1..eN` in order). `md` for the roster
 * / standalone references, `sm` for inline and dense contexts.
 */
interface ElementBadgeProps {
  /** 1-based element number within the claim. */
  n: number;
  size?: 'sm' | 'md';
  className?: string;
}

const SIZE = {
  sm: 'w-5 h-5 text-[9px]',
  md: 'w-7 h-7 text-[11px]',
} as const;

/** Parse the 1-based element number out of an element id (`e3` → 3). */
export function elementNumberFromId(id: string): number {
  return parseInt(id.replace(/^e/i, ''), 10) || 0;
}

export function ElementBadge({ n, size = 'sm', className = '' }: ElementBadgeProps) {
  const label = String(n).padStart(2, '0');
  return (
    <span
      role="img"
      aria-label={`Element ${label}`}
      className={`${SIZE[size]} inline-flex items-center justify-center shrink-0 rounded-full border bg-white font-mono font-bold text-zinc-700 leading-none ${className}`}
      style={{ borderColor: 'var(--accent)' }}
    >
      {label}
    </span>
  );
}
