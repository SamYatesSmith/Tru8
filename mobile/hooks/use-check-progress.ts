import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@clerk/clerk-expo';
import { getCheck } from '@/lib/api';
import type { Check } from '@shared/types';

type PipelineStage = 'pending' | 'processing' | 'ingest' | 'extract' | 'retrieve' | 'verify' | 'judge' | 'completed' | 'failed';

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
          stage = 'judge'; // Has results, likely in final judgment
          progress = 90;
        } else {
          // Still processing, estimate based on processing time
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