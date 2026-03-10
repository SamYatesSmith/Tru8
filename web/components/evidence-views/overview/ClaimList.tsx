'use client';

import { Claim } from '@shared/types';
import { ClaimOverviewCard } from './ClaimOverviewCard';

interface ClaimListProps {
  claims: Claim[];
  checkId: string;
  onSelect?: (position: number) => void;
  activePosition?: number | null;
}

export function ClaimList({ claims, checkId, onSelect, activePosition }: ClaimListProps) {
  return (
    <div className="mb-16">
      <div className="border-b border-zinc-200 pb-2 mb-6">
        <div className="font-mono text-sm font-bold uppercase tracking-[0.3em] text-zinc-600">
          Claims &middot; {claims.length}
        </div>
        <p className="text-[11px] text-zinc-400 mt-1">
          Select a claim to explore its evidence in detail across all six views.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {claims.map((claim, index) => (
          <ClaimOverviewCard
            key={claim.id}
            claim={claim}
            position={index}
            checkId={checkId}
            onSelect={onSelect}
            isActive={activePosition === index}
          />
        ))}
      </div>
    </div>
  );
}
