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

const ALL_TABS: { value: ViewTab; label: string; subtitle: string }[] = [
  { value: 'cartographer', label: 'CARTOGRAPHER', subtitle: 'Shape of the conversation' },
  { value: 'librarian', label: 'LIBRARIAN', subtitle: 'Full evidence set, classified' },
  { value: 'interpreter', label: 'INTERPRETER', subtitle: 'Does this answer the question?' },
  { value: 'seeker', label: 'SEEKER', subtitle: "What don't we know yet?" },
  { value: 'projectionist', label: 'PROJECTIONIST', subtitle: "What's been said on camera?" },
  { value: 'chronologist', label: 'CHRONOLOGIST', subtitle: 'When did evidence appear?' },
];

export function ViewSelector({ mode, activeTab, onTabChange }: ViewSelectorProps) {
  const [hoveredTab, setHoveredTab] = useState<string | null>(null);

  return (
    <div className="relative flex justify-between border-b border-zinc-200 mb-6">
      {ALL_TABS.map((tab) => {
        const isDisabled = mode === 'overview' && DETAIL_ONLY_TABS.includes(tab.value);
        const isActive = activeTab === tab.value && !isDisabled;
        const showTooltip = isDisabled && hoveredTab === tab.value;

        return (
          <div key={tab.value} className="relative flex-1 text-center group">
            <button
              onClick={() => !isDisabled && onTabChange(tab.value)}
              onMouseEnter={() => isDisabled && setHoveredTab(tab.value)}
              onMouseLeave={() => setHoveredTab(null)}
              className={`w-full px-2 py-2.5 md:px-4 md:py-4 font-bold uppercase font-mono transition-all duration-200 ${
                isActive
                  ? 'border-b-2 border-[var(--accent)] text-black text-[10px] md:text-[13px] tracking-[0.15em] md:tracking-[0.25em]'
                  : isDisabled
                    ? 'text-zinc-200 cursor-default text-[9px] md:text-[11px] tracking-[0.15em] md:tracking-[0.25em]'
                    : 'text-zinc-400 text-[9px] md:text-[11px] tracking-[0.15em] md:tracking-[0.25em] hover:text-zinc-800 hover:text-[10px] hover:md:text-[13px]'
              }`}
              disabled={isDisabled}
              aria-disabled={isDisabled}
            >
              {tab.label}
              <span className={`hidden md:block font-normal tracking-normal normal-case font-sans mt-0.5 transition-all duration-200 ${
                isActive
                  ? 'text-zinc-500 text-[9px]'
                  : isDisabled
                    ? 'text-zinc-200 text-[8px]'
                    : 'text-zinc-400 text-[8px] group-hover:text-[9px] group-hover:text-zinc-500'
              }`}>
                {tab.subtitle}
              </span>
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
