'use client';

import { ClaimElement } from '@shared/types';

const STATE_BORDER_COLORS: Record<string, string> = {
  supported: '#10B981',
  disputed: '#F59E0B',
  unresolved: '#94A3B8',
};

const STATE_LABELS: Record<string, string> = {
  supported: 'Supported',
  disputed: 'Disputed',
  unresolved: 'Unresolved',
};

interface ElementSelectorProps {
  elements: ClaimElement[];
  activeIndex: number;
  onSelect: (index: number) => void;
}

export function ElementSelector({ elements, activeIndex, onSelect }: ElementSelectorProps) {
  return (
    <div className="flex flex-wrap gap-2 mb-8">
      {elements.map((element, i) => {
        const state = element.state || 'unresolved';
        const isActive = i === activeIndex;
        const borderColor = STATE_BORDER_COLORS[state] || STATE_BORDER_COLORS.unresolved;
        const hasEvidence = (element.evidenceRefs?.length || 0) > 0;
        const label = hasEvidence ? STATE_LABELS[state] || 'Unresolved' : 'Gap';

        return (
          <button
            key={element.elementId}
            onClick={() => onSelect(i)}
            className={`element-pill flex items-center gap-2 px-4 py-2 border text-[10px] font-mono font-bold uppercase tracking-wider ${
              isActive
                ? 'bg-zinc-900 text-white border-zinc-900'
                : 'border-zinc-200 text-zinc-500 hover:border-zinc-400'
            }`}
            style={{ borderLeft: `3px solid ${borderColor}` }}
          >
            {String(i + 1).padStart(2, '0')} {label}
          </button>
        );
      })}
    </div>
  );
}
