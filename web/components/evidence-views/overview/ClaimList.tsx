'use client';

import { Claim } from '@shared/types';
import { ClaimOverviewCard } from './ClaimOverviewCard';

interface ClaimListProps {
  claims: Claim[];
  checkId: string;
}

export function ClaimList({ claims, checkId }: ClaimListProps) {
  return (
    <div className="mb-16">
      <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-zinc-400 mb-6 border-b border-zinc-100 pb-2">
        Claims &middot; {claims.length}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {claims.map((claim, index) => (
          <ClaimOverviewCard
            key={claim.id}
            claim={claim}
            position={index}
            checkId={checkId}
          />
        ))}
      </div>
    </div>
  );
}
