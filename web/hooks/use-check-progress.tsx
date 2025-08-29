'use client';

import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@clerk/nextjs';

type PipelineStage = 'queued' | 'ingest' | 'extract' | 'retrieve' | 'verify' | 'judge' | 'complete';

interface ProgressEvent {
  type: 'connected' | 'progress' | 'completed' | 'error' | 'heartbeat' | 'timeout';
  checkId: string;
  stage?: PipelineStage;
  progress?: number; // 0-100
  message?: string;
  timestamp?: string;
  error?: string;
}

interface ProgressState {
  stage: PipelineStage;
  progress: number;
  message?: string;
  error?: string;
  isComplete: boolean;
  isConnected: boolean;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export function useCheckProgress(checkId: string | null) {
  const { getToken } = useAuth();
  const [state, setState] = useState<ProgressState>({
    stage: 'queued',
    progress: 0,
    isComplete: false,
    isConnected: false,
  });
  
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const maxReconnectAttempts = 5;
  const reconnectAttempts = useRef(0);

  const cleanup = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  };

  const connect = async () => {
    if (!checkId) return;

    try {
      const token = await getToken();
      if (!token) {
        console.error('No authentication token available');
        return;
      }

      cleanup();

      // Note: EventSource doesn't support custom headers in all browsers
      // For now, we'll pass the token as a query parameter (less secure but functional)
      // In production, consider using WebSocket or polling for authenticated SSE
      const url = `${API_BASE_URL}/api/v1/checks/${checkId}/progress?token=${encodeURIComponent(token)}`;
      
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log('SSE connection opened');
        setState(prev => ({ ...prev, isConnected: true, error: undefined }));
        reconnectAttempts.current = 0;
      };

      eventSource.onmessage = (event) => {
        try {
          const data: ProgressEvent = JSON.parse(event.data);
          console.log('Progress event:', data);

          switch (data.type) {
            case 'connected':
              setState(prev => ({ ...prev, isConnected: true }));
              break;

            case 'progress':
              if (data.stage && data.progress !== undefined) {
                setState(prev => ({
                  ...prev,
                  stage: data.stage!,
                  progress: data.progress!,
                  message: data.message,
                  error: undefined,
                }));
              }
              break;

            case 'completed':
              setState(prev => ({
                ...prev,
                stage: 'complete',
                progress: 100,
                isComplete: true,
                message: 'Fact-check completed successfully!',
                error: undefined,
              }));
              cleanup();
              break;

            case 'error':
              setState(prev => ({
                ...prev,
                error: data.error || 'An error occurred during processing',
                isComplete: true,
              }));
              cleanup();
              break;

            case 'timeout':
              setState(prev => ({
                ...prev,
                error: 'Processing timed out. Please try again.',
                isComplete: true,
              }));
              cleanup();
              break;

            case 'heartbeat':
              // Keep connection alive, no state update needed
              break;

            default:
              console.log('Unknown event type:', data.type);
          }
        } catch (error) {
          console.error('Error parsing SSE data:', error);
        }
      };

      eventSource.onerror = (error) => {
        console.error('SSE connection error:', error);
        setState(prev => ({ ...prev, isConnected: false }));
        
        eventSource.close();
        
        // Attempt to reconnect with exponential backoff
        if (reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000);
          reconnectAttempts.current += 1;
          
          console.log(`Attempting to reconnect in ${delay}ms (attempt ${reconnectAttempts.current}/${maxReconnectAttempts})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else {
          setState(prev => ({
            ...prev,
            error: 'Connection lost. Please refresh the page.',
            isConnected: false,
          }));
        }
      };

    } catch (error) {
      console.error('Error setting up SSE connection:', error);
      setState(prev => ({
        ...prev,
        error: 'Failed to connect to progress updates',
        isConnected: false,
      }));
    }
  };

  useEffect(() => {
    if (checkId && !state.isComplete) {
      connect();
    }

    return cleanup;
  }, [checkId]);

  // Cleanup on unmount
  useEffect(() => {
    return cleanup;
  }, []);

  const reconnect = () => {
    reconnectAttempts.current = 0;
    connect();
  };

  return {
    ...state,
    reconnect,
  };
}