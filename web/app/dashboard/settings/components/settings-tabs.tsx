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
  ];

  return (
    <div className="border-b border-slate-700">
      <div className="flex items-center gap-8">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`pb-4 text-sm font-bold uppercase tracking-wide transition-colors border-b-2 ${
              activeTab === tab.id
                ? 'text-[#f57a07] border-[#f57a07]'
                : 'text-slate-400 border-transparent hover:text-white'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </div>
  );
}
