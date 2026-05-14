'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@clerk/nextjs';
import { apiClient } from '@/lib/api';

interface ResearchButtonProps {
  checkId: string;
  claimId: string;
  token: string | null;
  gapElementIds: string[];
  creditInfo?: { remaining: number } | null;
  coverageBefore?: number;
  onComplete?: () => void;
}

const STATUS_MESSAGES: Record<string, string> = {
  planning: 'Planning queries...',
  retrieving: 'Searching...',
  classifying: 'Classifying...',
  mapping: 'Mapping evidence...',
};

// Backend pipeline can take a couple of minutes for slow gap claims. Cap polling
// at 5 minutes so a broken/forgotten poll can never loop indefinitely.
const POLL_TIMEOUT_MS = 5 * 60 * 1000;

export function ResearchButton({
  checkId,
  claimId,
  token,
  gapElementIds,
  creditInfo,
  coverageBefore,
  onComplete,
}: ResearchButtonProps) {
  // Use Clerk's getToken directly so each API call (start + every poll) gets a
  // freshly-refreshed JWT. The `token` prop is kept for the "is signed in?" check
  // since the parent already wires it that way — but we never use that stale token
  // for the actual requests. Without this, ~60s into a re-search the JWT expires,
  // every poll returns 401, and the UI is stuck on "Searching…" while the
  // backend has completed the work successfully.
  const { getToken } = useAuth();

  const [status, setStatus] = useState<'idle' | 'running' | 'completed' | 'error' | 'limit_reached'>('idle');
  const [message, setMessage] = useState('');
  const [totalNewCount, setTotalNewCount] = useState(0);
  const [coverageAfter, setCoverageAfter] = useState<number | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval>>();

  const cleanup = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = undefined;
    }
  }, []);

  useEffect(() => cleanup, [cleanup]);

  const startResearch = useCallback(async () => {
    if (!token || status === 'running' || gapElementIds.length === 0) return;

    setStatus('running');
    setMessage(`Searching ${gapElementIds.length} gap${gapElementIds.length !== 1 ? 's' : ''}...`);

    try {
      const startToken = await getToken();
      if (!startToken) {
        setStatus('error');
        setMessage('Authentication expired — please refresh');
        return;
      }
      await apiClient.startGapResearch(checkId, claimId, startToken);

      const startedAt = Date.now();

      pollRef.current = setInterval(async () => {
        // Hard timeout — never poll forever
        if (Date.now() - startedAt > POLL_TIMEOUT_MS) {
          cleanup();
          setStatus('error');
          setMessage('Search timed out — refresh to see what completed');
          return;
        }

        try {
          // Fresh token per poll; Clerk auto-refreshes when needed
          const pollToken = await getToken();
          if (!pollToken) {
            cleanup();
            setStatus('error');
            setMessage('Session expired — please refresh');
            return;
          }

          let allDone = true;
          let anyError = false;
          let totalNew = 0;
          let latestMessage = '';

          for (const eid of gapElementIds) {
            const result = await apiClient.getResearchStatus(checkId, claimId, eid, pollToken);
            if (!result) { allDone = false; continue; }

            if (result.status === 'completed') {
              totalNew += result.newEvidenceCount || 0;
            } else if (result.status === 'error') {
              anyError = true;
            } else {
              allDone = false;
              latestMessage = STATUS_MESSAGES[result.status] || result.message;
            }
          }

          if (!allDone && latestMessage) {
            setMessage(latestMessage);
          }

          if (allDone) {
            cleanup();
            setTotalNewCount(totalNew);

            if (anyError && totalNew === 0) {
              setStatus('error');
              setMessage('Some searches failed');
            } else {
              setStatus('completed');
              setMessage(
                totalNew > 0
                  ? `Found ${totalNew} new source${totalNew !== 1 ? 's' : ''}`
                  : 'No new sources found'
              );
            }

            // Trigger data refresh after short delay
            setTimeout(() => {
              onComplete?.();
            }, 1500);
          }
        } catch {
          // Per-poll transient error — continue polling, hard timeout will bail eventually
        }
      }, 2500);
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : String(err);
      if (errMsg.includes('402') || errMsg.toLowerCase().includes('limit') || errMsg.toLowerCase().includes('credit')) {
        setStatus('limit_reached');
        setMessage('Credit limit reached');
      } else {
        setStatus('error');
        setMessage(errMsg || 'Failed to start research');
      }
    }
  }, [checkId, claimId, token, getToken, gapElementIds, status, cleanup, onComplete]);

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
          {totalNewCount > 0
            ? `Found ${totalNewCount} new source${totalNewCount !== 1 ? 's' : ''}`
            : message}
        </span>
        {typeof coverageBefore === 'number' && totalNewCount > 0 && (
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
        onClick={() => { setStatus('idle'); setMessage(''); }}
        className="font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:text-zinc-600"
      >
        Retry
      </button>
    </div>
  );
}
