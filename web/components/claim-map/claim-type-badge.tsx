'use client';

import type { ClaimType } from '@shared/types';
import { CLAIM_TYPE_LABELS } from '@shared/constants';

interface ClaimTypeBadgeProps {
  claimType: ClaimType;
}

export function ClaimTypeBadge({ claimType }: ClaimTypeBadgeProps) {
  return (
    <span className="px-2 py-0.5 border border-zinc-200 text-[9px] uppercase tracking-widest text-zinc-500 font-mono rounded-full">
      {CLAIM_TYPE_LABELS[claimType]}
    </span>
  );
}
