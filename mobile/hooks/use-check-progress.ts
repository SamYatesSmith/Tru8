import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@clerk/clerk-expo';
import { getCheck } from '@/lib/api';
import type { Check } from '@shared/types';

type PipelineStage = 'pending' | 'processing' | 'ingest' | 'extract' | 'retrieve' | 'select' | 'decompose' | 'analyze' | 'completed' | 'failed';

interface ProgressState {
  check?: Check;
  stage: PipelineStage;
  progress: number; // 0-100
  message?: string;
  isLoading: boolean;
  isError: boolean;
  error?: string;
}

const STAGE_PROGRESS = {
  pending: 0,
  processing: 5,
  ingest: 10,
  extract: 25,
  retrieve: 40,
  select: 55,
  decompose: 70,
  analyze: 85,
  completed: 100,
  failed: 0,
};

const STAGE_MESSAGES = {
  pending: 'Queued for processing...',
  processing: 'Starting analysis...',
  ingest: 'Processing your content...',
  extract: 'Identifying claims...',
  retrieve: 'Gathering evidence from sources...',
  select: 'Ranking claims for analysis...',
  decompose: 'Breaking claims into elements...',
  analyze: 'Mapping evidence to claim elements...',
  completed: 'Analysis complete!',
  failed: 'Processing failed',
};

/**
 * Hook to monitor check progress via polling
 * Since React Native doesn't support EventSource, we poll the API every 2 seconds
 */
export function useCheckProgress(checkId: string | null) {
  const { getToken } = useAuth();
  const [state, setState] = useState<ProgressState>({
    stage: 'pending',
    progress: 0,
    isLoading: false,
    isError: false,
  });

  const [intervalId, setIntervalId] = useState<NodeJS.Timeout | null>(null);

  const fetchCheckStatus = useCallback(async () => {
    if (!checkId) return;
    
    try {
      const token = await getToken();
      if (!token) {
        setState(prev => ({
          ...prev,
          isError: true,
          error: 'Not authenticated',
        }));
        return;
      }

      const check = await getCheck(checkId, token);
      
      // Determine stage from check status and data
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
          stage = 'analyze'; // Has results, likely in final analysis
          progress = 85;
        } else {
          // Still processing, estimate based on processing time
          const processingTime = check.processingTimeMs || 0;
          if (processingTime > 12000) {
            stage = 'analyze';
            progress = 85;
          } else if (processingTime > 10000) {
            stage = 'decompose';
            progress = 70;
          } else if (processingTime > 8000) {
            stage = 'select';
            progress = 55;
          } else if (processingTime > 5000) {
            stage = 'retrieve';
            progress = 40;
          } else if (processingTime > 2000) {
            stage = 'extract';
            progress = 25;
          } else {
            stage = 'ingest';
            progress = 10;
          }
        }
      } else {
        stage = 'pending';
        progress = 0;
      }

      setState({
        check,
        stage,
        progress,
        message: STAGE_MESSAGES[stage],
        isLoading: false,
        isError: false,
      });

      // Stop polling if completed or failed
      if (stage === 'completed' || stage === 'failed') {
        if (intervalId) {
          clearInterval(intervalId);
          setIntervalId(null);
        }
      }

    } catch (error: any) {
      console.error('Error fetching check progress:', error);
      setState(prev => ({
        ...prev,
        isError: true,
        error: error.message || 'Failed to fetch check status',
        isLoading: false,
      }));
    }
  }, [checkId, getToken, intervalId]);

  // Start polling when checkId is provided
  useEffect(() => {
    if (!checkId) {
      setState({
        stage: 'pending',
        progress: 0,
        isLoading: false,
        isError: false,
      });
      return;
    }

    setState(prev => ({
      ...prev,
      isLoading: true,
      isError: false,
    }));

    // Initial fetch
    fetchCheckStatus();

    // Start polling every 2 seconds
    const id = setInterval(fetchCheckStatus, 2000);
    setIntervalId(id);

    return () => {
      if (id) {
        clearInterval(id);
      }
      setIntervalId(null);
    };
  }, [checkId]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [intervalId]);

  const retry = useCallback(() => {
    if (checkId) {
      setState(prev => ({
        ...prev,
        isLoading: true,
        isError: false,
        error: undefined,
      }));
      fetchCheckStatus();
    }
  }, [checkId, fetchCheckStatus]);

  return {
    ...state,
    retry,
    isPolling: intervalId !== null,
  };
}