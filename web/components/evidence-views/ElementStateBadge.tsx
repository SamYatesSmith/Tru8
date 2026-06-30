/**
 * ElementStateBadge — single source of truth for claim-element state styling.
 *
 * Element states are MUTED, claim-context indicators — never page-level verdicts
 * (Stitch §2.2 colour lock). Includes the 4th `contextual` state (sky), which the
 * old inline configs omitted, so related-but-not-substantiating evidence is kept
 * visually distinct from a true gap.
 *
 * Two render shapes share one config:
 *   - `.text`  → text-colour class for inline state counts (e.g. ClaimSummaryPanel)
 *   - `.badge` → filled pill classes for roster/card badges
 */

export type ElementStateKey = 'supported' | 'disputed' | 'unresolved' | 'contextual';

// NEUTRAL by design (no-verdict colour lock): state is differentiated by ICON +
// tonal WEIGHT + filled-vs-outline, never by green/amber. supported = filled dark
// (most-evidenced, by weight not hue); disputed = outlined (contested); contextual
// = light fill; unresolved = dashed outline (open). The word carries the meaning.
export const ELEMENT_STATE: Record<
  ElementStateKey,
  { label: string; icon: string; text: string; badge: string }
> = {
  supported: { label: 'Supported', icon: '+', text: 'text-zinc-700', badge: 'bg-zinc-800 text-white border border-zinc-800' },
  disputed: { label: 'Disputed', icon: '±', text: 'text-zinc-700', badge: 'bg-white text-zinc-800 border border-zinc-400' },
  contextual: { label: 'Contextual', icon: 'ⓘ', text: 'text-zinc-500', badge: 'bg-zinc-100 text-zinc-600 border border-zinc-200' },
  unresolved: { label: 'Unresolved', icon: '○', text: 'text-zinc-500', badge: 'bg-white text-zinc-500 border border-dashed border-zinc-300' },
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
      className={`${BADGE_SIZE[size]} inline-flex items-center gap-1 font-mono font-bold uppercase tracking-wider shrink-0 rounded ${cfg.badge} ${className}`}
    >
      <span aria-hidden className="not-italic">{cfg.icon}</span>
      {label ?? cfg.label}
    </span>
  );
}
