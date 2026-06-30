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

// Action label leads; the SUBTITLE is the QUESTION each lens answers (the value
// signpost — NN/g information scent; fixes the bare "VIDEO" format-label). The
// profession is internal only (kept in this comment, not user-facing):
//   librarian=Evidence · correspondent=Sources · chronologist=Timeline ·
//   seeker=Gaps · cartographer=Map · projectionist=Video.
// `value` strings are unchanged — ?view= deep links stay stable. Order leads
// with Evidence (the recommended default lens).
export const ALL_TABS: { value: ViewTab; label: string; subtitle: string }[] = [
  { value: 'librarian', label: 'EVIDENCE', subtitle: 'What does the evidence say?' },
  { value: 'correspondent', label: 'SOURCES', subtitle: 'Is the full set here?' },
  { value: 'chronologist', label: 'TIMELINE', subtitle: 'When did it appear?' },
  { value: 'seeker', label: 'GAPS', subtitle: "What don't we know yet?" },
  { value: 'cartographer', label: 'MAP', subtitle: 'Shape of the debate?' },
  { value: 'projectionist', label: 'VIDEO', subtitle: "What's said on camera?" },
];

export function ViewSelector({ mode, activeTab, onTabChange, hiddenTabs = [] }: ViewSelectorProps) {
  const [hoveredTab, setHoveredTab] = useState<string | null>(null);
  const visibleTabs = ALL_TABS.filter((tab) => !hiddenTabs.includes(tab.value));
  // Active tab's question — surfaced as a caption on mobile, where the per-tab
  // subtitles are hidden (so the wayfinding scent isn't desktop-only).
  const active = visibleTabs.find(
    (t) => t.value === activeTab && !(mode === 'overview' && DETAIL_ONLY_TABS.includes(t.value))
  );

  return (
    // Segmented control: one connected, bordered track signals "same analysis,
    // different views" (not separate-content tabs). Borders collapse via -ml/-mt
    // px so cells read as one calibrated control. Mobile = 3-col grid, lg = single
    // row. Active = filled (≥2 cues: fill + bold + white). Orange is the hover/
    // wayfinding accent; inactive stays clearly visible (never greyed-to-disabled).
    <div className="mb-6">
      <div className="grid grid-cols-3 lg:grid-cols-6 border border-zinc-300">
      {visibleTabs.map((tab) => {
        const isDisabled = mode === 'overview' && DETAIL_ONLY_TABS.includes(tab.value);
        const isActive = activeTab === tab.value && !isDisabled;
        const showTooltip = isDisabled && hoveredTab === tab.value;

        return (
          <div key={tab.value} className="relative -ml-px -mt-px">
            <button
              onClick={() => {
                if (isDisabled) return;
                if (tab.value !== activeTab) capture('view_opened', { view: tab.value });
                onTabChange(tab.value);
              }}
              onMouseEnter={() => isDisabled && setHoveredTab(tab.value)}
              onMouseLeave={() => setHoveredTab(null)}
              disabled={isDisabled}
              aria-disabled={isDisabled}
              aria-pressed={isActive}
              className={`relative w-full h-full min-h-[52px] px-2 py-2.5 lg:px-3 lg:py-3 border border-zinc-200 text-center transition-colors duration-150 ${
                isActive
                  ? 'z-10 bg-zinc-900 border-zinc-900 text-white cursor-pointer'
                  : isDisabled
                    ? 'bg-zinc-50 text-zinc-300 cursor-default'
                    : 'bg-white text-zinc-700 hover:bg-zinc-50 hover:text-[var(--accent)] cursor-pointer'
              }`}
            >
              <span className="block font-mono font-bold uppercase text-[10px] lg:text-[12px] tracking-[0.12em]">
                {tab.label}
              </span>
              <span
                className={`hidden lg:block font-sans font-normal normal-case tracking-normal text-[10px] mt-0.5 ${
                  isActive ? 'text-zinc-300' : isDisabled ? 'text-zinc-300' : 'text-zinc-500'
                }`}
              >
                {tab.subtitle}
              </span>
              {/* Recommended "start here" cue on the default lens when not active. */}
              {tab.value === 'librarian' && !isActive && !isDisabled && (
                <span className="absolute top-1 right-1.5 font-mono text-[9px] font-bold tracking-[0.1em] uppercase text-[var(--accent)]">
                  start
                </span>
              )}
            </button>

            {/* Tooltip for disabled tabs */}
            {showTooltip && (
              <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 z-50 w-56 px-3 py-2 bg-zinc-900 text-white text-[10px] leading-relaxed shadow-lg pointer-events-none">
                <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-zinc-900 rotate-45" />
                {DETAIL_ONLY_TOOLTIPS[tab.value]}
              </div>
            )}
          </div>
        );
      })}
      </div>
      {active && (
        <p className="lg:hidden mt-2 text-xs text-zinc-500">
          <span className="font-medium text-zinc-700">{active.label}</span> — {active.subtitle}
        </p>
      )}
    </div>
  );
}
