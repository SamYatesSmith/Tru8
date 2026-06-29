'use client';

import { ClaimElement } from '@shared/types';
import { ElementStateBadge, ElementStateKey } from '../ElementStateBadge';

interface ElementRosterProps {
  elements: ClaimElement[];
}

export function ElementRoster({ elements }: ElementRosterProps) {
  return (
    <div className="mb-16">
      <div className="font-mono text-sm font-bold uppercase tracking-[0.3em] text-zinc-600 mb-6 border-b border-zinc-200 pb-2">
        Elements
      </div>
      <div className="space-y-3">
        {elements.map((element, i) => {
          const sourceCount = element.evidenceRefs?.length || 0;
          const state = (element.state || 'unresolved') as ElementStateKey;
          const isGap = sourceCount === 0;

          return (
            <div
              key={element.elementId}
              className={`flex flex-col gap-1 lg:flex-row lg:items-center lg:gap-6 px-3 lg:px-4 py-3 border ${
                isGap
                  ? 'border-dashed border-zinc-200 bg-zinc-50/30'
                  : 'border-zinc-100'
              }`}
            >
              <div className="flex items-center gap-2 lg:contents">
                <span className="font-mono text-xs text-zinc-300">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <span className={`text-sm font-medium flex-grow ${isGap ? 'text-zinc-400' : 'text-zinc-900'}`}>
                  {element.description}
                </span>
              </div>
              <div className="flex items-center gap-3 pl-6 lg:pl-0 lg:contents">
                <span className={`font-mono text-[10px] ${isGap ? 'text-zinc-400' : 'text-zinc-500'}`}>
                  {sourceCount} {sourceCount === 1 ? 'source' : 'sources'}
                </span>
                <ElementStateBadge
                  state={isGap ? 'unresolved' : state}
                  label={isGap ? 'Gap' : undefined}
                  size="md"
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
