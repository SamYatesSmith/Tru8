'use client';

type ViewTab = 'cartographer' | 'librarian' | 'interpreter' | 'projectionist' | 'chronologist';

interface ViewSelectorProps {
  mode: 'overview' | 'detail';
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const OVERVIEW_TABS: { value: ViewTab; label: string }[] = [
  { value: 'cartographer', label: 'CARTOGRAPHER' },
  { value: 'librarian', label: 'LIBRARIAN' },
  { value: 'projectionist', label: 'PROJECTIONIST' },
  { value: 'chronologist', label: 'CHRONOLOGIST' },
];

const DETAIL_TABS: { value: ViewTab; label: string }[] = [
  { value: 'cartographer', label: 'CARTOGRAPHER' },
  { value: 'librarian', label: 'LIBRARIAN' },
  { value: 'interpreter', label: 'INTERPRETER' },
  { value: 'projectionist', label: 'PROJECTIONIST' },
  { value: 'chronologist', label: 'CHRONOLOGIST' },
];

export function ViewSelector({ mode, activeTab, onTabChange }: ViewSelectorProps) {
  const tabs = mode === 'overview' ? OVERVIEW_TABS : DETAIL_TABS;

  return (
    <div className="flex border-b border-zinc-200">
      {tabs.map((tab) => (
        <button
          key={tab.value}
          onClick={() => onTabChange(tab.value)}
          className={`px-4 py-3 md:px-8 md:py-4 text-[11px] font-bold tracking-[0.25em] uppercase font-mono transition-colors ${
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
