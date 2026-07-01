import { Evidence } from '@shared/types';
import { TierStamp } from '../librarian/TierStamp';
import { extractDomain, cleanTitle } from '../shared-utils';

interface UndatedSidebarProps {
  evidence: Evidence[];
  onCardClick: (evidence: Evidence) => void;
}

export function UndatedSidebar({ evidence, onCardClick }: UndatedSidebarProps) {
  return (
    <div className="w-56 shrink-0 border-l border-dashed border-zinc-200 pl-4">
      <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-400 mb-3">
        Date Unknown &middot; {evidence.length}
      </p>
      <div className="space-y-2">
        {evidence.map((ev, i) => (
          <button
            key={ev.evidenceId || ev.id || i}
            onClick={() => onCardClick(ev)}
            className="block w-full text-left border border-zinc-100 hover:border-zinc-300 p-2 transition-colors"
          >
            <p className="text-[11px] font-medium text-zinc-900 truncate">{cleanTitle(ev.title) || 'Untitled'}</p>
            <div className="flex items-center gap-1.5 mt-1">
              <span className="font-mono text-[9px] text-zinc-400">{extractDomain(ev.url)}</span>
            </div>
            {ev.tier && (
              <div className="mt-1.5">
                <TierStamp tier={ev.tier} />
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
