'use client';

import { useState } from 'react';
import { TimelineNode } from './TimelineNode';
import type { DatedItem } from './ChronologistView';

function extractDomain(url: string): string {
  try { return new URL(url).hostname.replace(/^www\./, ''); } catch { return url; }
}

function formatShortDate(date: Date): string {
  return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

interface TimelineClusterProps {
  count: number;
  items: DatedItem[];
  dominantColor: string;
}

export function TimelineCluster({ count, items, dominantColor }: TimelineClusterProps) {
  const [expanded, setExpanded] = useState(false);

  if (expanded) {
    return (
      <div className="flex flex-col-reverse gap-1 items-center">
        {items.map((item, i) => (
          <TimelineNode
            key={i}
            color={item.color}
            title={item.evidence.title || 'Untitled'}
            domain={extractDomain(item.evidence.url)}
            date={formatShortDate(item.date)}
            tier={item.evidence.tier}
            url={item.evidence.url}
            label={item.label}
          />
        ))}
      </div>
    );
  }

  return (
    <button onClick={() => setExpanded(true)} className="group relative cursor-pointer">
      <div
        className="w-5 h-5 rounded-full flex items-center justify-center border-2 border-white shadow-sm transition-transform group-hover:scale-110"
        style={{ backgroundColor: dominantColor }}
      >
        <span className="font-mono text-[9px] font-bold text-white">{count}</span>
      </div>
      {/* Tooltip */}
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-20 pointer-events-none">
        <div className="bg-zinc-900 text-white px-3 py-2 max-w-[200px]">
          <p className="font-mono text-[9px] text-zinc-400 mb-1">
            {count} sources on {formatShortDate(items[0].date)}
          </p>
          {items.slice(0, 3).map((item, i) => (
            <p key={i} className="font-mono text-[10px] truncate">{item.evidence.title || 'Untitled'}</p>
          ))}
          {items.length > 3 && (
            <p className="font-mono text-[9px] text-zinc-500 mt-1">+{items.length - 3} more &middot; Click to expand</p>
          )}
        </div>
      </div>
    </button>
  );
}
