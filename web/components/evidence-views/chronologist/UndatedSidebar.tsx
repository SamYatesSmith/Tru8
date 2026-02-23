import { Evidence } from '@shared/types';

function extractDomain(url: string): string {
  try { return new URL(url).hostname.replace(/^www\./, ''); } catch { return url; }
}

interface UndatedSidebarProps {
  evidence: Evidence[];
}

export function UndatedSidebar({ evidence }: UndatedSidebarProps) {
  return (
    <div className="w-56 shrink-0 border-l border-dashed border-zinc-200 pl-4">
      <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-400 mb-3">
        Date Unknown &middot; {evidence.length}
      </p>
      <div className="space-y-2">
        {evidence.map((ev, i) => (
          <a
            key={ev.evidenceId || ev.id || i}
            href={ev.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block border border-zinc-100 hover:border-zinc-300 p-2 transition-colors"
          >
            <p className="text-[11px] font-medium text-zinc-900 truncate">{ev.title || 'Untitled'}</p>
            <div className="flex items-center gap-1.5 mt-1">
              <span className="font-mono text-[9px] text-zinc-400">{extractDomain(ev.url)}</span>
              {ev.tier && (
                <>
                  <span className="font-mono text-[9px] text-zinc-300">&middot;</span>
                  <span className="font-mono text-[9px] uppercase text-zinc-400">{ev.tier}</span>
                </>
              )}
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
