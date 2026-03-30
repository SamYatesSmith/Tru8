'use client';

import { Claim, InputType } from '@shared/types';
import { ClaimSectionCard } from './ClaimSectionCard';

interface ClaimSectionStackProps {
  claims: Claim[];
  onExplore: (position: number) => void;
  inputType?: InputType;
}

export function ClaimSectionStack({ claims, onExplore, inputType }: ClaimSectionStackProps) {
  return (
    <div className="mb-16">
      <div className="border-b border-zinc-200 pb-2 mb-6">
        <div className="font-mono text-sm font-bold uppercase tracking-[0.3em] text-zinc-600">
          Claims &middot; {claims.length}
        </div>
        <p className="text-[11px] text-zinc-400 mt-1">
          Each claim below shows its evidence summary. Select one to explore in full detail.
        </p>
      </div>

      <div className="space-y-4">
        {claims.map((claim, index) => (
          <ClaimSectionCard
            key={claim.id}
            claim={claim}
            position={index}
            onExplore={onExplore}
            inputType={inputType}
          />
        ))}
      </div>
    </div>
  );
}
