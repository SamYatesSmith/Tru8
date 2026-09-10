'use client';

import { Evidence, EvidenceTier, EvidenceRelationship } from '@shared/types';
import { LedgerCard } from './LedgerCard';
import { ReadingTable } from './ReadingTable';
import { SortField } from './SortControl';
import { SegmentedRow } from './SegmentedRow';

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
  /** Public record (/r/): model free text in the reading table is gated. */
  readOnly?: boolean;
  evidence: Evidence[];
  totalCount: number;
  sortField: SortField;
  onSortChange: (field: SortField) => void;
  elementMap: Map<string, string[]>;
  claimLabelMap?: Map<string, string>;
  callNumberMap: Map<string, string>;
  diagnosticValues?: Map<string, number>;
  diagnosticActive?: boolean;
  /** Present when the check has diagnostic variance: renders the
   *  "Highlight decisive sources" switch in the header beside Sort. */
  onToggleDiagnostic?: () => void;
  activeEvidenceId: string | null;
  onCardClick?: (evidence: Evidence) => void;
  elementDescriptionMap: Map<string, string>;
  /** Distinct disposition(s) per evidenceId (Slice 0b); undefined → no marker. */
  relationshipMap?: Map<string, EvidenceRelationship[]>;
  mobileReadingTable?: React.ReactNode;
  activeElementDescriptions?: React.ComponentProps<typeof ReadingTable>['elementDescriptions'];
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
  onToggleDiagnostic,
  activeEvidenceId,
  onCardClick,
  elementDescriptionMap,
  relationshipMap,
  activeElementDescriptions,
  readOnly,
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
      {/* Ledger header (fresh approach 2026-09-10): the heading, then the
          ledger's two controls as SegmentedRows — the SAME shape as the
          filter rows above — side by side from `md`, stacked on a phone. The
          highlight row is the ACH diagnostic view: "Decisive" marks a source
          that supports one element while challenging another (orange left
          rule on its card) and fades context-only / same-direction sources.
          Rendered only when the check has any challenges to tell apart. */}
      <div className="mb-6">
        <div className="font-mono text-sm font-bold uppercase tracking-[0.15em] lg:tracking-[0.3em] text-zinc-600 border-b border-zinc-200 pb-2 mb-3">
          <span className="hidden lg:inline">Evidence Ledger{evidence.length === totalCount && <> &middot; {totalCount} {totalCount === 1 ? 'source' : 'sources'}</>}</span>
          <span className="lg:hidden">Ledger{evidence.length === totalCount && <> &middot; {totalCount}</>}</span>
        </div>
        <div className={`border border-zinc-300 grid grid-cols-1 ${onToggleDiagnostic ? 'md:grid-cols-2' : ''}`}>
          <div className="[&>*]:border-t-0">
            <SegmentedRow<SortField>
              label="Sort"
              ariaLabel="Sort the ledger"
              options={[
                { value: 'date', label: 'Date' },
                { value: 'source', label: 'Source' },
                { value: 'element', label: 'Element' },
              ]}
              active={new Set([sortField])}
              onSelect={onSortChange}
            />
          </div>
          {onToggleDiagnostic && (
            <div className="border-t border-zinc-300 md:border-t-0 md:border-l [&>*]:border-t-0">
              <SegmentedRow<'off' | 'on'>
                label="View"
                ariaLabel="Highlight decisive sources"
                options={[
                  { value: 'off', label: 'All sources' },
                  {
                    value: 'on',
                    label: 'Highlight decisive',
                    mark: <span aria-hidden className={`w-2 h-2 rounded-full shrink-0 ${diagnosticActive ? 'bg-[var(--accent)]' : 'border border-zinc-300'}`} />,
                  },
                ]}
                active={new Set<'off' | 'on'>([diagnosticActive ? 'on' : 'off'])}
                onSelect={(v) => { if ((v === 'on') !== !!diagnosticActive) onToggleDiagnostic(); }}
              />
            </div>
          )}
        </div>
        {onToggleDiagnostic && (
          <p className="mt-2 text-xs text-zinc-500">
            Decisive: a source that supports one element while challenging another — it tells the claim&rsquo;s
            possibilities apart. Highlighted with an orange rule; context-only sources fade.
          </p>
        )}
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
                        elementDescriptions={activeElementDescriptions || elDescs}
                        claimLabel={claimLabelMap?.get(evId)}
                        readOnly={readOnly}
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
