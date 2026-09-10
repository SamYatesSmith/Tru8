'use client';

import { getFaviconUrl } from '../shared-utils';
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

interface EvidenceHeatmapProps {
  evidence: Evidence[];
  onCellClick?: (tier: EvidenceTier, type: EvidenceType) => void;
}

// The one-line legend under the grid — a gloss, not a definition (those live in
// TIER_DESCRIPTIONS below, in the guide). Kept short so the three items sit on
// one line at desktop width and wrap as whole units on a phone.
const TIER_SHORT: Record<EvidenceTier, string> = {
  primary: 'closest to the original',
  reporting: 'investigated coverage',
  commentary: 'analysis & opinion',
};

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

      {/* Classification guide (reworked 2026-09-10 — founder: "could be arranged in
          a more appealing and orderly manner"). What was wrong: the tier line was
          stated twice in two wordings (terse legend + the panel's fuller one);
          the legend's "·" separators dangled at line ends on a phone; tier rows
          carried a colour swatch while type rows did not, so the label columns
          never lined up; a wrapped description fell under its own label; and the
          "(rows)/(columns)" headings are wrong on a phone, where the grid is
          transposed. Now: ONE legend row whose items wrap as units with the tier
          swatch as the marker (no separators), and ONE guide rendered as an
          aligned definition grid — swatch · label · description in fixed columns,
          so wrapped descriptions hang under themselves — with axis-free headings. */}
      {/* Phone: a stacked list under the TIERS label (one item per line); sm+:
          one row. A wrapping row put the first item beside the label and the
          other two beneath — ragged. */}
      <div className="mt-4 flex flex-col sm:flex-row sm:flex-wrap sm:items-center gap-y-1.5 sm:gap-x-5 text-[11px]">
        <span className="font-mono text-[9px] font-bold uppercase tracking-widest text-zinc-400 leading-[1.125rem]">
          Tiers
        </span>
        {TIERS.map((tier) => (
          <span key={tier} className="inline-flex items-center gap-1.5 whitespace-nowrap">
            <span aria-hidden className={`w-3 h-[2px] ${TIER_BAR_COLORS[tier]} shrink-0`} />
            <span className={`font-medium ${tier === 'primary' ? 'text-[var(--tier1-accent)]' : 'text-zinc-700'}`}>
              {TIER_LABELS[tier]}
            </span>
            <span className="text-zinc-400">{TIER_SHORT[tier]}</span>
          </span>
        ))}
      </div>

      <div className="mt-3">
        <button
          type="button"
          onClick={toggleLegend}
          aria-expanded={legendOpen}
          className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:text-zinc-600 transition-colors cursor-pointer"
        >
          <span aria-hidden className={`inline-block transition-transform ${legendOpen ? 'rotate-90' : ''}`}>▸</span>
          {legendOpen ? 'Hide the classification guide' : 'What the tiers and types mean'}
        </button>

        {legendOpen && (
          <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-x-10 gap-y-5 border border-zinc-200 bg-zinc-50 px-4 py-4">
            <GuideColumn
              title="Source tiers"
              rows={TIERS.map((tier) => ({
                key: tier,
                marker: <span aria-hidden className={`block w-3 h-[2px] ${TIER_BAR_COLORS[tier]}`} />,
                label: TIER_LABELS[tier],
                description: TIER_DESCRIPTIONS[tier],
              }))}
            />
            <GuideColumn
              title="Content types"
              rows={TYPES.map((type) => ({
                key: type,
                marker: <span aria-hidden className="block w-1 h-1 bg-zinc-300 rounded-full" />,
                label: TYPE_LABELS[type],
                description: TYPE_DESCRIPTIONS[type],
              }))}
            />
          </div>
        )}
      </div>
    </div>
  );
}

/** One column of the guide: a titled definition grid with fixed marker and
 *  label columns, so every description starts on the same x and wraps under
 *  itself rather than under its label. */
function GuideColumn({
  title,
  rows,
}: {
  title: string;
  rows: { key: string; marker: React.ReactNode; label: string; description: string }[];
}) {
  return (
    <div>
      <h4 className="font-mono text-[10px] font-bold uppercase tracking-widest text-zinc-500 pb-1.5 mb-2 border-b border-zinc-200">
        {title}
      </h4>
      <dl className="grid grid-cols-[0.75rem_5.5rem_1fr] gap-x-2 gap-y-1.5 text-[11px] leading-relaxed">
        {rows.map((row) => (
          // A fragment per row keeps the <dl> valid while the grid places the parts.
          <div key={row.key} className="contents">
            <span className="flex items-center h-[1.125rem]">{row.marker}</span>
            <dt className="font-medium text-zinc-700">{row.label}</dt>
            <dd className="text-zinc-500">{row.description}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
