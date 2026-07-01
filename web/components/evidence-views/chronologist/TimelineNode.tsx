import { Evidence } from '@shared/types';
import { getFaviconUrl, cleanTitle } from '../shared-utils';

interface TimelineNodeProps {
  evidence: Evidence;
  color: string;
  tierLabel: string;
  dotSize: number;
  domain: string;
  date: string;
  isSelected?: boolean;
  /** Horizontal position 0-100% — used to keep tooltip within viewport */
  positionPct?: number;
  onClick: () => void;
}

export function TimelineNode({
  evidence,
  color,
  tierLabel,
  dotSize,
  domain,
  date,
  isSelected,
  positionPct,
  onClick,
}: TimelineNodeProps) {
  const firstLetter = domain.charAt(0).toUpperCase();
  const faviconUrl = getFaviconUrl(evidence.url);

  // Tooltip alignment: left-align near left edge, right-align near right edge, centre otherwise
  let tooltipAlign = 'left-1/2 -translate-x-1/2'; // centre (default)
  if (typeof positionPct === 'number') {
    if (positionPct < 12) tooltipAlign = 'left-0';
    else if (positionPct > 88) tooltipAlign = 'right-0';
  }

  return (
    <button onClick={onClick} className="group relative cursor-pointer">
      <div
        className={`rounded-full overflow-hidden flex items-center justify-center bg-white relative ${isSelected ? 'ring-2 ring-offset-1' : ''} transition-transform group-hover:scale-110`}
        style={{
          width: dotSize,
          height: dotSize,
          border: `2px solid ${color}`,
          ...(isSelected ? { ['--tw-ring-color' as string]: color } : {}),
        }}
      >
        <span className="font-mono font-bold text-zinc-400" style={{ fontSize: Math.max(6, dotSize * 0.4) }}>{firstLetter}</span>
        {faviconUrl && (
          <img
            src={faviconUrl}
            alt=""
            className="absolute inset-0 w-full h-full rounded-full"
            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
          />
        )}
      </div>
      {/* Tooltip — edge-aware positioning */}
      <div className={`absolute bottom-full ${tooltipAlign} mb-2 hidden group-hover:block z-20 pointer-events-none`}>
        <div className="bg-zinc-900 text-white px-3 py-2 max-w-[220px] whitespace-normal">
          <p className="font-mono text-[10px] font-medium truncate">{cleanTitle(evidence.title) || 'Untitled'}</p>
          <div className="flex items-center gap-1.5 mt-1">
            <span className="font-mono text-[9px] text-zinc-400">{domain}</span>
            <span className="font-mono text-[9px] text-zinc-600">&middot;</span>
            <span className="font-mono text-[9px] text-zinc-400">{date}</span>
          </div>
          <span className="font-mono text-[8px] uppercase tracking-wider text-zinc-500 mt-1 block">{tierLabel}</span>
        </div>
      </div>
    </button>
  );
}
