'use client';

import { Evidence, EvidenceTier } from '@shared/types';
import { CascadeNode } from './CascadeNode';

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

interface MobileCascadeProps {
  evidenceByTier: Record<EvidenceTier, Evidence[]>;
  divergentIds: Set<string>;
  claimLabelMap?: Map<string, string>;
  diagnosticValues?: Map<string, number>;
  diagnosticActive?: boolean;
  onNodeClick?: (evidence: Evidence) => void;
}

export function MobileCascade({ evidenceByTier, divergentIds, claimLabelMap, diagnosticValues, diagnosticActive, onNodeClick }: MobileCascadeProps) {
  return (
    <div className="space-y-8">
      {TIER_ORDER.map((tier) => {
        const items = evidenceByTier[tier] || [];
        if (items.length === 0) return null;

        return (
          <div key={tier}>
            <div className="font-mono text-[9px] uppercase tracking-widest text-zinc-400 mb-4 flex items-center gap-2">
              <div className={`w-3 h-[2px] ${TIER_BAR_COLORS[tier]}`} />
              {TIER_LABELS[tier]}
            </div>
            <div className="space-y-3 pl-4 border-l border-zinc-100">
              {items.map((ev) => {
                const evId = ev.evidenceId || ev.id;
                return (
                  <CascadeNode
                    key={ev.id}
                    evidence={ev}
                    isDivergent={divergentIds.has(evId)}
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
