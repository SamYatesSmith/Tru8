'use client';

import { EvidenceTier } from '@shared/types';

const TIER_COLOURS: Record<EvidenceTier, string> = {
  primary: '#EA580C',
  reporting: '#3F3F46',
  commentary: '#A1A1AA',
};

interface DomainSegment {
  name: string;
  count: number;
  tier: EvidenceTier;
}

interface ConcentrationBarProps {
  domains: DomainSegment[];
}

export function ConcentrationBar({ domains }: ConcentrationBarProps) {
  if (domains.length === 0) return null;

  const sorted = [...domains].sort((a, b) => b.count - a.count);
  const total = sorted.reduce((sum, d) => sum + d.count, 0);
  const topThree = sorted.slice(0, 3);

  return (
    <div>
      <div className="h-3 flex overflow-hidden border border-zinc-200">
        {sorted.map((d) => (
          <div
            key={d.name}
            style={{
              width: `${(d.count / total) * 100}%`,
              backgroundColor: TIER_COLOURS[d.tier],
            }}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1.5">
        {topThree.map((d) => (
          <span key={d.name} className="font-mono text-[9px] text-zinc-400 tracking-widest">
            {d.name}
          </span>
        ))}
      </div>
    </div>
  );
}
