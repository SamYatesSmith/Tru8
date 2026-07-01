'use client';

import { useCallback } from 'react';
import { apiClient } from '@/lib/api';
import { useResearchPoll } from '@/hooks/use-research-poll';

interface ResearchButtonProps {
  checkId: string;
  claimId: string;
  token: string | null;
  gapElementIds: string[];
  creditInfo?: { remaining: number } | null;
  coverageBefore?: number;
  onComplete?: () => void;
}

export function ResearchButton({
  checkId,
  claimId,
  token,
  gapElementIds,
  creditInfo,
  coverageBefore,
  onComplete,
}: ResearchButtonProps) {
  // Shared re-search state machine (start → poll all ids → refresh). Gap-specific
  // copy stays here; the loop is the same one the thin top-up uses.
  const { status, message, newCount, run, reset } = useResearchPoll({ checkId, claimId, token, onComplete });

  const startResearch = useCallback(() => {
    if (gapElementIds.length === 0) return;
    return run(async (t) => {
      await apiClient.startGapResearch(checkId, claimId, t);
      return gapElementIds;
    }, `Searching ${gapElementIds.length} gap${gapElementIds.length !== 1 ? 's' : ''}...`);
  }, [checkId, claimId, gapElementIds, run]);

  if (gapElementIds.length === 0) return null;

  if (status === 'limit_reached' || (creditInfo && creditInfo.remaining <= 0 && status === 'idle')) {
    return (
      <div className="border border-zinc-200 bg-zinc-50/50 px-4 py-3 text-center">
        <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-400">
          Limit reached &mdash; upgrade for more
        </span>
      </div>
    );
  }

  if (status === 'idle') {
    return (
      <div>
        <button
          onClick={startResearch}
          className="w-full border border-zinc-200 bg-white px-4 py-3 hover:bg-zinc-50 hover:border-zinc-300 transition-colors flex items-center justify-center gap-2.5"
        >
          <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
            Seek sources for {gapElementIds.length} gap{gapElementIds.length !== 1 ? 's' : ''}
          </span>
          <span className="font-mono text-[9px] bg-zinc-100 px-2 py-0.5 text-zinc-500">
            1 credit
          </span>
        </button>
        {creditInfo && (
          <p className="font-mono text-[10px] text-zinc-400 text-center mt-1.5">
            {creditInfo.remaining} credit{creditInfo.remaining !== 1 ? 's' : ''} remaining
          </p>
        )}
      </div>
    );
  }

  if (status === 'running') {
    return (
      <div className="border border-zinc-200 bg-zinc-50/50 px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 border-2 border-zinc-300 border-t-zinc-600 rounded-full animate-spin" />
          <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
            {message}
          </span>
        </div>
      </div>
    );
  }

  if (status === 'completed') {
    return (
      <div className="border border-emerald-200 bg-emerald-50/50 px-4 py-3">
        <span className="font-mono text-[10px] uppercase tracking-widest text-emerald-600">
          {newCount > 0
            ? `Found ${newCount} new source${newCount !== 1 ? 's' : ''}`
            : message}
        </span>
        {typeof coverageBefore === 'number' && newCount > 0 && (
          <p className="font-mono text-[10px] text-emerald-500/70 mt-1">
            Refresh to see updated coverage
          </p>
        )}
      </div>
    );
  }

  // error
  return (
    <div className="border border-red-200 bg-red-50/50 px-4 py-3 flex items-center justify-between">
      <span className="font-mono text-[10px] uppercase tracking-widest text-red-500">
        {message}
      </span>
      <button
        onClick={reset}
        className="font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:text-zinc-600"
      >
        Retry
      </button>
    </div>
  );
}
