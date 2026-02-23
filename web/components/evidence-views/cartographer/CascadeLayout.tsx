'use client';

import { useRef, useState, useEffect, useMemo } from 'react';
import dagre from 'dagre';
import { Evidence, EvidenceTier } from '@shared/types';
import { CascadeNode } from './CascadeNode';
import { ConnectionLines } from './ConnectionLines';

const TIER_ORDER: EvidenceTier[] = ['primary', 'reporting', 'commentary'];
const TIER_LABELS: Record<EvidenceTier, string> = {
  primary: 'Tier 1 — Primary',
  reporting: 'Tier 2 — Reporting',
  commentary: 'Tier 3 — Commentary',
};
const TIER_BAR_COLORS: Record<EvidenceTier, string> = {
  primary: 'bg-[var(--tier1-accent)]',
  reporting: 'bg-zinc-600',
  commentary: 'bg-zinc-400',
};
const NODE_SIZES: Record<EvidenceTier, { width: number; height: number }> = {
  primary: { width: 240, height: 80 },
  reporting: { width: 200, height: 64 },
  commentary: { width: 190, height: 56 },
};
const TIER_RANK: Record<EvidenceTier, number> = { primary: 0, reporting: 1, commentary: 2 };

interface CascadeLayoutProps {
  evidenceByTier: Record<EvidenceTier, Evidence[]>;
  edges: Array<{ fromId: string; toId: string }>;
  divergentIds: Set<string>;
  claimLabelMap?: Map<string, string>;
  diagnosticValues?: Map<string, number>;
  diagnosticActive?: boolean;
  onNodeClick?: (evidence: Evidence) => void;
}

export function CascadeLayout({ evidenceByTier, edges, divergentIds, claimLabelMap, diagnosticValues, diagnosticActive, onNodeClick }: CascadeLayoutProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(0);

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerWidth(entry.contentRect.width);
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Use dagre to compute optimal node ordering within each tier
  const orderedTiers = useMemo(() => {
    if (containerWidth === 0) return null;

    const g = new dagre.graphlib.Graph();
    g.setGraph({ rankdir: 'TB', ranksep: 80, nodesep: 20, marginx: 0, marginy: 0 });
    g.setDefaultEdgeLabel(() => ({}));

    // Add all nodes
    const allEvidence = new Map<string, Evidence>();
    for (const tier of TIER_ORDER) {
      for (const ev of evidenceByTier[tier] || []) {
        const evId = ev.evidenceId || ev.id;
        const size = NODE_SIZES[tier];
        g.setNode(evId, { width: size.width, height: size.height, rank: TIER_RANK[tier] });
        allEvidence.set(evId, ev);
      }
    }

    // Add edges
    for (const edge of edges) {
      if (g.hasNode(edge.fromId) && g.hasNode(edge.toId)) {
        g.setEdge(edge.fromId, edge.toId);
      }
    }

    // Run dagre layout
    try {
      dagre.layout(g);
    } catch {
      // Dagre can fail on degenerate graphs — fall back to insertion order
    }

    // Extract ordered evidence per tier, sorted by dagre x-position
    const ordered: Record<EvidenceTier, Evidence[]> = { primary: [], reporting: [], commentary: [] };
    for (const tier of TIER_ORDER) {
      const items = (evidenceByTier[tier] || []).map((ev) => {
        const evId = ev.evidenceId || ev.id;
        const node = g.node(evId);
        return { ev, x: node?.x ?? 0 };
      });
      items.sort((a, b) => a.x - b.x);
      ordered[tier] = items.map((i) => i.ev);
    }

    // Build node positions for connection lines
    const nodePositions = new Map<string, { x: number; y: number; width: number; height: number }>();
    for (const nodeId of g.nodes()) {
      const node = g.node(nodeId);
      if (node) {
        nodePositions.set(nodeId, {
          x: node.x - node.width / 2,
          y: node.y - node.height / 2,
          width: node.width,
          height: node.height,
        });
      }
    }

    const graphHeight = g.graph().height || 500;

    return { ordered, nodePositions, graphHeight };
  }, [evidenceByTier, edges, containerWidth]);

  // Before dagre computes (no container width yet), show tiers in default order
  const displayTiers = orderedTiers?.ordered || evidenceByTier;

  return (
    <div ref={containerRef} className="mb-16 relative">
      <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-zinc-400 mb-8 border-b border-zinc-100 pb-2">
        Citation Cascade
      </div>

      {TIER_ORDER.map((tier) => {
        const items = displayTiers[tier] || [];
        if (items.length === 0) return null;

        return (
          <div key={tier} className="mb-6">
            <div className="font-mono text-[9px] uppercase tracking-widest text-zinc-400 mb-4 flex items-center gap-2">
              <div className={`w-3 h-[2px] ${TIER_BAR_COLORS[tier]}`} />
              {TIER_LABELS[tier]}
            </div>
            <div className="flex flex-wrap gap-3 justify-center">
              {items.map((ev) => {
                const evId = ev.evidenceId || ev.id;
                const hasDownstreamConnection = tier !== 'commentary' && edges.some((e) => e.fromId === evId);

                return (
                  <CascadeNode
                    key={ev.id}
                    evidence={ev}
                    isDivergent={divergentIds.has(evId)}
                    showConnectionStub={hasDownstreamConnection}
                    claimLabel={claimLabelMap?.get(evId)}
                    diagnosticValue={diagnosticValues?.get(evId)}
                    diagnosticActive={diagnosticActive}
                    onClick={() => onNodeClick?.(ev)}
                  />
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
