'use client';

import { VideoRecommendation } from '@shared/types';
import { VideoCard } from './VideoCard';

interface VideoGridProps {
  videos: VideoRecommendation[];
}

export function VideoGrid({ videos }: VideoGridProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-12">
      {videos.map((video) => (
        <VideoCard key={video.videoId} video={video} />
      ))}
    </div>
  );
}
