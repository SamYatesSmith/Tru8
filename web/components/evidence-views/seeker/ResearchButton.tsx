'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { apiClient } from '@/lib/api';

interface ResearchButtonProps {
  elementId: string;
  checkId: string;
  claimId: string;
  token: string | null;
  hasBountyText: boolean;
  onComplete?: () => void;
}

const STATUS_MESSAGES: Record<string, string> = {
  planning: 'Planning queries...',
  retrieving: 'Searching...',
  classifying: 'Classifying...',
  mapping: 'Mapping evidence...',
};

export function ResearchButton({
  elementId,
  checkId,
  claimId,
  token,
  hasBountyText,
  onComplete,
}: ResearchButtonProps) {
  const [status, setStatus] = useState<'idle' | 'running' | 'completed' | 'error'>('idle');
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

  const startResearch = useCallback(async () => {
    if (!token || status === 'running') return;

    setStatus('running');
    setMessage('Starting...');

    try {
      await apiClient.startElementResearch(checkId, claimId, elementId, token);

      // Poll for status every 2 seconds
      pollRef.current = setInterval(async () => {
        try {
          const result = await apiClient.getResearchStatus(
            checkId, claimId, elementId, token,
          );
          if (!result) return;

          const displayMsg = STATUS_MESSAGES[result.status] || result.message;
          setMessage(displayMsg);

          if (result.status === 'completed') {
            setStatus('completed');
            setNewCount(result.newEvidenceCount || 0);
            setMessage(result.message);
            cleanup();
            // Trigger data refresh after short delay
            setTimeout(() => {
              onComplete?.();
            }, 1500);
          } else if (result.status === 'error') {
            setStatus('error');
            setMessage(result.message);
            cleanup();
          }
        } catch {
          // Polling error — continue polling
        }
      }, 2000);
    } catch (err) {
      setStatus('error');
      setMessage(err instanceof Error ? err.message : 'Failed to start research');
    }
  }, [checkId, claimId, elementId, token, status, cleanup, onComplete]);

  if (!hasBountyText) return null;

  if (status === 'idle') {
    return (
      <button
        onClick={startResearch}
        className="mt-3 w-full border border-zinc-200 bg-white px-4 py-2.5 hover:bg-zinc-50 hover:border-zinc-300 transition-colors font-mono text-[10px] uppercase tracking-widest text-zinc-500"
      >
        Re-search this element
      </button>
    );
  }

  if (status === 'running') {
    return (
      <div className="mt-3 border border-zinc-200 bg-zinc-50/50 px-4 py-2.5">
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
      <div className="mt-3 border border-emerald-200 bg-emerald-50/50 px-4 py-2.5">
        <span className="font-mono text-[10px] uppercase tracking-widest text-emerald-600">
          {newCount > 0
            ? `Found ${newCount} new source${newCount !== 1 ? 's' : ''}`
            : message}
        </span>
      </div>
    );
  }

  // error
  return (
    <div className="mt-3 border border-red-200 bg-red-50/50 px-4 py-2.5 flex items-center justify-between">
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
