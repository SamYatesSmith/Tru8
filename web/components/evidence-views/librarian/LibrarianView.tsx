'use client';

import { useState, useMemo, useCallback } from 'react';
import { Claim, Evidence, EvidenceTier, EvidenceType } from '@shared/types';
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
}

export function LibrarianView({ scope, claims }: LibrarianViewProps) {
  const [activeTiers, setActiveTiers] = useState<Set<EvidenceTier>>(new Set());
  const [activeTypes, setActiveTypes] = useState<Set<EvidenceType>>(new Set());
  const [sortField, setSortField] = useState<SortField>('date');
  const [readingTableEvId, setReadingTableEvId] = useState<string | null>(null);

  // Diagnostic value computation
  const diagnostic = useMemo(() => computeDiagnosticValues(claims), [claims]);
  const [diagnosticActive, setDiagnosticActive] = useState(false);
  const showDiagnosticToggle = diagnostic.hasDiagnosticVariance;

  // Pool all evidence across claims (deduped by evidenceId for check-wide)
  const { allEvidence, includedEvidence, excludedEvidence, elementMap, claimLabelMap, elementDescriptionMap } = useMemo(() => {
    const seen = new Set<string>();
    const all: Evidence[] = [];
    const elementMap = new Map<string, string[]>();
    const claimLabelMap = new Map<string, string>();
    const elementDescriptionMap = new Map<string, string>();

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

    const included = all.filter((ev) => ev.receiptStatus !== 'excluded');
    const excluded = all.filter((ev) => ev.receiptStatus === 'excluded');

    return { allEvidence: all, includedEvidence: included, excludedEvidence: excluded, elementMap, claimLabelMap, elementDescriptionMap };
  }, [claims, scope]);

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

  // Apply filters
  const filteredEvidence = useMemo(() => {
    return includedEvidence.filter((ev) => {
      if (activeTiers.size > 0 && !activeTiers.has(ev.tier || 'commentary')) return false;
      if (activeTypes.size > 0 && !activeTypes.has(ev.evidenceType || 'news_reporting')) return false;
      return true;
    });
  }, [includedEvidence, activeTiers, activeTypes]);

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

  const handleClearAll = useCallback(() => {
    setActiveTiers(new Set());
    setActiveTypes(new Set());
  }, []);

  const handleCellClick = useCallback((tier: EvidenceTier, type: EvidenceType) => {
    setActiveTiers(new Set([tier]));
    setActiveTypes(new Set([type]));
  }, []);

  const handleCardClick = useCallback((ev: Evidence) => {
    const evId = ev.evidenceId || ev.id;
    setReadingTableEvId((prev) => (prev === evId ? null : evId));
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
        onToggleTier={handleToggleTier}
        onToggleType={handleToggleType}
        onClearAll={handleClearAll}
      />

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
        <div className="hidden md:block mb-6">
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
      />

      <RetrievalFunnel
        reviewedCount={claims.reduce((sum, c) => sum + (c.sourcesReviewedCount || 0), 0)}
        includedCount={includedEvidence.length}
        excludedEvidence={excludedEvidence}
      />
    </div>
  );
}
