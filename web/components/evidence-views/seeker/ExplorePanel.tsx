'use client';

import { RelatedClaim } from '@shared/types';
import { RelatedClaimCard } from './RelatedClaimCard';

interface ExplorePanelProps {
  relatedClaims: RelatedClaim[];
}

export function ExplorePanel({ relatedClaims }: ExplorePanelProps) {
  if (relatedClaims.length === 0) {
    return (
      <div className="py-8 text-center border border-dashed border-zinc-200 bg-zinc-50/30">
        <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-400 mb-2">
          No related claims found yet
        </p>
        <p className="text-[12px] text-zinc-400 leading-relaxed max-w-md mx-auto">
          As more users investigate similar topics, related angles will appear here.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <p className="font-mono text-[10px] font-bold uppercase tracking-widest text-zinc-500">
          Adjacent Claims
        </p>
        <span className="font-mono text-[10px] text-zinc-300">
          {relatedClaims.length} found
        </span>
      </div>
      <p className="text-[12px] text-zinc-400 leading-relaxed">
        Other users have investigated these related claims. Explore different angles or perspectives on this topic.
      </p>
      {relatedClaims.map((claim, idx) => (
        <RelatedClaimCard key={idx} claim={claim} />
      ))}
    </div>
  );
}
