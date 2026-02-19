'use client';

type ViewTab = 'cartographer' | 'librarian' | 'interpreter' | 'projectionist';

interface ViewSelectorProps {
  mode: 'overview' | 'detail';
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const OVERVIEW_TABS: { value: ViewTab; label: string }[] = [
  { value: 'cartographer', label: 'CARTOGRAPHER' },
  { value: 'librarian', label: 'LIBRARIAN' },
  { value: 'projectionist', label: 'PROJECTIONIST' },
];

const DETAIL_TABS: { value: ViewTab; label: string }[] = [
  { value: 'cartographer', label: 'CARTOGRAPHER' },
  { value: 'librarian', label: 'LIBRARIAN' },
  { value: 'interpreter', label: 'INTERPRETER' },
  { value: 'projectionist', label: 'PROJECTIONIST' },
];

export function ViewSelector({ mode, activeTab, onTabChange }: ViewSelectorProps) {
  const tabs = mode === 'overview' ? OVERVIEW_TABS : DETAIL_TABS;

  return (
    <div className="flex border-b border-zinc-200">
      {tabs.map((tab) => (
        <button
          key={tab.value}
          onClick={() => onTabChange(tab.value)}
          className={`px-8 py-4 text-[11px] font-bold tracking-[0.25em] uppercase font-mono transition-colors ${
            activeTab === tab.value
              ? 'border-b-2 border-[var(--accent)] text-black'
              : 'text-zinc-400 hover:text-zinc-600'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
