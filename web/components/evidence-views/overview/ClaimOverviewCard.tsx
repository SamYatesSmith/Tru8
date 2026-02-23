'use client';

import { useRouter } from 'next/navigation';
import { Claim } from '@shared/types';

interface ClaimOverviewCardProps {
  claim: Claim;
  position: number;
  checkId: string;
  isActive?: boolean;
  onSelect?: (position: number) => void;
}

export function ClaimOverviewCard({ claim, position, checkId, isActive, onSelect }: ClaimOverviewCardProps) {
  const router = useRouter();

  const claimMap = claim.claimMap;
  const elements = claimMap?.elements || [];
  const evidenceCount = claim.evidence?.length || 0;
  const orientation = claimMap?.orientation;
  const claimType = claimMap?.claimType || claim.claimType;

  // Count element states
  const stateCounts = { supported: 0, disputed: 0, gap: 0 };
  for (const el of elements) {
    if (el.state === 'supported') stateCounts.supported++;
    else if (el.state === 'disputed') stateCounts.disputed++;
    else stateCounts.gap++;
  }

  const isGap = evidenceCount === 0;
  const rankLabel = String(position + 1).padStart(2, '0');

  const typeLabels: Record<string, string> = {
    empirical: 'Empirical',
    definitional: 'Definitional',
    causal_interpretive: 'Causal',
    predictive: 'Predictive',
    normative_flagged: 'Normative',
  };

  return (
    <div
      className={`claim-overview-card p-5 ${
        isActive
          ? 'border border-zinc-900 bg-white'
          : isGap
            ? 'border border-dashed border-zinc-200 bg-zinc-50/30'
            : 'border border-zinc-100 bg-white'
      }`}
      onClick={() => onSelect ? onSelect(position) : router.push(`/dashboard/check/${checkId}/claim/${position}`)}
      role="link"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter') {
          onSelect ? onSelect(position) : router.push(`/dashboard/check/${checkId}/claim/${position}`);
        }
      }}
    >
      {/* Rank + Type badge */}
      <div className="flex items-start justify-between mb-3">
        <span className="font-mono text-xs font-bold text-zinc-300">{rankLabel}</span>
        {claimType && (
          <span className="px-2.5 py-0.5 bg-zinc-50 border border-zinc-200 text-[9px] font-mono font-bold uppercase tracking-wider text-zinc-500">
            {typeLabels[claimType] || claimType}
          </span>
        )}
      </div>

      {/* Claim text */}
      <h3
        className={`text-[15px] font-medium leading-relaxed mb-4 line-clamp-2 ${
          isGap ? 'text-zinc-400' : 'text-zinc-900'
        }`}
      >
        {claim.text}
      </h3>

      {/* Metadata row */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mb-3">
        <span className="font-mono text-[10px] text-zinc-400">
          Elements {elements.length}
        </span>
        <span className="text-zinc-200">&middot;</span>
        <span className="font-mono text-[10px] text-zinc-400">
          Sources {evidenceCount}
        </span>
        {(stateCounts.supported > 0 || stateCounts.disputed > 0 || stateCounts.gap > 0) && (
          <>
            <span className="text-zinc-200">&middot;</span>
            {stateCounts.supported > 0 && (
              <span className="font-mono text-[10px] text-emerald-500">
                {stateCounts.supported} supported
              </span>
            )}
            {stateCounts.disputed > 0 && (
              <span className="font-mono text-[10px] text-amber-500">
                {stateCounts.disputed} disputed
              </span>
            )}
            {stateCounts.gap > 0 && (
              <span className="font-mono text-[10px] text-zinc-400">
                {stateCounts.gap} {stateCounts.gap === 1 ? 'unknown' : 'unknowns'}
              </span>
            )}
          </>
        )}
      </div>

      {/* Orientation + drill arrow */}
      <div className="flex items-end justify-between">
        <p className={`text-[12px] leading-relaxed flex-grow ${isGap ? 'text-zinc-400' : 'text-zinc-500'}`}>
          {orientation || 'No orientation available.'}
        </p>
        <span className="drill-arrow text-zinc-300 text-sm ml-4 transition-colors">
          &rarr;
        </span>
      </div>
    </div>
  );
}
