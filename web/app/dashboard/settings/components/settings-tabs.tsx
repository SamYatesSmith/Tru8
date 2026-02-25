'use client';

interface SettingsTabsProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export function SettingsTabs({ activeTab, onTabChange }: SettingsTabsProps) {
  const tabs = [
    { id: 'account', label: 'ACCOUNT' },
    { id: 'subscription', label: 'SUBSCRIPTION' },
    { id: 'notifications', label: 'NOTIFICATIONS' },
    { id: 'developer', label: 'DEVELOPER' },
  ];

  return (
    <div className="border-b border-zinc-100">
      <div className="flex items-center gap-8">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`pb-4 font-mono text-[10px] font-bold uppercase tracking-[0.2em] transition-colors border-b-2 ${
              activeTab === tab.id
                ? 'text-black border-accent'
                : 'text-zinc-400 border-transparent hover:text-zinc-900'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </div>
  );
}
