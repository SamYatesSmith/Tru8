'use client';

import { ClaimElement } from '@shared/types';

const STATE_CONFIG: Record<string, { label: string; className: string; borderColor: string }> = {
  supported: {
    label: 'Supported',
    className: 'bg-emerald-50 text-emerald-600',
    borderColor: 'border-emerald-300',
  },
  disputed: {
    label: 'Disputed',
    className: 'bg-amber-50 text-amber-600',
    borderColor: 'border-amber-300',
  },
  unresolved: {
    label: 'Unresolved',
    className: 'bg-zinc-50 text-zinc-500',
    borderColor: 'border-zinc-300',
  },
};

interface ElementFocusPanelProps {
  element: ClaimElement;
  index: number;
  totalElements: number;
}

export function ElementFocusPanel({ element, index, totalElements }: ElementFocusPanelProps) {
  const state = element.state || 'unresolved';
  const config = STATE_CONFIG[state] || STATE_CONFIG.unresolved;

  return (
    <div className="border border-zinc-200 bg-[var(--surface-raised)] p-6 mb-0">
      <div className="flex items-start justify-between mb-4">
        <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">
          Element {String(index + 1).padStart(2, '0')} of {totalElements}
        </span>
        <span className={`px-2.5 py-1 text-[10px] font-mono font-bold uppercase tracking-wider rounded ${config.className}`}>
          {config.label}
        </span>
      </div>

      <h2 className="text-xl font-light tracking-tight text-zinc-900 mb-4 leading-relaxed">
        {element.description}
      </h2>

      {element.uncertainty && (
        <div className={`pl-4 border-l-2 ${config.borderColor}`}>
          <p className="text-[12px] text-zinc-500 italic leading-relaxed">
            {element.uncertainty}
          </p>
        </div>
      )}
    </div>
  );
}
