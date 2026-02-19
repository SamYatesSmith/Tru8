'use client';

import { VideoRecommendation } from '@shared/types';
import { TierBadge } from '../TierBadge';
import { TypeBadge } from '../TypeBadge';

interface VideoCardProps {
  video: VideoRecommendation;
}

function formatDuration(iso: string | undefined): string | null {
  if (!iso) return null;
  // Parse ISO 8601 duration e.g. "PT4M32S" → "4:32"
  const match = iso.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/);
  if (!match) return null;
  const h = parseInt(match[1] || '0', 10);
  const m = parseInt(match[2] || '0', 10);
  const s = parseInt(match[3] || '0', 10);
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  return `${m}:${String(s).padStart(2, '0')}`;
}

function formatDate(dateStr: string | undefined): string | null {
  if (!dateStr) return null;
  try {
    return new Date(dateStr).toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return null;
  }
}

export function VideoCard({ video }: VideoCardProps) {
  const duration = formatDuration(video.duration);
  const date = formatDate(video.publishDate);

  return (
    <a
      href={video.videoUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="block border border-zinc-100 bg-white overflow-hidden transition-all duration-150 cursor-pointer hover:border-zinc-300 hover:-translate-y-px group"
    >
      {/* Thumbnail */}
      <div className="relative aspect-video bg-zinc-100 flex items-center justify-center">
        {video.thumbnailUrl ? (
          <img
            src={video.thumbnailUrl}
            alt={video.title}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        ) : null}
        {/* Play indicator */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-10 h-10 rounded-full bg-white/80 flex items-center justify-center opacity-70 group-hover:opacity-100 transition-opacity">
            <div className="w-0 h-0 ml-0.5 border-l-[10px] border-l-zinc-800 border-y-[6px] border-y-transparent" />
          </div>
        </div>
        {/* Duration badge */}
        {duration && (
          <div className="absolute bottom-2 right-2 bg-black/80 px-1.5 py-0.5">
            <span className="font-mono text-[10px] text-white font-medium">{duration}</span>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Tier + Type badges */}
        {(video.tierLabel || video.typeLabel) && (
          <div className="flex items-center gap-2 mb-2">
            {video.tierLabel && <TierBadge tier={video.tierLabel} />}
            {video.typeLabel && <TypeBadge type={video.typeLabel} />}
          </div>
        )}

        {/* Title */}
        <div className="text-sm font-medium text-zinc-900 mb-1.5 line-clamp-2">
          {video.title}
        </div>

        {/* Metadata row */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-mono text-[10px] text-zinc-400">{video.channelName}</span>
          <span className="font-mono text-[10px] text-zinc-300">&middot;</span>
          <span className="font-mono text-[10px] text-zinc-400">youtube.com</span>
          {date && (
            <>
              <span className="font-mono text-[10px] text-zinc-300">&middot;</span>
              <span className="font-mono text-[10px] text-zinc-400">{date}</span>
            </>
          )}
        </div>
      </div>
    </a>
  );
}
