'use client';

import { useState, useMemo, useCallback, useEffect } from 'react';
import { capture } from '@/lib/analytics';
import { Claim, Evidence, EvidenceTier, EvidenceType, EvidenceRelationship } from '@shared/types';
import { computeDiagnosticValues } from '@/lib/diagnostic-value';
import { EvidenceHeatmap } from './EvidenceHeatmap';
import { FilterPills } from './FilterPills';
import { EvidenceLedger } from './EvidenceLedger';
import { ReadingTable } from './ReadingTable';
import { RetrievalFunnel } from './RetrievalFunnel';
import { SortField } from './SortControl';

const TIER_INITIALS: Record<string, string> = {
  primary: 'P', reporting: 'R', commentary: 'C',
};
const TYPE_CODES: Record<string, string> = {
  data: 'DATA', official_statement: 'OFCL', news_reporting: 'NEWS',
  analysis: 'ANLYS', opinion: 'OPNON', academic: 'ACAD',
};

interface LibrarianViewProps {
  scope: 'check' | 'claim';
  claims: Claim[];
  /** Deep-link entry filter (Slice 0b) — set when arriving from a summary
   *  state-count click. `initialRelationships` filters by disposition;
   *  `focusElementId` narrows to one claim element. Both are clearable in-view. */
  initialRelationships?: EvidenceRelationship[];
  focusElementId?: string;
}

export function LibrarianView({ scope, claims, initialRelationships, focusElementId }: LibrarianViewProps) {
  const [activeTiers, setActiveTiers] = useState<Set<EvidenceTier>>(new Set());
  const [activeTypes, setActiveTypes] = useState<Set<EvidenceType>>(new Set());
  const [activeRelationships, setActiveRelationships] = useState<Set<EvidenceRelationship>>(
    () => new Set(initialRelationships || [])
  );
  const [focusElement, setFocusElement] = useState<string | undefined>(focusElementId);
  const [sortField, setSortField] = useState<SortField>('date');
  const [readingTableEvId, setReadingTableEvId] = useState<string | null>(null);

  // Re-sync the filter when a NEW deep-link arrives (e.g. clicking a different
  // summary state-count while already on the Evidence lens). Keyed on the
  // serialised deep-link so manual in-view filter changes are preserved.
  const deepLinkKey = `${(initialRelationships || []).join(',')}|${focusElementId || ''}`;
  useEffect(() => {
    setActiveRelationships(new Set(initialRelationships || []));
    setFocusElement(focusElementId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deepLinkKey]);

  // Diagnostic value computation
  const diagnostic = useMemo(() => computeDiagnosticValues(claims), [claims]);
  const [diagnosticActive, setDiagnosticActive] = useState(false);
  const showDiagnosticToggle = diagnostic.hasDiagnosticVariance;

  // Pool all evidence across claims (deduped by evidenceId for check-wide)
  const { allEvidence, includedEvidence, excludedEvidence, elementMap, claimLabelMap, elementDescriptionMap, relationshipRefs } = useMemo(() => {
    const seen = new Set<string>();
    const all: Evidence[] = [];
    const elementMap = new Map<string, string[]>();
    const claimLabelMap = new Map<string, string>();
    const elementDescriptionMap = new Map<string, string>();
    // evidenceId → its (element, disposition) refs (Slice 0b).
    const relationshipRefs = new Map<string, { elementId: string; relationship: EvidenceRelationship }[]>();

    claims.forEach((claim, claimIdx) => {
      const evidence = claim.evidence || [];

      // Build element map from ClaimMap
      if (claim.claimMap?.elements) {
        for (const element of claim.claimMap.elements) {
          // Store element descriptions
          if (element.description) {
            elementDescriptionMap.set(element.elementId, element.description);
          }
          for (const ref of element.evidenceRefs || []) {
            const existing = elementMap.get(ref.evidenceId) || [];
            if (!existing.includes(element.elementId)) {
              existing.push(element.elementId);
              elementMap.set(ref.evidenceId, existing);
            }
            const rExisting = relationshipRefs.get(ref.evidenceId) || [];
            rExisting.push({ elementId: element.elementId, relationship: ref.relationship });
            relationshipRefs.set(ref.evidenceId, rExisting);
          }
        }
      }

      for (const ev of evidence) {
        const evId = ev.evidenceId || ev.id;

        // For check-wide, deduplicate by evidenceId
        if (scope === 'check' && seen.has(evId)) continue;
        seen.add(evId);

        all.push(ev);

        // Claim attribution for check-wide mode
        if (scope === 'check') {
          const existing = claimLabelMap.get(evId);
          const label = `Claim ${String(claimIdx + 1).padStart(2, '0')}`;
          claimLabelMap.set(evId, existing ? `${existing}, ${label}` : label);
        }
      }
    });

    // Show all classified evidence in the landscape; only truly-excluded
    // items (extraction failures, duplicates, satire) drop out. Unmapped
    // items appear in the heatmap/ledger with no element badge — matches
    // Cartographer + Chronologist + Correspondent filtering and the
    // "no hidden curation" invariant.
    const isVisibleInLandscape = (ev: Evidence) =>
      ev.receiptStatus !== 'excluded';
    const included = all.filter(isVisibleInLandscape);
    const excluded = all.filter((ev) => !isVisibleInLandscape(ev));

    return { allEvidence: all, includedEvidence: included, excludedEvidence: excluded, elementMap, claimLabelMap, elementDescriptionMap, relationshipRefs };
  }, [claims, scope]);

  // Distinct disposition(s) per evidenceId — for the ledger card marker. When an
  // element is focused, the marker shows only this evidence's relation to THAT
  // element; otherwise it shows all distinct relations across mapped elements.
  const relationshipSummaryMap = useMemo(() => {
    const map = new Map<string, EvidenceRelationship[]>();
    relationshipRefs.forEach((refs, evId) => {
      const scoped = focusElement ? refs.filter((r) => r.elementId === focusElement) : refs;
      const distinct = Array.from(new Set(scoped.map((r) => r.relationship)));
      if (distinct.length > 0) map.set(evId, distinct);
    });
    return map;
  }, [relationshipRefs, focusElement]);

  // Compute call numbers from includedEvidence (stable, before filtering)
  const callNumberMap = useMemo(() => {
    const map = new Map<string, string>();
    const groupCounters: Record<string, number> = {};

    for (const ev of includedEvidence) {
      const evId = ev.evidenceId || ev.id;
      const tier = ev.tier || 'commentary';
      const type = ev.evidenceType || 'news_reporting';
      const tierInit = TIER_INITIALS[tier] || 'C';
      const typeCode = TYPE_CODES[type] || 'NEWS';
      const groupKey = `${tier}:${type}`;

      groupCounters[groupKey] = (groupCounters[groupKey] || 0) + 1;
      const seq = String(groupCounters[groupKey]).padStart(2, '0');
      map.set(evId, `${tierInit}\u00B7${typeCode}\u00B7${seq}`);
    }

    return map;
  }, [includedEvidence]);

  // Apply filters — tier, type, disposition (Slice 0b), and element focus.
  const filteredEvidence = useMemo(() => {
    return includedEvidence.filter((ev) => {
      const evId = ev.evidenceId || ev.id;
      if (activeTiers.size > 0 && !activeTiers.has(ev.tier || 'commentary')) return false;
      if (activeTypes.size > 0 && !activeTypes.has(ev.evidenceType || 'news_reporting')) return false;
      const refs = relationshipRefs.get(evId) || [];
      const scoped = focusElement ? refs.filter((r) => r.elementId === focusElement) : refs;
      // Element focus: keep only evidence mapped to the focused element.
      if (focusElement && scoped.length === 0) return false;
      // Disposition: evidence must carry a matching relationship — to the focused
      // element when focused, otherwise to any element it maps to.
      if (activeRelationships.size > 0 && !scoped.some((r) => activeRelationships.has(r.relationship))) return false;
      return true;
    });
  }, [includedEvidence, activeTiers, activeTypes, activeRelationships, focusElement, relationshipRefs]);

  // Find the active evidence for the desktop reading table
  const activeEvidence = useMemo(() => {
    if (!readingTableEvId) return null;
    return filteredEvidence.find((ev) => (ev.evidenceId || ev.id) === readingTableEvId) || null;
  }, [readingTableEvId, filteredEvidence]);

  const handleToggleTier = useCallback((tier: EvidenceTier) => {
    setActiveTiers((prev) => {
      const next = new Set(prev);
      if (next.has(tier)) next.delete(tier);
      else next.add(tier);
      return next;
    });
  }, []);

  const handleToggleType = useCallback((type: EvidenceType) => {
    setActiveTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }, []);

  const handleToggleRelationship = useCallback((rel: EvidenceRelationship) => {
    setActiveRelationships((prev) => {
      const next = new Set(prev);
      if (next.has(rel)) next.delete(rel);
      else next.add(rel);
      return next;
    });
  }, []);

  const handleClearAll = useCallback(() => {
    setActiveTiers(new Set());
    setActiveTypes(new Set());
    setActiveRelationships(new Set());
  }, []);

  const handleCellClick = useCallback((tier: EvidenceTier, type: EvidenceType) => {
    setActiveTiers(new Set([tier]));
    setActiveTypes(new Set([type]));
  }, []);

  const handleCardClick = useCallback((ev: Evidence) => {
    const evId = ev.evidenceId || ev.id;
    setReadingTableEvId((prev) => {
      const next = prev === evId ? null : evId;
      if (next) capture('evidence_expanded');
      return next;
    });
  }, []);

  // Build element descriptions for the active evidence reading table
  const activeElementDescriptions = useMemo(() => {
    if (!activeEvidence) return [];
    const evId = activeEvidence.evidenceId || activeEvidence.id;
    const elIds = elementMap.get(evId) || [];
    return elIds.map((eid) => ({
      elementId: eid,
      description: elementDescriptionMap.get(eid) || '',
    }));
  }, [activeEvidence, elementMap, elementDescriptionMap]);

  return (
    <div>
      <EvidenceHeatmap
        evidence={includedEvidence}
        onCellClick={handleCellClick}
      />

      <FilterPills
        activeTiers={activeTiers}
        activeTypes={activeTypes}
        activeRelationships={activeRelationships}
        onToggleTier={handleToggleTier}
        onToggleType={handleToggleType}
        onToggleRelationship={handleToggleRelationship}
        onClearAll={handleClearAll}
      />

      {/* Element-focus context (Slice 0b) — arrived from a summary state-count
          deep-link; names the focused element and offers a clear affordance. */}
      {focusElement && (
        <div className="flex items-start gap-2 mb-4 border-l-2 border-zinc-300 pl-3 py-1">
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400 pt-0.5 shrink-0">Focus</span>
          <span className="text-[11px] text-zinc-600 flex-grow">
            {elementDescriptionMap.get(focusElement) || 'Selected element'}
          </span>
          <button
            type="button"
            onClick={() => setFocusElement(undefined)}
            className="font-mono text-[9px] uppercase tracking-widest text-zinc-400 hover:text-zinc-900 transition-colors shrink-0 cursor-pointer"
          >
            Clear
          </button>
        </div>
      )}

      {/* Diagnostic toggle */}
      {showDiagnosticToggle && (
        <div className="flex items-center gap-2 mb-4">
          <button
            onClick={() => setDiagnosticActive((prev) => !prev)}
            className={`flex items-center gap-1.5 px-3 py-1.5 border text-[10px] font-mono uppercase tracking-widest transition-colors ${
              diagnosticActive
                ? 'bg-zinc-900 text-white border-zinc-900'
                : 'text-zinc-400 hover:text-zinc-600 border-zinc-200'
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${diagnosticActive ? 'bg-[var(--accent)]' : 'bg-zinc-300'}`} />
            Diagnostic
          </button>
        </div>
      )}

      {/* Desktop reading table — between filters and ledger */}
      {activeEvidence && (
        <div className="hidden lg:block mb-6">
          <ReadingTable
            evidence={activeEvidence}
            callNumber={callNumberMap.get(activeEvidence.evidenceId || activeEvidence.id) || ''}
            elementDescriptions={activeElementDescriptions}
            claimLabel={claimLabelMap?.get(activeEvidence.evidenceId || activeEvidence.id)}
            onClose={() => setReadingTableEvId(null)}
          />
        </div>
      )}

      <EvidenceLedger
        evidence={filteredEvidence}
        totalCount={includedEvidence.length}
        sortField={sortField}
        onSortChange={setSortField}
        elementMap={elementMap}
        claimLabelMap={scope === 'check' ? claimLabelMap : undefined}
        callNumberMap={callNumberMap}
        diagnosticValues={showDiagnosticToggle ? diagnostic.values : undefined}
        diagnosticActive={showDiagnosticToggle && diagnosticActive}
        activeEvidenceId={readingTableEvId}
        onCardClick={handleCardClick}
        elementDescriptionMap={elementDescriptionMap}
        relationshipMap={relationshipSummaryMap}
      />

      <RetrievalFunnel
        reviewedCount={claims.reduce((sum, c) => sum + (c.sourcesReviewedCount || 0), 0)}
        includedCount={includedEvidence.length}
        excludedEvidence={excludedEvidence}
      />
    </div>
  );
}
