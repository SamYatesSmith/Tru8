'use client';

import type { ElementState } from '@shared/types';
import { ELEMENT_STATE_LABELS } from '@shared/constants';

interface ElementStateBadgeProps {
  state: ElementState;
  size?: 'sm' | 'md';
}

const STATE_ICONS: Record<ElementState, string> = {
  supported: '\u2713',
  disputed: '\u26A0',
  unresolved: '\u25CB',
  contextual: '\u24D8',
};

const STATE_CLASSES: Record<ElementState, string> = {
  supported: 'bg-state-supported/10 text-state-supported border-state-supported/20',
  disputed: 'bg-state-disputed/10 text-state-disputed border-state-disputed/20',
  unresolved: 'bg-state-unresolved/10 text-state-unresolved border-state-unresolved/20',
  contextual: 'bg-state-contextual/10 text-state-contextual border-state-contextual/20',
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
