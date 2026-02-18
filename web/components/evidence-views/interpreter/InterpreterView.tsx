'use client';

import { useState, useMemo, useCallback } from 'react';
import { Claim, Evidence, EvidenceRelationship } from '@shared/types';
import { ElementSelector } from './ElementSelector';
import { ElementFocusPanel } from './ElementFocusPanel';
import { DispositionBar } from './DispositionBar';
import { EvidenceGroups } from './EvidenceGroups';
import { ProvenanceNote } from './ProvenanceNote';
import { ElementNavigation } from './ElementNavigation';

interface InterpreterViewProps {
  claim: Claim;
}

export function InterpreterView({ claim }: InterpreterViewProps) {
  const [activeIndex, setActiveIndex] = useState(0);

  const elements = useMemo(() => claim.claimMap?.elements || [], [claim.claimMap?.elements]);

  // Build evidence lookup: evidenceId → Evidence object
  const evidenceLookup = useMemo(() => {
    const map = new Map<string, Evidence>();
    for (const ev of claim.evidence || []) {
      const key = ev.evidenceId || ev.id;
      map.set(key, ev);
    }
    return map;
  }, [claim.evidence]);

  // Group evidence by disposition for the active element
  const { supports, challenges, context } = useMemo(() => {
    const groups: Record<EvidenceRelationship, Evidence[]> = {
      supports: [],
      challenges: [],
      context: [],
    };

    if (activeIndex < elements.length) {
      const element = elements[activeIndex];
      for (const ref of element.evidenceRefs || []) {
        const ev = evidenceLookup.get(ref.evidenceId);
        if (ev) {
          const rel = ref.relationship || 'context';
          groups[rel].push(ev);
        }
      }
    }

    return groups;
  }, [elements, activeIndex, evidenceLookup]);

  const handleCardClick = useCallback((ev: Evidence) => {
    if (ev.url) {
      window.open(ev.url, '_blank', 'noopener,noreferrer');
    }
  }, []);

  if (elements.length === 0) {
    return (
      <div className="py-12 text-center border border-dashed border-zinc-200 bg-zinc-50/30">
        <p className="font-mono text-[11px] uppercase tracking-widest text-zinc-400">
          No elements available for this claim
        </p>
      </div>
    );
  }

  const activeElement = elements[activeIndex];

  return (
    <div>
      <ElementSelector
        elements={elements}
        activeIndex={activeIndex}
        onSelect={setActiveIndex}
      />

      <ElementFocusPanel
        element={activeElement}
        index={activeIndex}
        totalElements={elements.length}
      />

      <DispositionBar
        supports={supports.length}
        challenges={challenges.length}
        context={context.length}
      />

      <EvidenceGroups
        supports={supports}
        challenges={challenges}
        context={context}
        onCardClick={handleCardClick}
      />

      <ProvenanceNote />

      <ElementNavigation
        elements={elements}
        activeIndex={activeIndex}
        onNavigate={setActiveIndex}
      />
    </div>
  );
}
