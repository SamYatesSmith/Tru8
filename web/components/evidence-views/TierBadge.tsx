'use client';

type Tier = 'primary' | 'reporting' | 'commentary';

interface TierBadgeProps {
  tier: Tier;
}

const TIER_CONFIG: Record<Tier, { label: string; className: string }> = {
  primary: {
    label: 'Primary',
    className: 'bg-orange-50 border-orange-200 text-orange-700',
  },
  reporting: {
    label: 'Reporting',
    className: 'bg-zinc-100 border-zinc-300 text-zinc-700',
  },
  commentary: {
    label: 'Commentary',
    className: 'bg-zinc-50 border-zinc-200 text-zinc-400',
  },
};

export function TierBadge({ tier }: TierBadgeProps) {
  const config = TIER_CONFIG[tier];

  return (
    <span
      className={`px-2 py-0.5 border text-[9px] font-mono font-bold uppercase tracking-wider ${config.className}`}
    >
      {config.label}
    </span>
  );
}
