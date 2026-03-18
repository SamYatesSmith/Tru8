'use client';

import { EvidenceTier } from '@shared/types';

const TIER_STYLES: Record<EvidenceTier, { text: string; border: string; outline: string; bg: string }> = {
  primary: {
    text: 'text-[#EA580C]',
    border: 'border-[#EA580C]',
    outline: '#EA580C',
    bg: 'bg-orange-50',
  },
  reporting: {
    text: 'text-[#3F3F46]',
    border: 'border-[#3F3F46]',
    outline: '#3F3F46',
    bg: 'bg-zinc-100',
  },
  commentary: {
    text: 'text-[#A1A1AA]',
    border: 'border-[#A1A1AA]',
    outline: '#A1A1AA',
    bg: 'bg-zinc-50',
  },
};

const TIER_LABELS: Record<EvidenceTier, string> = {
  primary: 'Primary',
  reporting: 'Reporting',
  commentary: 'Commentary',
};

interface TierStampProps {
  tier: EvidenceTier;
}

export function TierStamp({ tier }: TierStampProps) {
  const style = TIER_STYLES[tier];

  return (
    <span
      className={`inline-block font-mono text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rotate-1 border ${style.text} ${style.border} ${style.bg}`}
      style={{ outline: `1px solid ${style.outline}`, outlineOffset: '1px' }}
    >
      {TIER_LABELS[tier]}
    </span>
  );
}
