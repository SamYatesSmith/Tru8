'use client';

import { Evidence, EvidenceTier, EvidenceRelationship } from '@shared/types';
import { LedgerCard } from './LedgerCard';
import { ReadingTable } from './ReadingTable';
import { SortControl, SortField } from './SortControl';

const TIER_ORDER: Record<string, number> = { primary: 0, reporting: 1, commentary: 2 };
const TIER_GROUPS: EvidenceTier[] = ['primary', 'reporting', 'commentary'];

const TIER_DIVIDER_LABELS: Record<EvidenceTier, string> = {
  primary: 'PRIMARY SOURCES',
  reporting: 'REPORTING SOURCES',
  commentary: 'COMMENTARY SOURCES',
};

const TIER_DIVIDER_COLORS: Record<EvidenceTier, string> = {
  primary: 'text-[#EA580C]',
  reporting: 'text-[#3F3F46]',
  commentary: 'text-[#A1A1AA]',
};

function sortWithinGroup(items: Evidence[], field: SortField, elementMap: Map<string, string[]>): Evidence[] {
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
  callNumberMap: Map<string, string>;
  diagnosticValues?: Map<string, number>;
  diagnosticActive?: boolean;
  activeEvidenceId: string | null;
  onCardClick?: (evidence: Evidence) => void;
  elementDescriptionMap: Map<string, string>;
  /** Distinct disposition(s) per evidenceId (Slice 0b); undefined → no marker. */
  relationshipMap?: Map<string, EvidenceRelationship[]>;
  mobileReadingTable?: React.ReactNode;
}

export function EvidenceLedger({
  evidence,
  totalCount,
  sortField,
  onSortChange,
  elementMap,
  claimLabelMap,
  callNumberMap,
  diagnosticValues,
  diagnosticActive,
  activeEvidenceId,
  onCardClick,
  elementDescriptionMap,
  relationshipMap,
}: EvidenceLedgerProps) {
  // Group evidence by tier, then sort within each group
  const tierGroups = TIER_GROUPS.map((tier) => {
    const items = evidence.filter((ev) => (ev.tier || 'commentary') === tier);
    return {
      tier,
      items: sortWithinGroup(items, sortField, elementMap),
    };
  }).filter((group) => group.items.length > 0);

  return (
    <div>
      <div className="font-mono text-sm font-bold uppercase tracking-[0.15em] lg:tracking-[0.3em] text-zinc-600 mb-6 border-b border-zinc-200 pb-2 flex flex-col gap-1 lg:flex-row lg:justify-between lg:items-center">
        <span>
          <span className="hidden lg:inline">Evidence Ledger &middot; Showing {evidence.length} of {totalCount}</span>
          <span className="lg:hidden">Ledger &middot; {evidence.length}/{totalCount}</span>
        </span>
        <SortControl value={sortField} onChange={onSortChange} />
      </div>

      <div className="space-y-3 mb-12">
        {tierGroups.map((group) => (
          <div key={group.tier}>
            {/* Shelf Divider */}
            <div className="flex items-center gap-3 my-4">
              <span className="flex-1 h-px bg-zinc-200" />
              <span className={`font-mono text-[10px] uppercase tracking-[0.25em] font-bold ${TIER_DIVIDER_COLORS[group.tier]}`}>
                {TIER_DIVIDER_LABELS[group.tier]} ({group.items.length})
              </span>
              <span className="flex-1 h-px bg-zinc-200" />
            </div>

            {group.items.map((ev) => {
              const evId = ev.evidenceId || ev.id;
              const isActive = activeEvidenceId === evId;

              // Build element descriptions for mobile reading table
              const elIds = elementMap.get(evId) || [];
              const elDescs = elIds.map((eid) => ({
                elementId: eid,
                description: elementDescriptionMap.get(eid) || '',
              }));

              return (
                <div key={ev.id}>
                  <LedgerCard
                    evidence={ev}
                    callNumber={callNumberMap.get(evId)}
                    elementIds={elementMap.get(evId)}
                    claimLabel={claimLabelMap?.get(evId)}
                    relationships={relationshipMap?.get(evId)}
                    elementDescriptions={elementDescriptionMap}
                    diagnosticValue={diagnosticValues?.get(evId)}
                    diagnosticActive={diagnosticActive}
                    isActive={isActive}
                    onClick={() => onCardClick?.(ev)}
                  />
                  {/* Mobile reading table — inline after active card */}
                  {isActive && (
                    <div className="lg:hidden mt-2">
                      <ReadingTable
                        evidence={ev}
                        callNumber={callNumberMap.get(evId) || ''}
                        elementDescriptions={elDescs}
                        claimLabel={claimLabelMap?.get(evId)}
                        onClose={() => onCardClick?.(ev)}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ))}

        {evidence.length === 0 && (
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
