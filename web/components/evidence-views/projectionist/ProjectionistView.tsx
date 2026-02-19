'use client';

import { useMemo } from 'react';
import { Claim, VideoRecommendation } from '@shared/types';
import { VideoGrid } from './VideoGrid';
import { EmptyVideoState } from './EmptyVideoState';
import { ClaimSummary } from './ClaimSummary';
import { VideoProvenanceNote } from './VideoProvenanceNote';

interface ProjectionistViewProps {
  scope: 'check' | 'claim';
  claims: Claim[];
  videos: VideoRecommendation[];
  isLoading?: boolean;
}

export function ProjectionistView({ scope, claims, videos, isLoading }: ProjectionistViewProps) {
  // For check-wide scope, show all videos (max 5 total).
  // For per-claim scope, show videos for that claim only (max 5).
  const scopedVideos = useMemo(() => {
    if (scope === 'check') {
      // Dedupe by videoId across all claims, cap at 5
      const seen = new Set<string>();
      const deduped: VideoRecommendation[] = [];
      for (const v of videos) {
        if (!seen.has(v.videoId)) {
          seen.add(v.videoId);
          deduped.push(v);
        }
        if (deduped.length >= 5) break;
      }
      return deduped;
    }

    // Per-claim: videos are already filtered by claimId from the hook
    return videos.slice(0, 5);
  }, [scope, videos]);

  // Get orientation line for ClaimSummary (per-claim only)
  const orientation = useMemo(() => {
    if (scope !== 'claim' || claims.length === 0) return null;
    return claims[0]?.claimMap?.orientation ?? null;
  }, [scope, claims]);

  if (isLoading) {
    return (
      <div className="py-16 text-center">
        <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-400 animate-pulse">
          Loading video context...
        </p>
      </div>
    );
  }

  return (
    <div>
      {/* Claim Summary (per-claim only) */}
      {scope === 'claim' && <ClaimSummary orientation={orientation} />}

      {/* Video count header */}
      <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-zinc-400 mb-6 border-b border-zinc-100 pb-2">
        Videos &middot; {scopedVideos.length}
      </div>

      {/* Video grid or empty state */}
      {scopedVideos.length > 0 ? (
        <VideoGrid videos={scopedVideos} />
      ) : (
        <EmptyVideoState />
      )}

      {/* Provenance */}
      <VideoProvenanceNote />
    </div>
  );
}
