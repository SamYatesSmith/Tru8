'use client';

import { useState } from 'react';
import { capture } from '@/lib/analytics';

export type ViewTab = 'cartographer' | 'librarian' | 'correspondent' | 'seeker' | 'projectionist' | 'chronologist';

interface ViewSelectorProps {
  mode: 'overview' | 'detail';
  activeTab: string;
  onTabChange: (tab: string) => void;
  hiddenTabs?: ViewTab[];
}

/** Tabs that only make sense at the per-claim detail level. */
const DETAIL_ONLY_TABS: ViewTab[] = ['seeker'];

const DETAIL_ONLY_TOOLTIPS: Record<string, string> = {
  seeker: 'Available when viewing a specific claim — click a claim card above to surface unknowns.',
};

// Plain-language label leads; the profession is kept as flavour in the subtitle
// (D-R1, §7.4). `value` strings are unchanged — ?view= deep links stay stable.
// Order leads with Evidence (the default lens, §7.2.2).
export const ALL_TABS: { value: ViewTab; label: string; subtitle: string }[] = [
  { value: 'librarian', label: 'EVIDENCE', subtitle: 'Librarian · full classified set' },
  { value: 'correspondent', label: 'SOURCES', subtitle: "Correspondent · who's in the room" },
  { value: 'chronologist', label: 'TIMELINE', subtitle: 'Chronologist · when evidence appeared' },
  { value: 'seeker', label: 'GAPS', subtitle: "Seeker · what we don't know yet" },
  { value: 'cartographer', label: 'MAP', subtitle: 'Cartographer · shape of the conversation' },
  { value: 'projectionist', label: 'VIDEO', subtitle: 'Projectionist · on camera' },
];

export function ViewSelector({ mode, activeTab, onTabChange, hiddenTabs = [] }: ViewSelectorProps) {
  const [hoveredTab, setHoveredTab] = useState<string | null>(null);
  const visibleTabs = ALL_TABS.filter(tab => !hiddenTabs.includes(tab.value));

  return (
    <div className="relative grid grid-cols-3 lg:flex lg:justify-between border-b border-zinc-200 mb-6">
      {visibleTabs.map((tab) => {
        const isDisabled = mode === 'overview' && DETAIL_ONLY_TABS.includes(tab.value);
        const isActive = activeTab === tab.value && !isDisabled;
        const showTooltip = isDisabled && hoveredTab === tab.value;

        return (
          <div key={tab.value} className="relative text-center lg:flex-1 group">
            <button
              onClick={() => {
                if (isDisabled) return;
                if (tab.value !== activeTab) capture('view_opened', { view: tab.value });
                onTabChange(tab.value);
              }}
              onMouseEnter={() => isDisabled && setHoveredTab(tab.value)}
              onMouseLeave={() => setHoveredTab(null)}
              className={`w-full min-h-[44px] px-2 py-2.5 lg:px-4 lg:py-4 font-bold uppercase font-mono transition-all duration-200 ${
                isActive
                  ? 'border-b-2 border-[var(--accent)] text-black text-[10px] lg:text-[13px] tracking-[0.08em] lg:tracking-[0.25em]'
                  : isDisabled
                    ? 'text-zinc-200 cursor-default text-[9px] lg:text-[11px] tracking-[0.08em] lg:tracking-[0.25em]'
                    : 'text-zinc-400 text-[9px] lg:text-[11px] tracking-[0.08em] lg:tracking-[0.25em] hover:text-zinc-800 hover:text-[10px] hover:lg:text-[13px]'
              }`}
              disabled={isDisabled}
              aria-disabled={isDisabled}
            >
              {tab.label}
              <span className={`hidden lg:block font-normal tracking-normal normal-case font-sans mt-0.5 transition-all duration-200 ${
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
