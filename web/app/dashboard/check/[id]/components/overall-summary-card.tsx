'use client';

import { OrientationLine } from '@/components/claim-map';
import { ElementStateBadge } from '@/components/claim-map';
import type { Claim, ElementState } from '@shared/types';

interface OverallSummaryCardProps {
  claims: Claim[];
  processingTimeMs?: number;
  checkId: string;
  sourcesCount: number;
}

export function OverallSummaryCard({ claims, processingTimeMs, checkId, sourcesCount }: OverallSummaryCardProps) {
  const stateCounts: Record<ElementState, number> = { supported: 0, disputed: 0, unresolved: 0 };

  for (const claim of claims) {
    if (!claim.claimMap) continue;
    for (const el of claim.claimMap.elements) {
      if (el.state && el.state in stateCounts) {
        stateCounts[el.state]++;
      }
    }
  }

  const firstOrientation = claims[0]?.claimMap?.orientation ?? null;

  const formatTime = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  return (
    <div className="bg-white border border-zinc-200 p-8 mb-8">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-zinc-900 mb-4">Overall Assessment</h2>
        <OrientationLine orientation={firstOrientation} />
      </div>

      <div className="flex items-center gap-4 mb-6">
        {(['supported', 'disputed', 'unresolved'] as ElementState[]).map((state) => (
          <div key={state} className="flex items-center gap-2">
            <ElementStateBadge state={state} size="sm" />
            <span className="text-sm font-bold text-zinc-900">{stateCounts[state]}</span>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-4 font-mono text-[10px] tracking-widest uppercase text-zinc-400">
        <span>REF {checkId.slice(0, 8).toUpperCase()}</span>
        <span>&middot;</span>
        <span>{sourcesCount} SOURCES</span>
        {processingTimeMs !== undefined && (
          <>
            <span>&middot;</span>
            <span>PROCESSED {formatTime(processingTimeMs)}</span>
          </>
        )}
      </div>
    </div>
  );
}
