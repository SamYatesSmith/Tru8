'use client';

import { useState } from 'react';

type ViewTab = 'cartographer' | 'librarian' | 'interpreter' | 'seeker' | 'projectionist' | 'chronologist';

interface ViewSelectorProps {
  mode: 'overview' | 'detail';
  activeTab: string;
  onTabChange: (tab: string) => void;
}

/** Tabs that only make sense at the per-claim detail level. */
const DETAIL_ONLY_TABS: ViewTab[] = ['interpreter', 'seeker'];

const DETAIL_ONLY_TOOLTIPS: Record<string, string> = {
  interpreter: 'Available when viewing a specific claim — click a claim card above to explore its elements.',
  seeker: 'Available when viewing a specific claim — click a claim card above to surface unknowns.',
};

const ALL_TABS: { value: ViewTab; label: string }[] = [
  { value: 'cartographer', label: 'CARTOGRAPHER' },
  { value: 'librarian', label: 'LIBRARIAN' },
  { value: 'interpreter', label: 'INTERPRETER' },
  { value: 'seeker', label: 'SEEKER' },
  { value: 'projectionist', label: 'PROJECTIONIST' },
  { value: 'chronologist', label: 'CHRONOLOGIST' },
];

export function ViewSelector({ mode, activeTab, onTabChange }: ViewSelectorProps) {
  const [hoveredTab, setHoveredTab] = useState<string | null>(null);

  return (
    <div className="relative flex border-b border-zinc-200">
      {ALL_TABS.map((tab) => {
        const isDisabled = mode === 'overview' && DETAIL_ONLY_TABS.includes(tab.value);
        const isActive = activeTab === tab.value && !isDisabled;
        const showTooltip = isDisabled && hoveredTab === tab.value;

        return (
          <div key={tab.value} className="relative">
            <button
              onClick={() => !isDisabled && onTabChange(tab.value)}
              onMouseEnter={() => isDisabled && setHoveredTab(tab.value)}
              onMouseLeave={() => setHoveredTab(null)}
              className={`px-3 py-2.5 md:px-8 md:py-4 text-[9px] md:text-[11px] font-bold tracking-[0.15em] md:tracking-[0.25em] uppercase font-mono transition-colors ${
                isActive
                  ? 'border-b-2 border-[var(--accent)] text-black'
                  : isDisabled
                    ? 'text-zinc-200 cursor-default'
                    : 'text-zinc-400 hover:text-zinc-600'
              }`}
              disabled={isDisabled}
              aria-disabled={isDisabled}
            >
              {tab.label}
            </button>

            {/* Tooltip for disabled tabs */}
            {showTooltip && (
              <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 z-50 w-56 px-3 py-2 bg-zinc-900 text-white text-[10px] leading-relaxed rounded shadow-lg pointer-events-none">
                <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-zinc-900 rotate-45" />
                {DETAIL_ONLY_TOOLTIPS[tab.value]}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
