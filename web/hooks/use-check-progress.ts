'use client';

import { useState, useEffect, useRef } from 'react';
import type { ClaimForSelection } from '@/components/claim-selection/types';

interface ProgressData {
  type: 'progress' | 'completed' | 'error' | 'heartbeat' | 'connected' | 'timeout' | 'awaiting_selection' | 'stream_timeout';
  checkId?: string;
  stage?: string;
  progress?: number;
  message?: string;
  error?: string;
  timestamp?: string;
  timeEstimate?: string;
  claims?: ClaimForSelection[];
}

interface UseCheckProgressReturn {
  progress: number;
  currentStage: string;
  isConnected: boolean;
  isCompleted: boolean;  // True when SSE received 'completed' event
  isAwaitingSelection: boolean; // True when SSE received 'awaiting_selection' event
  claimsForSelection: ClaimForSelection[] | null; // Claims to display in selection UI
  error: string | null;
  message: string | null;
  timeEstimate: string | null;
}

/**
 * Hook for real-time check progress via SSE
 * Connects to backend SSE endpoint and streams progress updates
 * Falls back to polling if SSE fails
 */
export function useCheckProgress(
  checkId: string,
  token: string | null,
  enabled: boolean
): UseCheckProgressReturn {
  const [progress, setProgress] = useState(0);
  const [currentStage, setCurrentStage] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isCompleted, setIsCompleted] = useState(false);
  const [isAwaitingSelection, setIsAwaitingSelection] = useState(false);
  const [claimsForSelection, setClaimsForSelection] = useState<ClaimForSelection[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [timeEstimate, setTimeEstimate] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const progressRef = useRef(0);

  useEffect(() => {
    if (!enabled || !token) {
      return;
    }

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    let cancelled = false;

    async function connect() {
      // Obtain a short-lived stream token — never fall back to the full JWT
      let sseToken: string | null = null;
      try {
        const resp = await fetch(`${apiUrl}/api/v1/checks/${checkId}/sse-token`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
        });
        if (resp.ok) {
          const data = await resp.json();
          sseToken = data.token;
        }
      } catch {
        // SSE token fetch failed — will fall through to return
      }

      if (cancelled || !sseToken) return;

      const url = `${apiUrl}/api/v1/checks/${checkId}/progress?token=${sseToken}`;

      // Create SSE connection
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        setIsConnected(true);
        setError(null);
      };

      eventSource.onmessage = (event) => {
        try {
          const data: ProgressData = JSON.parse(event.data);

          // Handle different event types
          switch (data.type) {
            case 'connected':
              setIsConnected(true);
              break;

            case 'progress':
              // Receiving progress means we're connected
              setIsConnected(true);
              setError(null);
              // Monotonic progress guard: only accept forward progress
              // Prevents visual "rewind" from SSE reconnections or stale events
              if (data.progress !== undefined && data.progress >= progressRef.current) {
                progressRef.current = data.progress;
                setProgress(data.progress);
                if (data.stage) {
                  setCurrentStage(data.stage);
                }
                if (data.message) {
                  setMessage(data.message);
                }
                if (data.timeEstimate) {
                  setTimeEstimate(data.timeEstimate);
                }
              }
              break;

            case 'completed':
              setProgress(100);
              setCurrentStage('complete');  // Show final stage as complete
              setMessage('Evidence research completed successfully');
              setIsCompleted(true);  // Signal to parent that completion was received
              // Close connection on completion
              eventSource.close();
              break;

            case 'error':
              setError(data.error || 'Processing failed');
              setCurrentStage('failed');
              eventSource.close();
              break;

            case 'awaiting_selection':
              setIsAwaitingSelection(true);
              setClaimsForSelection(data.claims || []);
              setCurrentStage('select');
              setMessage('Select claims to investigate');
              // Don't close EventSource — let it close naturally
              break;

            case 'timeout':
              setError('Connection timeout - please refresh');
              eventSource.close();
              break;

            case 'stream_timeout':
              // Server closed a long-lived stream (hang-proofing W3). NOT an
              // error — the pipeline is unaffected; page polling takes over.
              setIsConnected(false);
              eventSource.close();
              break;

            case 'heartbeat':
              // Keep-alive, no action needed
              break;
          }
        } catch (err) {
          console.error('Failed to parse SSE data:', err);
        }
      };

      eventSource.onerror = () => {
        // Don't immediately close - EventSource has built-in reconnect
        // Only mark as disconnected so UI can show appropriate state
        setIsConnected(false);
        // Don't set error immediately - give reconnect a chance
        // EventSource automatically reconnects after errors
        // Only close if readyState is CLOSED (terminal error)
        if (eventSource.readyState === EventSource.CLOSED) {
          setError('Connection closed');
        }
      };
    }

    connect();

    return () => {
      cancelled = true;
      if (eventSourceRef.current && eventSourceRef.current.readyState !== EventSource.CLOSED) {
        eventSourceRef.current.close();
      }
    };
  }, [checkId, token, enabled]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  return {
    progress,
    currentStage,
    isConnected,
    isCompleted,
    isAwaitingSelection,
    claimsForSelection,
    error,
    message,
    timeEstimate,
  };
}
