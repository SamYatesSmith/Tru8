import { Evidence } from '@shared/types';
import type { DatedItem, ClusterItem } from './ChronologistView';

function extractDomain(url: string): string {
  try { return new URL(url).hostname.replace(/^www\./, ''); } catch { return url; }
}

function formatShortDate(date: Date): string {
  return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

interface MobileTimelineProps {
  items: DatedItem[];
  clusters: ClusterItem[];
  undated: Evidence[];
}

export function MobileTimeline({ items, clusters, undated }: MobileTimelineProps) {
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
              className="absolute -left-[25px] top-1 w-2 h-2 rounded-full"
              style={{ backgroundColor: entry.items[0].color }}
            />
            {/* Date label */}
            <span className="font-mono text-[9px] text-zinc-400 block mb-1">
              {formatShortDate(entry.date)}
            </span>
            {/* Evidence cards */}
            {entry.items.map((item, j) => (
              <a
                key={j}
                href={item.evidence.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block border border-zinc-100 hover:border-zinc-300 p-2 mb-1 transition-colors"
              >
                <div className="flex items-start gap-2">
                  <div
                    className="w-2.5 h-2.5 rounded-full shrink-0 mt-1"
                    style={{ backgroundColor: item.color }}
                  />
                  <div className="min-w-0">
                    <p className="text-[11px] font-medium text-zinc-900 truncate">
                      {item.evidence.title || 'Untitled'}
                    </p>
                    <span className="font-mono text-[9px] text-zinc-400">
                      {extractDomain(item.evidence.url)}
                    </span>
                    {item.label && (
                      <span className="font-mono text-[9px] text-zinc-300 ml-1.5">&middot; {item.label}</span>
                    )}
                  </div>
                </div>
              </a>
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
            <a
              key={ev.evidenceId || ev.id || i}
              href={ev.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block border border-zinc-100 hover:border-zinc-300 p-2 mb-1 transition-colors"
            >
              <p className="text-[11px] font-medium text-zinc-900 truncate">{ev.title || 'Untitled'}</p>
              <span className="font-mono text-[9px] text-zinc-400">{extractDomain(ev.url)}</span>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
