import { useEffect, useState, useCallback, useRef } from 'react';
import { useAuth } from '@clerk/clerk-expo';
import { AppState, AppStateStatus } from 'react-native';
import EventSource from 'react-native-sse';
import { getCheck } from '@/lib/api';
import type { Check, PipelineProgress } from '@shared/types';

type PipelineStage = 'pending' | 'processing' | 'ingest' | 'extract' | 'retrieve' | 'verify' | 'judge' | 'completed' | 'failed';

interface ProgressEvent {
  type: 'connected' | 'progress' | 'completed' | 'error' | 'heartbeat' | 'timeout';
  checkId: string;
  stage?: PipelineStage;
  progress?: number; // 0-100
  message?: string;
  timestamp?: string;
  error?: string;
  status?: string;
}

interface RealTimeProgressState {
  check?: Check;
  stage: PipelineStage;
  progress: number; // 0-100
  message?: string;
  isLoading: boolean;
  isError: boolean;
  error?: string;
  isConnected: boolean;
  connectionAttempts: number;
}

const STAGE_PROGRESS = {
  pending: 0,
  processing: 10,
  ingest: 20,
  extract: 40,
  retrieve: 60,
  verify: 75,
  judge: 90,
  completed: 100,
  failed: 0,
};

const STAGE_MESSAGES = {
  pending: 'Queued for processing...',
  processing: 'Starting fact-check...',
  ingest: 'Processing your content...',
  extract: 'Finding claims to fact-check...',
  retrieve: 'Gathering evidence from sources...',
  verify: 'Checking claims against evidence...',
  judge: 'Generating verdict and rationale...',
  completed: 'Fact-check complete!',
  failed: 'Processing failed',
};

const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 2000; // 2 seconds
const FALLBACK_POLLING_INTERVAL = 3000; // 3 seconds

/**
 * Hook to monitor check progress via real-time SSE connection with polling fallback
 */
export function useRealTimeProgress(checkId: string | null) {
  const { getToken } = useAuth();
  const [state, setState] = useState<RealTimeProgressState>({
    stage: 'pending',
    progress: 0,
    isLoading: false,
    isError: false,
    isConnected: false,
    connectionAttempts: 0,
  });

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const appStateRef = useRef<AppStateStatus>(AppState.currentState);
  const connectionAttemptsRef = useRef<number>(0);
  const scheduleReconnectRef = useRef<() => void>();

  const cleanup = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  }, []);

  const fallbackToPolling = useCallback(async () => {
    console.log('Falling back to polling for check progress');
    
    const poll = async () => {
      if (!checkId) return;
      
      try {
        const token = await getToken();
        if (!token) return;

        const check = await getCheck(checkId, token);
        
        let stage: PipelineStage = 'pending';
        let progress = 0;
        
        if (check.status === 'failed') {
          stage = 'failed';
          progress = 0;
        } else if (check.status === 'completed') {
          stage = 'completed';
          progress = 100;
        } else if (check.status === 'processing') {
          // Estimate stage based on whether we have claims/results
          if (check.claims && check.claims.length > 0) {
            stage = 'judge';
            progress = 90;
          } else {
            // Estimate based on processing time
            const processingTime = check.processingTimeMs || 0;
            if (processingTime > 8000) {
              stage = 'verify';
              progress = 75;
            } else if (processingTime > 5000) {
              stage = 'retrieve';
              progress = 60;
            } else if (processingTime > 2000) {
              stage = 'extract';
              progress = 40;
            } else {
              stage = 'ingest';
              progress = 20;
            }
          }
        }

        setState(prevState => ({
          ...prevState,
          check,
          stage,
          progress,
          message: STAGE_MESSAGES[stage],
          isLoading: false,
          isError: false,
          error: undefined,
        }));

        // Stop polling if completed or failed
        if (stage === 'completed' || stage === 'failed') {
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
          }
        }
      } catch (error: any) {
        console.error('Polling error:', error);
        setState(prevState => ({
          ...prevState,
          isError: true,
          error: error.message || 'Failed to fetch progress',
        }));
      }
    };

    // Initial poll
    await poll();
    
    // Start polling interval
    pollingIntervalRef.current = setInterval(poll, FALLBACK_POLLING_INTERVAL);
  }, [checkId, getToken]);

  const connectSSE = useCallback(async () => {
    if (!checkId || connectionAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
      console.log('Max reconnection attempts reached, falling back to polling');
      await fallbackToPolling();
      return;
    }

    try {
      const token = await getToken();
      if (!token) {
        setState(prevState => ({
          ...prevState,
          isError: true,
          error: 'Authentication token not available',
        }));
        return;
      }

      cleanup();

      // Security fix: Use headers instead of query params for token
      // Note: react-native-sse supports headers
      const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';
      const url = `${API_URL}/api/v1/checks/${checkId}/progress`;
      
      console.log('Connecting to SSE:', url);
      
      const eventSource = new EventSource(url, {
        headers: {
          'Authorization': `Bearer ${token}`,
        }
      });
      eventSourceRef.current = eventSource;

      connectionAttemptsRef.current += 1;
      setState(prevState => ({
        ...prevState,
        connectionAttempts: connectionAttemptsRef.current,
        isLoading: true,
      }));

      eventSource.addEventListener('open', () => {
        console.log('SSE connection opened');
        connectionAttemptsRef.current = 0; // Reset on successful connection
        setState(prevState => ({
          ...prevState,
          isConnected: true,
          isError: false,
          error: undefined,
          connectionAttempts: 0,
        }));
      });

      eventSource.addEventListener('message', (event: any) => {
        try {
          const data: ProgressEvent = JSON.parse(event.data);
          console.log('SSE Progress event:', data);

          switch (data.type) {
            case 'connected':
              setState(prevState => ({
                ...prevState,
                isConnected: true,
                isLoading: false,
              }));
              break;

            case 'progress':
              if (data.stage && data.progress !== undefined) {
                setState(prevState => ({
                  ...prevState,
                  stage: data.stage!,
                  progress: data.progress!,
                  message: data.message || STAGE_MESSAGES[data.stage!],
                  isLoading: false,
                  isError: false,
                  error: undefined,
                }));
              }
              break;

            case 'completed':
              setState(prevState => ({
                ...prevState,
                stage: 'completed',
                progress: 100,
                message: STAGE_MESSAGES.completed,
                isLoading: false,
                isError: false,
              }));
              cleanup(); // Stop SSE when complete
              break;

            case 'error':
              setState(prevState => ({
                ...prevState,
                stage: 'failed',
                progress: 0,
                message: data.error || 'Processing failed',
                isLoading: false,
                isError: true,
                error: data.error,
              }));
              cleanup();
              break;

            case 'heartbeat':
              // Keep connection alive
              console.log('SSE heartbeat received');
              break;

            case 'timeout':
              console.log('SSE timeout, reconnecting...');
              scheduleReconnectRef.current?.();
              break;
          }
        } catch (error) {
          console.error('Error parsing SSE message:', error);
        }
      });

      eventSource.addEventListener('error', (error: any) => {
        console.error('SSE connection error:', error);
        setState(prevState => ({
          ...prevState,
          isConnected: false,
        }));
        scheduleReconnectRef.current?.();
      });

    } catch (error: any) {
      console.error('Failed to establish SSE connection:', error);
      scheduleReconnectRef.current?.();
    }
  }, [checkId, getToken, cleanup, fallbackToPolling]);

  // Define scheduleReconnect after connectSSE to avoid circular dependency
  useEffect(() => {
    scheduleReconnectRef.current = () => {
      if (connectionAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
        console.log(`Scheduling reconnect attempt ${connectionAttemptsRef.current + 1}/${MAX_RECONNECT_ATTEMPTS}`);
        reconnectTimeoutRef.current = setTimeout(() => {
          connectSSE();
        }, RECONNECT_DELAY);
      } else {
        console.log('Max reconnect attempts reached, falling back to polling');
        fallbackToPolling();
      }
    };
  }, [connectSSE, fallbackToPolling]);

  // Handle app state changes (foreground/background)
  useEffect(() => {
    const handleAppStateChange = (nextAppState: AppStateStatus) => {
      if (appStateRef.current.match(/inactive|background/) && nextAppState === 'active') {
        // App has come to the foreground
        console.log('App became active, reconnecting SSE');
        if (checkId && (state.stage === 'processing' || state.stage === 'pending')) {
          connectSSE();
        }
      } else if (nextAppState.match(/inactive|background/)) {
        // App is going to background
        console.log('App going to background, cleaning up connections');
        cleanup();
      }
      appStateRef.current = nextAppState;
    };

    const subscription = AppState.addEventListener('change', handleAppStateChange);
    return () => subscription?.remove();
  }, [checkId, state.stage, connectSSE, cleanup]);

  // Main effect to start monitoring
  useEffect(() => {
    if (!checkId) {
      setState({
        stage: 'pending',
        progress: 0,
        isLoading: false,
        isError: false,
        isConnected: false,
        connectionAttempts: 0,
      });
      cleanup();
      return;
    }

    // Start with SSE, fallback to polling if needed
    connectSSE();

    return cleanup;
  }, [checkId, connectSSE, cleanup]);

  const retry = useCallback(() => {
    if (checkId) {
      connectionAttemptsRef.current = 0;
      setState(prevState => ({
        ...prevState,
        connectionAttempts: 0,
        isLoading: true,
        isError: false,
        error: undefined,
      }));
      connectSSE();
    }
  }, [checkId, connectSSE]);

  return {
    ...state,
    retry,
    isRealTime: eventSourceRef.current !== null,
    isPolling: pollingIntervalRef.current !== null,
  };
}