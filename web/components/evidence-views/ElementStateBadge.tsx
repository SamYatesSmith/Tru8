/**
 * ElementStateBadge — single source of truth for claim-element state styling.
 *
 * Element states are MUTED, claim-context indicators — never page-level verdicts
 * (Stitch §2.2 colour lock). Includes the 4th `contextual` state (sky), which the
 * old inline configs omitted, so related-but-not-substantiating evidence is kept
 * visually distinct from a true gap.
 *
 * Two render shapes share one config:
 *   - `.text`  → text-colour class for inline state counts (e.g. ClaimHeader)
 *   - `.badge` → filled pill classes for roster/card badges
 */

export type ElementStateKey = 'supported' | 'disputed' | 'unresolved' | 'contextual';

export const ELEMENT_STATE: Record<
  ElementStateKey,
  { label: string; text: string; badge: string }
> = {
  supported: { label: 'Supported', text: 'text-emerald-500', badge: 'bg-emerald-50 text-emerald-600' },
  disputed: { label: 'Disputed', text: 'text-amber-500', badge: 'bg-amber-50 text-amber-600' },
  contextual: { label: 'Contextual', text: 'text-sky-500', badge: 'bg-sky-50 text-sky-600' },
  unresolved: { label: 'Unresolved', text: 'text-slate-500', badge: 'bg-slate-50 text-slate-500' },
};

// Two badge scales live in the app: the dense overview cards (`sm`) and the
// roomier detail roster (`md`). Kept as an explicit prop because this project
// has no tailwind-merge, so a `className` size override wouldn't reliably win.
const BADGE_SIZE = {
  sm: 'px-1.5 py-0.5 text-[9px]',
  md: 'px-2 py-0.5 text-[10px]',
} as const;

interface ElementStateBadgeProps {
  state: ElementStateKey;
  /** Override the displayed text (e.g. "Gap" for an unresolved element with no evidence). */
  label?: string;
  /** Badge scale — `sm` (overview cards, default) or `md` (the detail roster). */
  size?: keyof typeof BADGE_SIZE;
  className?: string;
}

export function ElementStateBadge({ state, label, size = 'sm', className = '' }: ElementStateBadgeProps) {
  const cfg = ELEMENT_STATE[state] ?? ELEMENT_STATE.unresolved;
  return (
    <span
      className={`${BADGE_SIZE[size]} font-mono font-bold uppercase tracking-wider shrink-0 rounded ${cfg.badge} ${className}`}
    >
      {label ?? cfg.label}
    </span>
  );
}
