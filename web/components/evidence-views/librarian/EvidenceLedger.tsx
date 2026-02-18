'use client';

import { Evidence } from '@shared/types';
import { LedgerCard } from './LedgerCard';
import { SortControl, SortField } from './SortControl';

const TIER_ORDER: Record<string, number> = { primary: 0, reporting: 1, commentary: 2 };

function sortEvidence(items: Evidence[], field: SortField, elementMap: Map<string, string[]>): Evidence[] {
  const sorted = [...items];

  sorted.sort((a, b) => {
    switch (field) {
      case 'date': {
        const da = a.publishedDate ? new Date(a.publishedDate).getTime() : 0;
        const db = b.publishedDate ? new Date(b.publishedDate).getTime() : 0;
        return db - da;
      }
      case 'source':
        return (a.source || '').localeCompare(b.source || '');
      case 'tier':
        return (TIER_ORDER[a.tier || 'commentary'] ?? 2) - (TIER_ORDER[b.tier || 'commentary'] ?? 2);
      case 'element': {
        const aEls = elementMap.get(a.evidenceId || a.id) || [];
        const bEls = elementMap.get(b.evidenceId || b.id) || [];
        const aFirst = aEls[0] || 'z';
        const bFirst = bEls[0] || 'z';
        return aFirst.localeCompare(bFirst);
      }
      default:
        return 0;
    }
  });

  return sorted;
}

interface EvidenceLedgerProps {
  evidence: Evidence[];
  totalCount: number;
  sortField: SortField;
  onSortChange: (field: SortField) => void;
  elementMap: Map<string, string[]>;
  claimLabelMap?: Map<string, string>;
  onCardClick?: (evidence: Evidence) => void;
}

export function EvidenceLedger({
  evidence,
  totalCount,
  sortField,
  onSortChange,
  elementMap,
  claimLabelMap,
  onCardClick,
}: EvidenceLedgerProps) {
  const sorted = sortEvidence(evidence, sortField, elementMap);

  return (
    <div>
      <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-zinc-400 mb-6 border-b border-zinc-100 pb-2 flex justify-between items-center">
        <span>Evidence Ledger &middot; Showing {evidence.length} of {totalCount}</span>
        <SortControl value={sortField} onChange={onSortChange} />
      </div>

      <div className="space-y-3 mb-12">
        {sorted.map((ev) => {
          const evId = ev.evidenceId || ev.id;
          return (
            <LedgerCard
              key={ev.id}
              evidence={ev}
              elementIds={elementMap.get(evId)}
              claimLabel={claimLabelMap?.get(evId)}
              onClick={() => onCardClick?.(ev)}
            />
          );
        })}

        {sorted.length === 0 && (
          <div className="py-8 text-center border border-dashed border-zinc-200">
            <p className="font-mono text-[11px] uppercase tracking-widest text-zinc-400">
              No evidence matches current filters
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
