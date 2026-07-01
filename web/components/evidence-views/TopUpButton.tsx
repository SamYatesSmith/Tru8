'use client';

import { useCallback } from 'react';
import { apiClient } from '@/lib/api';
import { useResearchPoll } from '@/hooks/use-research-poll';

/**
 * "Top up a thin claim" trigger. Pulls MORE evidence into the existing pool for
 * a thin element (or all of a claim's thin elements), re-mapping new + existing
 * together — the same re-search the Seeker uses for gaps, surfaced on the digest.
 *
 * Two modes:
 *   - `element`  → one thin element ("Get more sources"), 1 credit.
 *   - `claim`    → all of a claim's thin elements in one run ("Strengthen this
 *                  claim"), 1 credit — the backend `research-thin` bundle.
 *
 * Neutral wayfinding only (orange accent, no stance colour); copy describes the
 * SOURCING, never the claim's truth. Dashboard-only (rendered where a token is
 * threaded); the public report never mounts it.
 */
interface TopUpButtonProps {
  mode: 'element' | 'claim';
  checkId: string;
  claimId: string;
  token: string | null;
  /** Required in `element` mode. */
  elementId?: string;
  /** Number of thin elements — labels the `claim` mode button. */
  thinCount?: number;
  onComplete?: () => void;
}

export function TopUpButton({ mode, checkId, claimId, token, elementId, thinCount, onComplete }: TopUpButtonProps) {
  const { status, message, newCount, run, reset } = useResearchPoll({ checkId, claimId, token, onComplete });

  const startTopUp = useCallback(() => {
    if (mode === 'element') {
      if (!elementId) return;
      return run(async (t) => {
        await apiClient.startElementResearch(checkId, claimId, elementId, t);
        return [elementId];
      }, 'Searching...');
    }
    return run(async (t) => {
      const res = await apiClient.startThinResearch(checkId, claimId, t);
      return res.elementIds || [];
    }, 'Strengthening...');
  }, [mode, checkId, claimId, elementId, run]);

  if (!token) return null;
  if (mode === 'element' && !elementId) return null;
  if (mode === 'claim' && (thinCount ?? 0) === 0) return null;

  const isClaim = mode === 'claim';

  // ── Running / completed / error / limit are shared compact treatments ──
  if (status === 'running') {
    return (
      <span className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        <span className="h-2.5 w-2.5 border-2 border-zinc-300 border-t-zinc-600 rounded-full animate-spin" />
        {message}
      </span>
    );
  }

  if (status === 'completed') {
    return (
      <span className="font-mono text-[10px] uppercase tracking-widest text-emerald-600">
        {newCount > 0 ? `Found ${newCount} new source${newCount !== 1 ? 's' : ''}` : message}
      </span>
    );
  }

  if (status === 'limit_reached') {
    return (
      <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-400">
        Limit reached &mdash; upgrade for more
      </span>
    );
  }

  if (status === 'error') {
    return (
      <span className="inline-flex items-center gap-2">
        <span className="font-mono text-[10px] uppercase tracking-widest text-red-500">{message}</span>
        <button
          onClick={reset}
          className="font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:text-zinc-600"
        >
          Retry
        </button>
      </span>
    );
  }

  // ── idle ──
  if (isClaim) {
    const n = thinCount ?? 0;
    return (
      <button
        onClick={startTopUp}
        className="inline-flex items-center gap-2 border border-zinc-200 bg-white px-3 py-2 hover:border-[var(--accent)] transition-colors group"
      >
        <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-600 group-hover:text-[var(--accent)] transition-colors">
          Strengthen this claim
        </span>
        <span className="font-mono text-[9px] text-zinc-400">
          {n} thin element{n !== 1 ? 's' : ''} &middot; 1 credit
        </span>
      </button>
    );
  }

  return (
    <button
      onClick={startTopUp}
      className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest text-zinc-500 hover:text-[var(--accent)] transition-colors"
    >
      Get more sources
      <span className="font-mono text-[9px] bg-zinc-100 px-1.5 py-0.5 text-zinc-500">1 credit</span>
    </button>
  );
}
