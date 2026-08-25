'use client';

import { useState } from 'react';
import { Evidence } from '@shared/types';
import { TimelineNode } from './TimelineNode';
import { extractDomain, formatShortDate, cleanTitle } from '../shared-utils';
import type { DatedItem } from './ChronologistView';

interface TimelineClusterProps {
  count: number;
  items: DatedItem[];
  dominantColor: string;
  onNodeClick: (evidence: Evidence) => void;
  selectedEvidenceId?: string;
  /** Horizontal position 0-100% — forwarded to nodes for tooltip edge-awareness */
  positionPct?: number;
}

export function TimelineCluster({ count, items, dominantColor, onNodeClick, selectedEvidenceId, positionPct }: TimelineClusterProps) {
  const [expanded, setExpanded] = useState(false);

  // Tooltip alignment for the cluster itself
  let tooltipAlign = 'left-1/2 -translate-x-1/2';
  if (typeof positionPct === 'number') {
    if (positionPct < 12) tooltipAlign = 'left-0';
    else if (positionPct > 88) tooltipAlign = 'right-0';
  }

  if (expanded) {
    return (
      <div className="flex flex-col-reverse gap-1 items-center">
        {items.map((item, i) => (
          <TimelineNode
            key={i}
            evidence={item.evidence}
            color={item.color}
            tierLabel={item.tierLabel}
            dotSize={item.dotSize}
            domain={extractDomain(item.evidence.url)}
            date={formatShortDate(item.date)}
            isSelected={selectedEvidenceId === (item.evidence.evidenceId || item.evidence.id)}
            positionPct={positionPct}
            onClick={() => onNodeClick(item.evidence)}
          />
        ))}
        <button
          onClick={() => setExpanded(false)}
          className="font-mono text-[8px] text-zinc-400 hover:text-zinc-600 transition-colors"
        >
          &minus;
        </button>
      </div>
    );
  }

  return (
    <button onClick={() => setExpanded(true)} className="group relative cursor-pointer">
      <div
        className="w-5 h-5 rounded-full flex items-center justify-center border-2 border-white ring-1 ring-zinc-200 ring-offset-1 transition-transform group-hover:scale-110"
        style={{ backgroundColor: dominantColor }}
      >
        <span className="font-mono text-[9px] font-bold text-white">{count}</span>
      </div>
      {/* Tooltip — edge-aware */}
      <div className={`absolute bottom-full ${tooltipAlign} mb-2 hidden group-hover:block z-20 pointer-events-none`}>
        <div className="bg-zinc-900 text-white px-3 py-2 max-w-[220px] whitespace-normal">
          <p className="font-mono text-[9px] text-zinc-400 mb-1">
            {count} sources on {formatShortDate(items[0].date)}
          </p>
          {items.slice(0, 3).map((item, i) => (
            <p key={i} className="font-mono text-[10px] line-clamp-2 break-words">{cleanTitle(item.evidence.title) || 'Untitled'}</p>
          ))}
          {items.length > 3 && (
            <p className="font-mono text-[9px] text-zinc-500 mt-1">+{items.length - 3} more &middot; Click to expand</p>
          )}
        </div>
      </div>
    </button>
  );
}
