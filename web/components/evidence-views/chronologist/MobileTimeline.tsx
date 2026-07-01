import { Evidence } from '@shared/types';
import { TierStamp } from '../librarian/TierStamp';
import { extractDomain, formatShortDate, cleanTitle } from '../shared-utils';
import type { DatedItem, ClusterItem } from './ChronologistView';

interface MobileTimelineProps {
  items: DatedItem[];
  clusters: ClusterItem[];
  undated: Evidence[];
  onCardClick: (evidence: Evidence) => void;
}

export function MobileTimeline({ items, clusters, undated, onCardClick }: MobileTimelineProps) {
  // Merge individual items and clusters into a single sorted list
  const allEntries: Array<{ date: Date; items: DatedItem[] }> = [];

  // Group individual items by date
  const itemsByDate = new Map<string, DatedItem[]>();
  for (const item of items) {
    const key = item.date.toISOString().slice(0, 10);
    const group = itemsByDate.get(key) || [];
    group.push(item);
    itemsByDate.set(key, group);
  }

  Array.from(itemsByDate.values()).forEach((group) => {
    allEntries.push({ date: group[0].date, items: group });
  });

  for (const cluster of clusters) {
    allEntries.push({ date: cluster.date, items: cluster.items });
  }

  allEntries.sort((a, b) => a.date.getTime() - b.date.getTime());

  return (
    <div>
      {/* Dated entries — vertical timeline */}
      <div className="relative pl-6 border-l border-zinc-200">
        {allEntries.map((entry, i) => (
          <div key={i} className="mb-4 relative">
            {/* Date dot on the timeline line */}
            <div
              className="absolute -left-[25px] top-1 rounded-full"
              style={{
                width: entry.items[0].dotSize,
                height: entry.items[0].dotSize,
                backgroundColor: entry.items[0].color,
              }}
            />
            {/* Date label */}
            <span className="font-mono text-[9px] text-zinc-400 block mb-1">
              {formatShortDate(entry.date)}
            </span>
            {/* Evidence cards */}
            {entry.items.map((item, j) => (
              <button
                key={j}
                onClick={() => onCardClick(item.evidence)}
                className="block w-full text-left border border-zinc-100 hover:border-zinc-300 p-2 mb-1 transition-colors"
              >
                <div className="flex items-start gap-2">
                  <div
                    className="rounded-full shrink-0 mt-1"
                    style={{
                      width: item.dotSize,
                      height: item.dotSize,
                      backgroundColor: item.color,
                    }}
                  />
                  <div className="min-w-0">
                    <p className="text-[11px] font-medium text-zinc-900 truncate">
                      {cleanTitle(item.evidence.title) || 'Untitled'}
                    </p>
                    <span className="font-mono text-[9px] text-zinc-400">
                      {extractDomain(item.evidence.url)}
                    </span>
                    {item.evidence.tier && (
                      <div className="mt-1">
                        <TierStamp tier={item.evidence.tier} />
                      </div>
                    )}
                  </div>
                </div>
              </button>
            ))}
          </div>
        ))}
      </div>

      {/* Undated section */}
      {undated.length > 0 && (
        <div className="mt-6 pt-4 border-t border-dashed border-zinc-200">
          <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-400 mb-3">
            Date Unknown &middot; {undated.length}
          </p>
          {undated.map((ev, i) => (
            <button
              key={ev.evidenceId || ev.id || i}
              onClick={() => onCardClick(ev)}
              className="block w-full text-left border border-zinc-100 hover:border-zinc-300 p-2 mb-1 transition-colors"
            >
              <p className="text-[11px] font-medium text-zinc-900 truncate">{cleanTitle(ev.title) || 'Untitled'}</p>
              <div className="flex items-center gap-1.5 mt-1">
                <span className="font-mono text-[9px] text-zinc-400">{extractDomain(ev.url)}</span>
              </div>
              {ev.tier && (
                <div className="mt-1">
                  <TierStamp tier={ev.tier} />
                </div>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
