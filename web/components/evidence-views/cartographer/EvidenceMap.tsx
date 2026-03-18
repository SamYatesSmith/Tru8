'use client';

import { useState, useMemo, useRef, useEffect, useCallback } from 'react';
import { Evidence, EvidenceTier, ClaimElement } from '@shared/types';
import {
  forceSimulation,
  forceX,
  forceY,
  forceCollide,
  forceManyBody,
  type SimulationNodeDatum,
} from 'd3-force';

// --- Types ---

export interface ElementMapping {
  elementIndex: number;
  elementDescription: string;
  relationship: 'supports' | 'challenges' | 'context';
}

interface MapNode extends SimulationNodeDatum {
  id: string;
  evidence: Evidence;
  tier: EvidenceTier;
  radius: number;
  elementIndices: number[];
  colour: string;
  targetX: number;
}

interface BandLayout {
  yCenter: number;
  bandTop: number;
  bandBottom: number;
  count: number;
}

interface EvidenceMapProps {
  evidenceByTier: Record<EvidenceTier, Evidence[]>;
  elements: ClaimElement[];
  evidenceElementMap: Map<string, ElementMapping[]>;
  claimLabelMap?: Map<string, string>;
}

// --- Constants ---

const TIER_CONFIG: Record<EvidenceTier, { colour: string; label: string }> = {
  primary:    { colour: 'var(--tier1-accent)', label: 'Primary' },
  reporting:  { colour: '#3F3F46',             label: 'Reporting' },
  commentary: { colour: '#A1A1AA',             label: 'Commentary' },
};

const TIERS: EvidenceTier[] = ['primary', 'reporting', 'commentary'];
const MIN_HEIGHT = 340;
const MIN_BAND_HEIGHT = 80;
const PADDING = { top: 44, right: 48, bottom: 72, left: 110 };

// --- Helpers ---

function getDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return '';
  }
}

function getFaviconUrl(url: string): string {
  const domain = getDomain(url);
  return domain ? `https://www.google.com/s2/favicons?domain=${domain}&sz=64` : '';
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  } catch {
    return '';
  }
}

function computeNodeRadius(tier: EvidenceTier, totalCount: number): number {
  const BASE: Record<EvidenceTier, number> = { primary: 26, reporting: 19, commentary: 14 };
  let r = BASE[tier];
  if (totalCount <= 4) r *= 1.6;
  else if (totalCount <= 8) r *= 1.4;
  else if (totalCount > 25) r *= 0.85;
  return Math.max(12, Math.min(40, Math.round(r)));
}

function computeBandLayout(
  evidenceByTier: Record<EvidenceTier, Evidence[]>,
  innerHeight: number,
  paddingTop: number,
): Record<EvidenceTier, BandLayout | null> {
  const counts: Record<EvidenceTier, number> = {
    primary: (evidenceByTier.primary || []).length,
    reporting: (evidenceByTier.reporting || []).length,
    commentary: (evidenceByTier.commentary || []).length,
  };
  const populated = TIERS.filter((t) => counts[t] > 0);
  const total = TIERS.reduce((s, t) => s + counts[t], 0);

  const result: Record<EvidenceTier, BandLayout | null> = {
    primary: null,
    reporting: null,
    commentary: null,
  };
  if (populated.length === 0 || total === 0) return result;

  const raw = new Map<EvidenceTier, number>();
  for (const tier of populated) {
    raw.set(tier, Math.max(MIN_BAND_HEIGHT, innerHeight * (counts[tier] / total)));
  }

  const rawTotal = Array.from(raw.values()).reduce((s, h) => s + h, 0);
  const scale = innerHeight / rawTotal;

  let currentY = paddingTop;
  for (const tier of TIERS) {
    if (!raw.has(tier)) continue;
    const h = raw.get(tier)! * scale;
    result[tier] = {
      bandTop: currentY,
      bandBottom: currentY + h,
      yCenter: currentY + h / 2,
      count: counts[tier],
    };
    currentY += h;
  }

  return result;
}

/** Find the longest shared word-boundary prefix across all strings */
function findCommonPrefix(strings: string[]): string {
  if (strings.length <= 1) return '';
  let prefix = strings[0];
  for (let i = 1; i < strings.length; i++) {
    while (!strings[i].startsWith(prefix)) {
      prefix = prefix.slice(0, -1);
      if (prefix.length === 0) return '';
    }
  }
  // Trim to last word boundary so we don't cut mid-word
  const lastSpace = prefix.lastIndexOf(' ');
  return lastSpace > 0 ? prefix.slice(0, lastSpace + 1) : '';
}

/** Strip the shared prefix and show the differentiating tail */
function computeSmartExcerpt(
  description: string,
  commonPrefix: string,
  maxChars: number,
): string {
  let unique = description.slice(commonPrefix.length).trim();
  if (unique.length === 0) unique = description; // fallback if identical

  const hasPrefix = commonPrefix.length > 0 && unique !== description;
  const text = hasPrefix ? '\u2026' + unique : unique;

  if (text.length <= maxChars) return text;
  return text.slice(0, maxChars - 1).trimEnd() + '\u2026';
}

// --- Component ---

export function EvidenceMap({
  evidenceByTier,
  elements,
  evidenceElementMap,
  claimLabelMap,
}: EvidenceMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(800);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [settled, setSettled] = useState(false);
  const [hasInteracted, setHasInteracted] = useState(false);
  const [hoveredColumnIdx, setHoveredColumnIdx] = useState<number | null>(null);

  // Measure container width
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerWidth(entry.contentRect.width);
      }
    });
    ro.observe(el);
    setContainerWidth(el.clientWidth);
    return () => ro.disconnect();
  }, []);

  // ─── Build nodes, compute layout, run simulation ───
  const { nodes, height, bandLayout, elementXPositions, columnCounts, maxColumnCount } =
    useMemo(() => {
      const totalCount = TIERS.reduce(
        (s, t) => s + (evidenceByTier[t] || []).length,
        0,
      );

      if (totalCount === 0) {
        return {
          nodes: [] as MapNode[],
          height: MIN_HEIGHT,
          bandLayout: { primary: null, reporting: null, commentary: null } as Record<
            EvidenceTier,
            BandLayout | null
          >,
          elementXPositions: [] as number[],
          columnCounts: [] as number[],
          maxColumnCount: 0,
        };
      }

      const innerWidth = containerWidth - PADDING.left - PADDING.right;
      const baseInnerHeight = Math.max(
        MIN_HEIGHT - PADDING.top - PADDING.bottom,
        Math.min(totalCount * 16, 560),
      );
      const height = baseInnerHeight + PADDING.top + PADDING.bottom;

      const bandLayout = computeBandLayout(evidenceByTier, baseInnerHeight, PADDING.top);
      const populated = TIERS.filter((t) => bandLayout[t] !== null);

      const elementCount = Math.max(elements.length, 1);
      const elementXPositions = elements.map((_, i) =>
        PADDING.left + (innerWidth * (i + 0.5)) / elementCount,
      );
      const centerX = PADDING.left + innerWidth / 2;

      const allNodes: MapNode[] = [];
      for (const tier of TIERS) {
        const items = evidenceByTier[tier] || [];
        const config = TIER_CONFIG[tier];
        const band = bandLayout[tier];
        if (!band) continue;

        for (const ev of items) {
          const evId = ev.evidenceId || ev.id;
          const mappings = evidenceElementMap.get(evId) || [];
          const elIndices = mappings.map((m) => m.elementIndex);

          let targetX = centerX;
          if (elIndices.length > 0 && elementXPositions.length > 0) {
            targetX =
              elIndices.reduce(
                (sum, idx) => sum + (elementXPositions[idx] ?? centerX),
                0,
              ) / elIndices.length;
          }

          allNodes.push({
            id: evId,
            evidence: ev,
            tier,
            radius: computeNodeRadius(tier, totalCount),
            elementIndices: elIndices,
            colour: config.colour,
            targetX,
            x: targetX + (Math.random() - 0.5) * 50,
            y: band.yCenter + (Math.random() - 0.5) * 30,
          });
        }
      }

      const forceYStrength = populated.length === 1 ? 0.3 : 0.7;

      const sim = forceSimulation<MapNode>(allNodes)
        .force('x', forceX<MapNode>((d) => d.targetX).strength(0.65))
        .force(
          'y',
          forceY<MapNode>((d) => bandLayout[d.tier]!.yCenter).strength(forceYStrength),
        )
        .force(
          'collide',
          forceCollide<MapNode>((d) => d.radius + 6).strength(0.85),
        )
        .force('charge', forceManyBody().strength(-8))
        .stop();

      for (let i = 0; i < 300; i++) sim.tick();

      for (const node of allNodes) {
        const band = bandLayout[node.tier]!;
        node.x = Math.max(
          PADDING.left + node.radius,
          Math.min(containerWidth - PADDING.right - node.radius, node.x!),
        );
        node.y = Math.max(
          band.bandTop + node.radius,
          Math.min(band.bandBottom - node.radius, node.y!),
        );
      }

      const columnCounts = elements.map((_, i) =>
        allNodes.filter((n) => n.elementIndices.includes(i)).length,
      );
      const maxColumnCount = Math.max(...columnCounts, 1);

      return {
        nodes: allNodes,
        height,
        bandLayout,
        elementXPositions,
        columnCounts,
        maxColumnCount,
      };
    }, [evidenceByTier, elements, evidenceElementMap, containerWidth]);

  // CSS settle animation
  useEffect(() => {
    setSettled(false);
    const t = requestAnimationFrame(() => {
      requestAnimationFrame(() => setSettled(true));
    });
    return () => cancelAnimationFrame(t);
  }, [nodes]);

  const handleNodeClick = useCallback((id: string) => {
    setSelectedId((prev) => (prev === id ? null : id));
    setHasInteracted(true);
  }, []);

  const handleBackgroundClick = useCallback(() => {
    setSelectedId(null);
  }, []);

  const handleNodeHover = useCallback((id: string | null) => {
    setHoveredId(id);
    if (id) setHasInteracted(true);
  }, []);

  // ─── Derived render data ───

  const selectedNode = selectedId ? nodes.find((n) => n.id === selectedId) : null;
  const selectedMappings = selectedId
    ? evidenceElementMap.get(selectedId) || []
    : [];
  const hoveredNode =
    hoveredId && !selectedId ? nodes.find((n) => n.id === hoveredId) : null;

  const innerHeight = height - PADDING.top - PADDING.bottom;
  const innerWidth = containerWidth - PADDING.left - PADDING.right;
  const elementCount = Math.max(elements.length, 1);
  const columnWidth = innerWidth / elementCount;

  const populatedBands = TIERS.filter((t) => bandLayout[t] !== null).map(
    (tier, idx) => ({
      tier,
      ...bandLayout[tier]!,
      config: TIER_CONFIG[tier],
      isEven: idx % 2 === 0,
    }),
  );

  // Smart element labels — strip common prefix, show differentiating tail
  const descriptions = elements.map((el) => el.description);
  const commonPrefix = findCommonPrefix(descriptions);
  const maxLabelChars = Math.max(10, Math.floor(columnWidth / 5.5));

  const elementColumns = elements.map((el, i) => ({
    index: i,
    code: String(i + 1).padStart(2, '0'),
    description: el.description,
    excerpt: computeSmartExcerpt(el.description, commonPrefix, maxLabelChars),
    x: PADDING.left + (innerWidth * (i + 0.5)) / elementCount,
    count: columnCounts[i] || 0,
  }));

  // Hovered column data for tooltip
  const hoveredColumn =
    hoveredColumnIdx !== null ? elementColumns[hoveredColumnIdx] : null;

  // ─── Empty state ───

  if (nodes.length === 0) {
    return (
      <div className="border border-dashed border-zinc-200 bg-zinc-50/30 p-12 text-center">
        <p className="font-mono text-xs uppercase tracking-widest text-zinc-400">
          No evidence to map
        </p>
      </div>
    );
  }

  // ─── Render ───

  return (
    <div
      ref={containerRef}
      className="relative w-full"
      style={{ minHeight: height }}
    >
      <svg
        width={containerWidth}
        height={height}
        className="absolute inset-0"
        onClick={handleBackgroundClick}
      >
        {/* ── Band backgrounds (alternating tint) ── */}
        {populatedBands.map(({ tier, bandTop, bandBottom, isEven }) => (
          <rect
            key={`band-bg-${tier}`}
            x={PADDING.left}
            y={bandTop}
            width={containerWidth - PADDING.left - PADDING.right}
            height={bandBottom - bandTop}
            fill={isEven ? '#FAFAFA' : 'white'}
          />
        ))}

        {/* ── Column density background tint ── */}
        {elementColumns.map(({ code, x, count }) => {
          if (count === 0) return null;
          const opacity = 0.02 + (count / maxColumnCount) * 0.04;
          const halfWidth = columnWidth / 2;
          const firstBand = populatedBands[0];
          const lastBand = populatedBands[populatedBands.length - 1];
          if (!firstBand || !lastBand) return null;
          return (
            <rect
              key={`col-tint-${code}`}
              x={x - halfWidth}
              y={firstBand.bandTop}
              width={columnWidth}
              height={lastBand.bandBottom - firstBand.bandTop}
              fill="#000000"
              opacity={opacity}
            />
          );
        })}

        {/* ── Tier watermark labels ── */}
        {populatedBands.map(({ tier, yCenter, bandTop, bandBottom, config }) => (
          <text
            key={`wm-${tier}`}
            x={PADDING.left + innerWidth / 2}
            y={yCenter}
            textAnchor="middle"
            dominantBaseline="central"
            fill="#F4F4F5"
            fontSize={Math.min(28, (bandBottom - bandTop) * 0.35)}
            fontFamily="var(--font-mono, monospace)"
            fontWeight={700}
            letterSpacing="0.25em"
            style={{ textTransform: 'uppercase', pointerEvents: 'none' }}
          >
            {config.label}
          </text>
        ))}

        {/* ── Band boundary lines ── */}
        {populatedBands.map(({ tier, bandTop, bandBottom }, idx) => (
          <g key={`boundary-${tier}`}>
            {idx === 0 && (
              <line
                x1={PADDING.left}
                x2={containerWidth - PADDING.right}
                y1={bandTop}
                y2={bandTop}
                stroke="#E5E7EB"
                strokeWidth={1}
                opacity={0.6}
              />
            )}
            <line
              x1={PADDING.left}
              x2={containerWidth - PADDING.right}
              y1={bandBottom}
              y2={bandBottom}
              stroke="#E5E7EB"
              strokeWidth={1}
              opacity={0.6}
            />
          </g>
        ))}

        {/* ── Element column guides ── */}
        {elementColumns.map(({ code, x }) => (
          <line
            key={`col-${code}`}
            x1={x}
            x2={x}
            y1={PADDING.top}
            y2={height - PADDING.bottom}
            stroke="#D1D5DB"
            strokeWidth={1}
            strokeDasharray="3 6"
            opacity={0.5}
          />
        ))}

        {/* ── Column density bars (wider, more visible) ── */}
        {elementColumns.map(({ code, x, count }) => {
          const barHeight =
            maxColumnCount > 0
              ? Math.min((count / maxColumnCount) * 18, 18)
              : 0;
          return (
            <g key={`density-${code}`}>
              {count > 0 ? (
                <rect
                  x={x - 6}
                  y={PADDING.top - 10 - barHeight}
                  width={12}
                  height={barHeight}
                  fill="#D1D5DB"
                  rx={2}
                />
              ) : (
                <rect
                  x={x - 6}
                  y={PADDING.top - 14}
                  width={12}
                  height={4}
                  fill="none"
                  stroke="#E5E7EB"
                  strokeWidth={0.5}
                  strokeDasharray="2 2"
                />
              )}
            </g>
          );
        })}

        {/* ── Drop-lines for drifted nodes ── */}
        {settled &&
          nodes.map((node) => {
            if (node.elementIndices.length === 0) return null;
            return node.elementIndices.map((elIdx) => {
              const targetX = elementXPositions[elIdx];
              if (targetX === undefined) return null;
              const dx = Math.abs(node.x! - targetX);
              if (dx < node.radius + 8) return null;
              return (
                <line
                  key={`drop-${node.id}-${elIdx}`}
                  x1={node.x!}
                  y1={node.y! + node.radius}
                  x2={targetX}
                  y2={height - PADDING.bottom}
                  stroke="#E5E7EB"
                  strokeWidth={0.5}
                  strokeDasharray="2 3"
                  opacity={0.3}
                  style={{
                    transition:
                      'all 0.7s cubic-bezier(0.34, 1.56, 0.64, 1)',
                  }}
                />
              );
            });
          })}

        {/* Clip paths for circular favicon masks */}
        <defs>
          {nodes.map((node) => (
            <clipPath key={`clip-${node.id}`} id={`clip-${node.id}`}>
              <circle cx={0} cy={0} r={node.radius - 3} />
            </clipPath>
          ))}
        </defs>

        {/* ── Evidence nodes ── */}
        {nodes.map((node) => {
          const isHovered = hoveredId === node.id;
          const isSelected = selectedId === node.id;
          const isDimmed =
            !!(hoveredId || selectedId) && !isHovered && !isSelected;
          const cx = settled ? node.x! : PADDING.left + innerWidth / 2;
          const cy = settled ? node.y! : PADDING.top + innerHeight / 2;

          return (
            <g
              key={node.id}
              style={{
                transform: `translate(${cx}px, ${cy}px)`,
                transition: settled
                  ? 'transform 0.7s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.2s ease'
                  : 'none',
                opacity: isDimmed ? 0.2 : 1,
                cursor: 'pointer',
              }}
              onMouseEnter={() => handleNodeHover(node.id)}
              onMouseLeave={() => handleNodeHover(null)}
              onClick={(e) => {
                e.stopPropagation();
                handleNodeClick(node.id);
              }}
            >
              {(isHovered || isSelected) && (
                <circle
                  cx={0}
                  cy={0}
                  r={node.radius + 5}
                  fill="none"
                  stroke={node.colour}
                  strokeWidth={1}
                  opacity={0.25}
                />
              )}

              <circle
                cx={0}
                cy={0}
                r={node.radius}
                fill="white"
                stroke={node.colour}
                strokeWidth={isHovered || isSelected ? 3 : 2}
              />

              {/* Fallback initial (behind favicon) */}
              <text
                x={0}
                y={1}
                textAnchor="middle"
                dominantBaseline="central"
                fill="#D4D4D8"
                fontSize={node.radius * 0.65}
                fontFamily="var(--font-mono, monospace)"
                fontWeight={600}
                pointerEvents="none"
                style={{ userSelect: 'none' }}
              >
                {(node.evidence.source || '?')[0].toUpperCase()}
              </text>

              <image
                href={getFaviconUrl(node.evidence.url)}
                x={-(node.radius - 3)}
                y={-(node.radius - 3)}
                width={(node.radius - 3) * 2}
                height={(node.radius - 3) * 2}
                clipPath={`url(#clip-${node.id})`}
                preserveAspectRatio="xMidYMid slice"
              />
            </g>
          );
        })}

        {/* ── Y-axis title (rotated) — neutral, no quality judgment ── */}
        <text
          x={0}
          y={0}
          textAnchor="middle"
          fill="#D4D4D8"
          fontSize={9}
          fontFamily="var(--font-mono, monospace)"
          fontWeight={600}
          letterSpacing="0.15em"
          style={{ textTransform: 'uppercase' }}
          transform={`translate(16, ${PADDING.top + innerHeight / 2}) rotate(-90)`}
        >
          Source Type
        </text>

        {/* Y-axis tier labels */}
        {populatedBands.map(({ tier, yCenter, config }) => (
          <text
            key={`lbl-${tier}`}
            x={PADDING.left - 16}
            y={yCenter}
            textAnchor="end"
            dominantBaseline="central"
            fill={config.colour}
            fontSize={10}
            fontFamily="var(--font-mono, monospace)"
            fontWeight={600}
            letterSpacing="0.08em"
          >
            {config.label}
          </text>
        ))}

        {/* ── Band count badges (right edge) ── */}
        {populatedBands.map(({ tier, yCenter, count, config }) => (
          <text
            key={`count-${tier}`}
            x={containerWidth - PADDING.right + 10}
            y={yCenter}
            textAnchor="start"
            dominantBaseline="central"
            fill={config.colour}
            fontSize={11}
            fontFamily="var(--font-mono, monospace)"
            fontWeight={700}
          >
            {count}
          </text>
        ))}

        {/* ── X-axis element labels (number + smart excerpt + hover hit area) ── */}
        {elementColumns.map(({ index, code, excerpt, x }) => (
          <g
            key={`el-label-${code}`}
            onMouseEnter={() => setHoveredColumnIdx(index)}
            onMouseLeave={() => setHoveredColumnIdx(null)}
            style={{ cursor: 'default' }}
          >
            {/* Invisible hit area for hover */}
            <rect
              x={x - columnWidth / 2}
              y={height - PADDING.bottom + 4}
              width={columnWidth}
              height={PADDING.bottom - 8}
              fill="transparent"
            />
            {/* Element number — prominent */}
            <text
              x={x}
              y={height - PADDING.bottom + 18}
              textAnchor="middle"
              fill="#71717A"
              fontSize={11}
              fontFamily="var(--font-mono, monospace)"
              fontWeight={700}
              letterSpacing="0.08em"
            >
              {code}
            </text>
            {/* Smart excerpt — differentiating tail */}
            <text
              x={x}
              y={height - PADDING.bottom + 32}
              textAnchor="middle"
              fill="#A1A1AA"
              fontSize={8}
              fontFamily="var(--font-mono, monospace)"
            >
              {excerpt}
            </text>
          </g>
        ))}
      </svg>

      {/* ── Column hover tooltip (full element description) ── */}
      {hoveredColumn && (
        <div
          className="absolute pointer-events-none z-10 bg-white border border-zinc-200 px-3 py-2 max-w-[320px]"
          style={{
            left: Math.min(
              Math.max(hoveredColumn.x - 160, 8),
              containerWidth - 336,
            ),
            top: height - PADDING.bottom + 40,
          }}
        >
          <div className="font-mono text-[9px] uppercase tracking-widest text-zinc-400 mb-0.5">
            Element {hoveredColumn.code}
          </div>
          <div className="text-[11px] text-zinc-700 leading-snug">
            {hoveredColumn.description}
          </div>
          <div className="text-[10px] text-zinc-400 mt-1 font-mono">
            {hoveredColumn.count} {hoveredColumn.count === 1 ? 'source' : 'sources'}
          </div>
        </div>
      )}

      {/* ── Interaction hint (fades after first interaction) ── */}
      {!hasInteracted && nodes.length > 0 && (
        <div
          className="absolute left-0 right-0 text-center pointer-events-none"
          style={{ top: height - PADDING.bottom + 48 }}
        >
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-300">
            Hover or tap any source to explore
          </span>
        </div>
      )}

      {/* ── Hover tooltip ── */}
      {hoveredNode && (
        <div
          className="absolute pointer-events-none z-10 bg-white border border-zinc-200 px-3 py-2 max-w-[260px]"
          style={{
            left: Math.min(
              hoveredNode.x! + hoveredNode.radius + 12,
              containerWidth - 280,
            ),
            top: hoveredNode.y! - 10,
          }}
        >
          <div
            className="font-mono text-[9px] uppercase tracking-widest mb-0.5"
            style={{ color: hoveredNode.colour }}
          >
            {hoveredNode.evidence.source}
          </div>
          <div className="text-[11px] text-zinc-800 font-medium line-clamp-2 leading-tight">
            {hoveredNode.evidence.title}
          </div>
          {hoveredNode.evidence.publishedDate && (
            <div className="text-[10px] text-zinc-400 mt-1 font-mono">
              {formatDate(hoveredNode.evidence.publishedDate)}
            </div>
          )}
          {claimLabelMap?.get(hoveredNode.id) && (
            <div className="text-[9px] text-zinc-400 mt-1 font-mono uppercase tracking-wider">
              {claimLabelMap.get(hoveredNode.id)}
            </div>
          )}
        </div>
      )}

      {/* ── Selected detail card ── */}
      {selectedNode && (
        <div
          className="absolute z-20 bg-white border border-zinc-300 p-4 max-w-[300px]"
          style={{
            left: Math.min(
              Math.max(selectedNode.x! + selectedNode.radius + 16, 16),
              containerWidth - 320,
            ),
            top: Math.max(selectedNode.y! - 24, PADDING.top),
          }}
        >
          <button
            onClick={() => setSelectedId(null)}
            className="absolute top-2 right-3 text-zinc-300 hover:text-zinc-600 text-base leading-none"
            aria-label="Close detail"
          >
            &times;
          </button>

          <div
            className="font-mono text-[9px] uppercase tracking-widest mb-1.5"
            style={{ color: selectedNode.colour }}
          >
            {selectedNode.evidence.source}
          </div>
          <div className="text-sm text-zinc-900 font-medium leading-snug mb-2 pr-4">
            {selectedNode.evidence.title}
          </div>
          {selectedNode.evidence.publishedDate && (
            <div className="text-[10px] text-zinc-400 font-mono mb-3">
              {formatDate(selectedNode.evidence.publishedDate)}
            </div>
          )}

          {selectedMappings.length > 0 && (
            <div className="border-t border-zinc-100 pt-2 mb-3">
              <div className="font-mono text-[9px] uppercase tracking-widest text-zinc-400 mb-1.5">
                Addresses
              </div>
              {selectedMappings.map((m) => (
                <div
                  key={m.elementIndex}
                  className="text-[11px] text-zinc-600 mb-0.5"
                >
                  Element {String(m.elementIndex + 1).padStart(2, '0')}
                  <span className="text-zinc-400"> &mdash; </span>
                  <span className="text-zinc-400 line-clamp-1">
                    {m.elementDescription}
                  </span>
                </div>
              ))}
            </div>
          )}

          {claimLabelMap?.get(selectedNode.id) && (
            <div className="text-[9px] text-zinc-400 font-mono uppercase tracking-wider mb-3">
              {claimLabelMap.get(selectedNode.id)}
            </div>
          )}

          <div className="flex items-center gap-3">
            <a
              href={selectedNode.evidence.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest text-zinc-500 hover:text-zinc-900 transition-colors"
            >
              Visit source <span className="text-xs">&rarr;</span>
            </a>
            {selectedNode.evidence.archivedUrl && (
              <a
                href={selectedNode.evidence.archivedUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-widest text-zinc-300 hover:text-zinc-600 transition-colors"
              >
                Archive
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
