'use client';

import { ClaimElement } from '@shared/types';

const STATE_BADGE_CONFIG: Record<string, { label: string; className: string }> = {
  supported: { label: 'Supported', className: 'bg-emerald-50 text-emerald-600' },
  disputed: { label: 'Disputed', className: 'bg-amber-50 text-amber-600' },
  unresolved: { label: 'Unresolved', className: 'bg-slate-50 text-slate-500' },
};

interface ElementRosterProps {
  elements: ClaimElement[];
  onElementClick?: (index: number) => void;
}

export function ElementRoster({ elements, onElementClick }: ElementRosterProps) {
  return (
    <div className="mb-16">
      <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-zinc-400 mb-6 border-b border-zinc-100 pb-2">
        Claim Elements
      </div>
      <div className="space-y-3">
        {elements.map((element, i) => {
          const sourceCount = element.evidenceRefs?.length || 0;
          const state = element.state || 'unresolved';
          const isGap = sourceCount === 0;
          const badge = STATE_BADGE_CONFIG[state] || STATE_BADGE_CONFIG.unresolved;

          return (
            <div
              key={element.elementId}
              className={`flex items-center gap-6 px-4 py-3 border transition-colors cursor-pointer ${
                isGap
                  ? 'border-dashed border-zinc-200 bg-zinc-50/30 hover:border-zinc-300'
                  : 'border-zinc-100 hover:border-zinc-300'
              }`}
              onClick={() => onElementClick?.(i)}
            >
              <span className="font-mono text-xs text-zinc-300">
                {String(i + 1).padStart(2, '0')}
              </span>
              <span className={`text-sm font-medium flex-grow ${isGap ? 'text-zinc-400' : 'text-zinc-900'}`}>
                {element.description}
              </span>
              <span className={`font-mono text-[10px] ${isGap ? 'text-zinc-300' : 'text-zinc-400'}`}>
                {sourceCount} {sourceCount === 1 ? 'source' : 'sources'}
              </span>
              <span className={`px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider rounded ${
                isGap ? 'bg-slate-50 text-slate-500' : badge.className
              }`}>
                {isGap ? 'Gap' : badge.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
