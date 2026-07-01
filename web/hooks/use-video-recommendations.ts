'use client';

import { useState, useEffect } from 'react';
import { VideoRecommendation } from '@shared/types';
import { apiClient } from '@/lib/api';

interface UseVideoRecommendationsReturn {
  videos: VideoRecommendation[];
  isLoading: boolean;
  error: string | null;
}

// Video recommendations are written by a fire-and-forget task that completes
// ~1s AFTER the check is marked complete, so a single fetch on page load can
// race (and lose to) that write — leaving the Video tab hidden for the whole
// session even though videos exist. We re-poll a few times when the first fetch
// comes back empty, silently (isLoading stays false so the tab doesn't flicker
// in-then-out), and surface the videos the moment they land.
const MAX_ATTEMPTS = 5; // initial + 4 retries
const RETRY_MS = 2500; // ~10s total window — comfortably covers the ~1s race

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
    let attempt = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let recoveryTried = false;

    // Last resort: if the retry window elapses with still no videos, the
    // fire-and-forget generation task was almost certainly lost (an API
    // restart in its short window). Trigger a durable, owner-only regeneration
    // once — the Video tab then self-heals when the videos land.
    const maybeRecover = () => {
      if (recoveryTried || cancelled || !token) return;
      recoveryTried = true;
      apiClient
        .recoverCheckVideos(checkId, token)
        .then((result) => {
          if (cancelled) return;
          const vids = (result as { videos?: VideoRecommendation[] }).videos || [];
          if (vids.length > 0) setVideos(vids);
        })
        .catch(() => {
          /* silent — this is already the fallback */
        });
    };

    const fetchVideos = async (isRetry: boolean) => {
      if (!isRetry) setIsLoading(true);
      try {
        const result = (await apiClient.getCheckVideos(checkId, claimId, token)) as {
          checkId: string;
          videos: VideoRecommendation[];
        };
        if (cancelled) return;
        const vids = result.videos || [];
        if (vids.length > 0) {
          setVideos(vids);
          if (!isRetry) setIsLoading(false);
          return; // done — tab appears
        }
        // Empty: finish the initial load (tab stays hidden, no flicker) and
        // keep retrying silently in case the fire-and-forget write is still in flight.
        if (!isRetry) setIsLoading(false);
        if (attempt < MAX_ATTEMPTS - 1) {
          attempt += 1;
          timer = setTimeout(() => fetchVideos(true), RETRY_MS);
        } else {
          maybeRecover();
        }
      } catch (e: any) {
        if (cancelled) return;
        if (!isRetry) {
          setError(e.message || 'Failed to load videos');
          setVideos([]);
          setIsLoading(false);
        }
        // Retry transient errors too.
        if (attempt < MAX_ATTEMPTS - 1) {
          attempt += 1;
          timer = setTimeout(() => fetchVideos(true), RETRY_MS);
        } else {
          maybeRecover();
        }
      }
    };

    fetchVideos(false);
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [checkId, claimId, token, enabled]);

  return { videos, isLoading, error };
}
