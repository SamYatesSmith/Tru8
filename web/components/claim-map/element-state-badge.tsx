'use client';

import type { ElementState } from '@shared/types';
import { ELEMENT_STATE_LABELS } from '@shared/constants';

interface ElementStateBadgeProps {
  state: ElementState;
  size?: 'sm' | 'md';
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

export function ElementStateBadge({ state, size = 'md' }: ElementStateBadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border font-bold uppercase tracking-wider font-mono ${STATE_CLASSES[state]} ${SIZE_CLASSES[size]}`}
    >
      <span>{STATE_ICONS[state]}</span>
      <span>{ELEMENT_STATE_LABELS[state]}</span>
    </span>
  );
}
