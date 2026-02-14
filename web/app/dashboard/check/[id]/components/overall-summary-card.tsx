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
    <div className="bg-gradient-to-br from-blue-950/50 to-purple-950/50 border-2 border-blue-500/30 rounded-xl p-8 mb-8">
      <div className="mb-6">
        <h2 className="text-2xl font-black text-white mb-4">Overall Assessment</h2>
        <OrientationLine orientation={firstOrientation} />
      </div>

      <div className="flex items-center gap-4 mb-6">
        {(['supported', 'disputed', 'unresolved'] as ElementState[]).map((state) => (
          <div key={state} className="flex items-center gap-2">
            <ElementStateBadge state={state} size="sm" />
            <span className="text-sm font-bold text-white">{stateCounts[state]}</span>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-4 text-xs font-mono text-slate-500">
        <span>REF {checkId.slice(0, 8).toUpperCase()}</span>
        <span>·</span>
        <span>{sourcesCount} SOURCES</span>
        {processingTimeMs !== undefined && (
          <>
            <span>·</span>
            <span>{formatTime(processingTimeMs)}</span>
          </>
        )}
      </div>
    </div>
  );
}
