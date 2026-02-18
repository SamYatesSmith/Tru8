'use client';

import { useMemo, useState } from 'react';
import { Evidence, EvidenceTier, EvidenceType } from '@shared/types';

const TIERS: EvidenceTier[] = ['primary', 'reporting', 'commentary'];
const TYPES: EvidenceType[] = ['data', 'official_statement', 'news_reporting', 'analysis', 'opinion', 'academic'];

const TIER_LABELS: Record<EvidenceTier, string> = {
  primary: 'Primary',
  reporting: 'Reporting',
  commentary: 'Commentary',
};

const TYPE_LABELS: Record<EvidenceType, string> = {
  data: 'Data',
  official_statement: 'Official',
  news_reporting: 'News',
  analysis: 'Analysis',
  opinion: 'Opinion',
  academic: 'Academic',
};

const TIER_BAR_COLORS: Record<EvidenceTier, string> = {
  primary: 'bg-[var(--tier1-accent)]',
  reporting: 'bg-zinc-600',
  commentary: 'bg-zinc-400',
};

function getCellStyle(count: number): { bg: string; border: string; text: string } {
  if (count === 0) return { bg: 'bg-white', border: 'border-zinc-100', text: 'text-zinc-200' };
  if (count <= 2) return { bg: 'bg-zinc-50', border: 'border-zinc-100', text: 'text-zinc-500' };
  if (count <= 5) return { bg: 'bg-zinc-100', border: 'border-zinc-200', text: 'text-zinc-600' };
  return { bg: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-700' };
}

interface EvidenceHeatmapProps {
  evidence: Evidence[];
  onCellClick?: (tier: EvidenceTier, type: EvidenceType) => void;
}

export function EvidenceHeatmap({ evidence, onCellClick }: EvidenceHeatmapProps) {
  const [hoveredCell, setHoveredCell] = useState<string | null>(null);

  const { counts, sources } = useMemo(() => {
    const counts: Record<string, number> = {};
    const sources: Record<string, string[]> = {};

    for (const ev of evidence) {
      const tier = ev.tier || 'commentary';
      const type = ev.evidenceType || 'news_reporting';
      const key = `${tier}:${type}`;
      counts[key] = (counts[key] || 0) + 1;
      if (!sources[key]) sources[key] = [];
      if (ev.source && sources[key].length < 5) {
        sources[key].push(ev.source);
      }
    }

    return { counts, sources };
  }, [evidence]);

  return (
    <div className="mb-10">
      <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-zinc-400 mb-6 border-b border-zinc-100 pb-2">
        Evidence Profile
      </div>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className="w-28"></th>
              {TYPES.map((type) => (
                <th key={type} className="px-3 py-2 font-mono text-[9px] uppercase tracking-widest text-zinc-400 font-medium text-center">
                  {TYPE_LABELS[type]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {TIERS.map((tier) => (
              <tr key={tier}>
                <td className="py-1 pr-4">
                  <div className="flex items-center gap-2">
                    <div className={`w-3 h-[2px] ${TIER_BAR_COLORS[tier]}`}></div>
                    <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500 font-bold">
                      {TIER_LABELS[tier]}
                    </span>
                  </div>
                </td>
                {TYPES.map((type) => {
                  const key = `${tier}:${type}`;
                  const count = counts[key] || 0;
                  const style = getCellStyle(count);
                  const cellSources = sources[key] || [];
                  const isHovered = hoveredCell === key;

                  return (
                    <td key={type} className="p-1">
                      <div
                        className={`heatmap-cell border ${style.border} ${style.bg} h-16 flex items-center justify-center cursor-pointer relative`}
                        onMouseEnter={() => setHoveredCell(key)}
                        onMouseLeave={() => setHoveredCell(null)}
                        onClick={() => onCellClick?.(tier, type)}
                      >
                        <span className={`font-mono text-xl font-bold ${style.text}`}>
                          {count}
                        </span>

                        {isHovered && cellSources.length > 0 && (
                          <div className="absolute z-10 bottom-full left-1/2 -translate-x-1/2 mb-2 bg-zinc-900 text-white px-3 py-2 text-[10px] font-mono whitespace-nowrap pointer-events-none">
                            {cellSources.map((s, i) => (
                              <div key={i}>{s}</div>
                            ))}
                            {count > cellSources.length && (
                              <div className="text-zinc-400">+{count - cellSources.length} more</div>
                            )}
                          </div>
                        )}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
