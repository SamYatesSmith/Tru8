'use client';

import { useState, useEffect, useRef } from 'react';

interface ProgressData {
  type: 'progress' | 'completed' | 'error' | 'heartbeat' | 'connected' | 'timeout';
  checkId?: string;
  stage?: string;
  progress?: number;
  message?: string;
  error?: string;
  timestamp?: string;
}

interface UseCheckProgressReturn {
  progress: number;
  currentStage: string;
  isConnected: boolean;
  error: string | null;
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
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!enabled || !token) {
      return;
    }

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
    const url = `${apiUrl}/api/v1/checks/${checkId}/progress?token=${token}`;

    try {
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
              if (data.stage) {
                setCurrentStage(data.stage);
              }
              if (data.progress !== undefined) {
                setProgress(data.progress);
              }
              break;

            case 'completed':
              setProgress(100);
              setCurrentStage('completed');
              // Close connection on completion
              eventSource.close();
              break;

            case 'error':
              setError(data.error || 'Processing failed');
              setCurrentStage('failed');
              eventSource.close();
              break;

            case 'timeout':
              setError('Connection timeout - please refresh');
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
        setIsConnected(false);
        setError('Connection lost');
        eventSource.close();
      };

      return () => {
        if (eventSource.readyState !== EventSource.CLOSED) {
          eventSource.close();
        }
      };
    } catch (err) {
      console.error('Failed to create SSE connection:', err);
      setError('Failed to connect');
      setIsConnected(false);
    }
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
    error,
  };
}
