'use client';

import { useState, useEffect } from 'react';
import { VideoRecommendation } from '@shared/types';
import { apiClient } from '@/lib/api';

interface UseVideoRecommendationsReturn {
  videos: VideoRecommendation[];
  isLoading: boolean;
  error: string | null;
}

export function useVideoRecommendations(
  checkId: string,
  claimId: string | null,
  token: string | null,
  enabled: boolean = true,
): UseVideoRecommendationsReturn {
  const [videos, setVideos] = useState<VideoRecommendation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled || !token || !checkId) return;

    let cancelled = false;
    const fetchVideos = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await apiClient.getCheckVideos(checkId, claimId, token) as {
          checkId: string;
          videos: VideoRecommendation[];
        };
        if (!cancelled) {
          setVideos(result.videos || []);
        }
      } catch (e: any) {
        if (!cancelled) {
          setError(e.message || 'Failed to load videos');
          setVideos([]);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    fetchVideos();
    return () => { cancelled = true; };
  }, [checkId, claimId, token, enabled]);

  return { videos, isLoading, error };
}
