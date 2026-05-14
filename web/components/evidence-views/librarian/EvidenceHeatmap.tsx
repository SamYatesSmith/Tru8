'use client';

import { useMemo, useState, useCallback } from 'react';
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
  if (count === 0) return { bg: 'bg-white', border: 'border-dashed border-zinc-200', text: 'text-zinc-200' };
  if (count <= 2) return { bg: 'bg-zinc-50', border: 'border-zinc-100', text: 'text-zinc-500' };
  if (count <= 5) return { bg: 'bg-zinc-100', border: 'border-zinc-200', text: 'text-zinc-600' };
  return { bg: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-700' };
}

function getDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
}

function getFaviconUrl(url: string): string {
  try {
    const hostname = new URL(url).hostname;
    return `https://www.google.com/s2/favicons?domain=${hostname}&sz=32`;
  } catch {
    return '';
  }
}

interface EvidenceHeatmapProps {
  evidence: Evidence[];
  onCellClick?: (tier: EvidenceTier, type: EvidenceType) => void;
}

const TIER_DESCRIPTIONS: Record<EvidenceTier, string> = {
  primary: 'Original data, official records, direct observation, raw statistics',
  reporting: 'News coverage, investigative journalism, factual reporting',
  commentary: 'Opinion, editorials, analysis pieces, blog posts',
};

const TYPE_DESCRIPTIONS: Record<EvidenceType, string> = {
  data: 'Raw datasets, statistics, measurements',
  official_statement: 'Government publications, press releases, regulatory filings',
  news_reporting: 'News articles, wire reports, investigative pieces',
  analysis: 'Research reports, policy analysis, expert commentary',
  opinion: 'Editorials, op-eds, blog posts, social media',
  academic: 'Peer-reviewed papers, preprints, institutional research',
};

function FaviconCircle({ url }: { url: string }) {
  const faviconUrl = getFaviconUrl(url);
  const domain = getDomain(url);
  const letter = domain.charAt(0).toUpperCase();

  return (
    <div className="w-4 h-4 rounded-full border border-zinc-200 bg-white flex items-center justify-center overflow-hidden relative shrink-0">
      <span className="font-mono text-[7px] font-bold text-zinc-300">{letter}</span>
      {faviconUrl && (
        <img
          src={faviconUrl}
          alt=""
          className="w-4 h-4 rounded-full absolute inset-0"
          onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
        />
      )}
    </div>
  );
}

export function EvidenceHeatmap({ evidence, onCellClick }: EvidenceHeatmapProps) {
  const [hoveredCell, setHoveredCell] = useState<string | null>(null);
  const [legendOpen, setLegendOpen] = useState(false);
  const toggleLegend = useCallback(() => setLegendOpen(prev => !prev), []);

  const { counts, sources, urls } = useMemo(() => {
    const counts: Record<string, number> = {};
    const sources: Record<string, string[]> = {};
    const urls: Record<string, string[]> = {};

    for (const ev of evidence) {
      const tier = ev.tier || 'commentary';
      const type = ev.evidenceType || 'news_reporting';
      const key = `${tier}:${type}`;
      counts[key] = (counts[key] || 0) + 1;
      if (!sources[key]) sources[key] = [];
      if (ev.source && sources[key].length < 5) {
        sources[key].push(ev.source);
      }
      if (!urls[key]) urls[key] = [];
      if (ev.url && urls[key].length < 4) {
        // Dedupe by domain
        const domain = getDomain(ev.url);
        const existingDomains = urls[key].map(getDomain);
        if (!existingDomains.includes(domain)) {
          urls[key].push(ev.url);
        }
      }
    }

    return { counts, sources, urls };
  }, [evidence]);

  return (
    <div className="mb-10">
      <div className="font-mono text-sm font-bold uppercase tracking-[0.3em] text-zinc-600 mb-6 border-b border-zinc-200 pb-2">
        At a Glance
      </div>

      {/* Desktop: Tiers as rows, Types as columns (3×6) */}
      <div className="hidden lg:block overflow-x-auto">
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
                  const cellUrls = urls[key] || [];
                  const isHovered = hoveredCell === key;

                  return (
                    <td key={type} className="p-1">
                      <div
                        role="button"
                        tabIndex={0}
                        className={`heatmap-cell border ${style.border} ${style.bg} h-16 flex items-center justify-center cursor-pointer relative`}
                        onMouseEnter={() => setHoveredCell(key)}
                        onMouseLeave={() => setHoveredCell(null)}
                        onClick={() => onCellClick?.(tier, type)}
                        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onCellClick?.(tier, type); } }}
                      >
                        {count === 0 ? (
                          <span className="font-mono text-sm text-zinc-200">&mdash;</span>
                        ) : (
                          <div className="flex flex-col items-center gap-1">
                            <div className="flex items-center gap-0.5">
                              {cellUrls.slice(0, count <= 3 ? count : 3).map((url, i) => (
                                <FaviconCircle key={i} url={url} />
                              ))}
                              {count > 3 && cellUrls.length >= 3 && (
                                <span className="font-mono text-[9px] text-zinc-400 ml-0.5">+{count - 3}</span>
                              )}
                            </div>
                            <span className={`font-mono text-[10px] ${style.text}`}>{count}</span>
                          </div>
                        )}

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

      {/* Mobile: Axis flipped — Types as rows, Tiers as columns (6×3) */}
      <div className="lg:hidden">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th></th>
              {TIERS.map((tier) => (
                <th key={tier} className="px-1 py-2 text-center">
                  <div className="flex flex-col items-center gap-1">
                    <div className={`w-3 h-[2px] ${TIER_BAR_COLORS[tier]}`}></div>
                    <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-500 font-bold">
                      {TIER_LABELS[tier]}
                    </span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {TYPES.map((type) => (
              <tr key={type}>
                <td className="py-1 pr-2">
                  <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400 font-medium">
                    {TYPE_LABELS[type]}
                  </span>
                </td>
                {TIERS.map((tier) => {
                  const key = `${tier}:${type}`;
                  const count = counts[key] || 0;
                  const style = getCellStyle(count);
                  const cellUrls = urls[key] || [];

                  return (
                    <td key={tier} className="p-1">
                      <div
                        role="button"
                        tabIndex={0}
                        className={`heatmap-cell border ${style.border} ${style.bg} h-14 flex items-center justify-center cursor-pointer relative`}
                        onClick={() => onCellClick?.(tier, type)}
                        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onCellClick?.(tier, type); } }}
                      >
                        {count === 0 ? (
                          <span className="font-mono text-sm text-zinc-200">&mdash;</span>
                        ) : (
                          <div className="flex flex-col items-center gap-0.5">
                            <div className="flex items-center gap-0.5">
                              {cellUrls.slice(0, Math.min(count, 2)).map((url, i) => (
                                <FaviconCircle key={i} url={url} />
                              ))}
                              {count > 2 && cellUrls.length >= 2 && (
                                <span className="font-mono text-[8px] text-zinc-400">+{count - 2}</span>
                              )}
                            </div>
                            <span className={`font-mono text-[10px] ${style.text}`}>{count}</span>
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

      {/* Always-visible tier legend — the most load-bearing part of the classification guide */}
      <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[11px] text-zinc-500">
        <span className="font-mono text-[9px] font-bold uppercase tracking-widest text-zinc-400">
          Tiers
        </span>
        <span>
          <span className="text-[#EA580C] font-medium">Primary</span>
          <span className="text-zinc-400"> — closest to original info</span>
        </span>
        <span className="text-zinc-200">·</span>
        <span>
          <span className="text-zinc-700 font-medium">Reporting</span>
          <span className="text-zinc-400"> — investigated coverage</span>
        </span>
        <span className="text-zinc-200">·</span>
        <span>
          <span className="text-zinc-500 font-medium">Commentary</span>
          <span className="text-zinc-400"> — analysis & opinion</span>
        </span>
      </div>

      {/* Expandable full guide — type descriptions live here */}
      <div className="mt-2">
        <button
          onClick={toggleLegend}
          className="font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:text-zinc-600 transition-colors"
        >
          {legendOpen ? '− Hide' : '+ Show'} content type descriptions
        </button>

        {legendOpen && (
          <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-6 border border-zinc-200 bg-zinc-50 p-4">
            <div>
              <h4 className="font-mono text-[10px] font-bold uppercase tracking-widest text-zinc-500 mb-2">
                Source Tiers (rows)
              </h4>
              {TIERS.map((tier) => (
                <div key={tier} className="flex items-start gap-2 mb-1.5">
                  <div className={`w-3 h-[2px] ${TIER_BAR_COLORS[tier]} mt-1.5 shrink-0`} />
                  <div>
                    <span className="text-[11px] font-medium text-zinc-700">{TIER_LABELS[tier]}</span>
                    <span className="text-[11px] text-zinc-400"> — {TIER_DESCRIPTIONS[tier]}</span>
                  </div>
                </div>
              ))}
            </div>
            <div>
              <h4 className="font-mono text-[10px] font-bold uppercase tracking-widest text-zinc-500 mb-2">
                Content Types (columns)
              </h4>
              {TYPES.map((type) => (
                <div key={type} className="flex items-start gap-2 mb-1.5">
                  <span className="text-[11px] font-medium text-zinc-700">{TYPE_LABELS[type]}</span>
                  <span className="text-[11px] text-zinc-400"> — {TYPE_DESCRIPTIONS[type]}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
