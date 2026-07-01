'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { apiClient } from '@/lib/api';

/**
 * The shared re-search state machine: start a re-search, poll every element's
 * status until all finish, aggregate the new-source count, then fire onComplete.
 *
 * Extracted from ResearchButton so the gap re-search (Seeker) and the thin
 * top-up (per-element + claim-level "Strengthen this claim") share ONE loop
 * instead of cloning it. The only thing that varies is HOW the run starts and
 * WHICH element ids to poll — supplied by the `start` callback passed to `run`.
 */

export type ResearchPollStatus =
  | 'idle'
  | 'running'
  | 'completed'
  | 'error'
  | 'limit_reached';

const STATUS_MESSAGES: Record<string, string> = {
  planning: 'Planning queries...',
  retrieving: 'Searching...',
  classifying: 'Classifying...',
  mapping: 'Mapping evidence...',
};

// Backend pipeline can take a couple of minutes for slow claims. Cap polling at
// 5 minutes so a broken/forgotten poll can never loop indefinitely.
const POLL_TIMEOUT_MS = 5 * 60 * 1000;

interface UseResearchPollArgs {
  checkId: string;
  claimId: string;
  /** Signed-in check only — the poll uses a freshly-refreshed token per call. */
  token: string | null;
  onComplete?: () => void;
}

export interface UseResearchPoll {
  status: ResearchPollStatus;
  message: string;
  newCount: number;
  /**
   * Kick off a re-search. `start` receives a freshly-refreshed token, performs
   * the POST, and resolves to the element ids to poll (e.g. gap ids,
   * `[elementId]`, or the thin ids the bundle endpoint returns).
   * `startingMessage` seeds the running label.
   */
  run: (start: (token: string) => Promise<string[]>, startingMessage?: string) => Promise<void>;
  reset: () => void;
}

export function useResearchPoll({ checkId, claimId, token, onComplete }: UseResearchPollArgs): UseResearchPoll {
  // Clerk's getToken directly so each request (start + every poll) gets a fresh
  // JWT. Without this, ~60s into a re-search the token expires, polls 401, and
  // the UI sticks on "Searching…" while the backend has finished successfully.
  const { getToken } = useAuth();

  const [status, setStatus] = useState<ResearchPollStatus>('idle');
  const [message, setMessage] = useState('');
  const [newCount, setNewCount] = useState(0);
  const pollRef = useRef<ReturnType<typeof setInterval>>();

  const cleanup = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = undefined;
    }
  }, []);

  useEffect(() => cleanup, [cleanup]);

  const reset = useCallback(() => {
    cleanup();
    setStatus('idle');
    setMessage('');
    setNewCount(0);
  }, [cleanup]);

  const run = useCallback(
    async (start: (token: string) => Promise<string[]>, startingMessage?: string) => {
      if (!token || status === 'running') return;

      setStatus('running');
      setMessage(startingMessage || 'Searching...');

      try {
        const startToken = await getToken();
        if (!startToken) {
          setStatus('error');
          setMessage('Authentication expired — please refresh');
          return;
        }

        const elementIds = await start(startToken);
        if (!elementIds || elementIds.length === 0) {
          setStatus('error');
          setMessage('Nothing to search');
          return;
        }

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

            for (const eid of elementIds) {
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
              setNewCount(totalNew);

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

              // Trigger data refresh after a short delay
              setTimeout(() => { onComplete?.(); }, 1500);
            }
          } catch {
            // Per-poll transient error — keep polling; hard timeout will bail.
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
    },
    [checkId, claimId, token, getToken, status, cleanup, onComplete]
  );

  return { status, message, newCount, run, reset };
}
