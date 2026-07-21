'use client';

import type { ElementBasis, ElementState } from '@shared/types';
import {
  CHALLENGED_GLYPH,
  CHALLENGED_LABEL,
  ELEMENT_STATE_LABELS,
  isChallengesOnly,
} from '@shared/constants';

interface ElementStateBadgeProps {
  state: ElementState;
  size?: 'sm' | 'md';
  /** Element basis — lets a challenges-only disputed element read "− Challenged". */
  basis?: ElementBasis;
}

// Neutral icons (no verdict glyphs): + supports-weighted, \u00B1 contested, \u25CB open,
// \u24D8 contextual. Colour neutralised below \u2014 no green/amber on state.
const STATE_ICONS: Record<ElementState, string> = {
  supported: '+',
  disputed: '\u00B1',
  unresolved: '\u25CB',
  contextual: '\u24D8',
};

// NEUTRAL (no-verdict colour lock): tonal weight + filled-vs-outline, never hue.
const STATE_CLASSES: Record<ElementState, string> = {
  supported: 'bg-zinc-800 text-white border-zinc-800',
  disputed: 'bg-white text-zinc-800 border-zinc-400',
  unresolved: 'bg-white text-zinc-500 border-dashed border-zinc-300',
  contextual: 'bg-zinc-100 text-zinc-600 border-zinc-200',
};

const SIZE_CLASSES = {
  sm: 'text-[9px] px-1.5 py-0.5',
  md: 'text-[10px] px-2 py-1',
};

export function ElementStateBadge({ state, size = 'md', basis }: ElementStateBadgeProps) {
  const challengesOnly = isChallengesOnly(state, basis);
  const glyph = challengesOnly ? CHALLENGED_GLYPH : STATE_ICONS[state];
  const label = challengesOnly ? CHALLENGED_LABEL : ELEMENT_STATE_LABELS[state];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border font-bold uppercase tracking-wider font-mono ${STATE_CLASSES[state]} ${SIZE_CLASSES[size]}`}
    >
      <span>{glyph}</span>
      <span>{label}</span>
    </span>
  );
}
