'use client';

import { useMemo, useState, useEffect } from 'react';
import { Claim, ClaimElement, RelatedClaim } from '@shared/types';
import { apiClient } from '@/lib/api';
import { UnknownsSummaryStrip } from './UnknownsSummaryStrip';
import { UnknownElementCard } from './UnknownElementCard';
import { CoverageMap } from './CoverageMap';
import { ResearchButton } from './ResearchButton';
import { SeekerProvenanceNote } from './SeekerProvenanceNote';
import { ExplorePanel } from './ExplorePanel';
import { DiagnosticFlag } from '../DiagnosticFlag';
import { evidenceCoverage, hasMappedEvidence, needsEvidenceReview } from '@/lib/evidence-coverage';

interface SeekerViewProps {
  claim: Claim;
  readOnly?: boolean;
  checkId?: string;
  token?: string | null;
  onResearchComplete?: () => void;
}

interface IndexedElement {
  element: ClaimElement;
  originalIndex: number;
}

export function SeekerView({ claim, readOnly, checkId, token, onResearchComplete }: SeekerViewProps) {
  const elements = useMemo(() => claim.claimMap?.elements || [], [claim.claimMap?.elements]);
  const evidence = useMemo(() => claim.evidence || [], [claim.evidence]);

  // Credit info for re-search gating
  const [creditInfo, setCreditInfo] = useState<{ remaining: number } | null>(null);
  const [resolvedOpen, setResolvedOpen] = useState(false);

  // Explore mode: related claims from other users
  const [exploreData, setExploreData] = useState<RelatedClaim[]>([]);
  const [exploreLoading, setExploreLoading] = useState(false);

  useEffect(() => {
    if (readOnly || !token) return;
    let cancelled = false;

    apiClient.getUsage(token).then((raw: unknown) => {
      if (cancelled) return;
      // Derive from the allowance window, the same pair every other surface
      // uses (dashboard hero, new-check, settings). NOT `creditsRemaining`.
      //
      // B2: that field was `user.credits`, a legacy counter reset only on the
      // Stripe billing period — once a YEAR on an annual plan, while the
      // allowance itself refreshes monthly. An annual subscriber who spent 200
      // checks in month 1 read 0 for the next eleven months and had re-search
      // disabled on it, while the backend would have served the request.
      //
      // The endpoint now derives the field correctly too, so this is belt and
      // braces — and it leaves the legacy counter with no readers at all.
      const usage = raw as
        | { creditsPerPeriod?: number; periodCreditsUsed?: number }
        | undefined;
      if (
        typeof usage?.creditsPerPeriod === 'number' &&
        typeof usage?.periodCreditsUsed === 'number'
      ) {
        setCreditInfo({
          remaining: Math.max(0, usage.creditsPerPeriod - usage.periodCreditsUsed),
        });
      }
    }).catch(() => {
      // Non-critical — button will work without credit display
    });

    return () => { cancelled = true; };
  }, [readOnly, token]);

  const metrics = useMemo(() => evidenceCoverage(elements), [elements]);

  // Determine if explore mode should activate
  const hasUnknowns = metrics.gaps > 0 || metrics.needsReview > 0;

  // Fetch explore data when no unknowns remain
  useEffect(() => {
    if (hasUnknowns || readOnly || !checkId || !token) return;
    let cancelled = false;

    setExploreLoading(true);
    apiClient.getExploreData(checkId, claim.id, token).then((data) => {
      if (cancelled) return;
      setExploreData(data.relatedClaims || []);
    }).catch(() => {
      // Non-critical — explore panel will show empty state
    }).finally(() => {
      if (!cancelled) setExploreLoading(false);
    });

    return () => { cancelled = true; };
  }, [hasUnknowns, readOnly, checkId, claim.id, token]);

  // Keep context-only and disputed elements visible for review. Finding
  // related material does not resolve the question it was retrieved for.
  const { gapElements, unresolvedElements, resolvedElements } = useMemo(() => {
    const gapEls: IndexedElement[] = [];
    const unresolvedEls: IndexedElement[] = [];
    const resolvedEls: IndexedElement[] = [];

    elements.forEach((element, originalIndex) => {
      const isGap = !hasMappedEvidence(element);

      if (isGap) {
        gapEls.push({ element, originalIndex });
      } else if (needsEvidenceReview(element)) {
        unresolvedEls.push({ element, originalIndex });
      } else {
        resolvedEls.push({ element, originalIndex });
      }
    });

    return { gapElements: gapEls, unresolvedElements: unresolvedEls, resolvedElements: resolvedEls };
  }, [elements]);

  // Gap element IDs for the claim-level research button
  const gapElementIds = useMemo(
    () => gapElements.map(g => g.element.elementId),
    [gapElements],
  );

  if (elements.length === 0) {
    return (
      <div className="py-12 text-center border border-dashed border-zinc-200 bg-zinc-50/30">
        <p className="font-mono text-[11px] uppercase tracking-widest text-zinc-400">
          No elements available for this claim
        </p>
      </div>
    );
  }

  const renderCard = ({ element, originalIndex }: IndexedElement, gapIdx?: number) => (
    <UnknownElementCard
      key={element.elementId}
      element={element}
      index={originalIndex}
      evidence={evidence}
      readOnly={readOnly}
      checkId={checkId}
      claimId={claim.id}
      token={token}
      gapIndex={gapIdx}
      totalGaps={gapElements.length}
    />
  );

  return (
    <div className="space-y-6">
      <UnknownsSummaryStrip {...metrics} />
      <CoverageMap elements={elements} />

      {/* Evidence Gaps */}
      {gapElements.length > 0 && (
        <div className="space-y-3">
          <p className="font-mono text-[10px] font-bold uppercase tracking-widest text-zinc-500">
            Evidence Gaps
          </p>
          {gapElements.map((entry, gapIdx) => renderCard(entry, gapIdx))}

          {/* Single claim-level research button for all gaps */}
          {!readOnly && checkId && token && (
            <ResearchButton
              checkId={checkId}
              claimId={claim.id}
              token={token}
              gapElementIds={gapElementIds}
              creditInfo={creditInfo}
              coverageBefore={metrics.coverage}
              onComplete={onResearchComplete}
            />
          )}
        </div>
      )}

      {/* Unresolved */}
      {unresolvedElements.length > 0 && (
        <div className="space-y-3">
          <p className="font-mono text-[10px] font-bold uppercase tracking-widest text-zinc-500">
            Needs review
          </p>
          {unresolvedElements.map(entry => renderCard(entry))}
        </div>
      )}

      {/* Resolved — collapsible */}
      {resolvedElements.length > 0 && (
        <div className="space-y-3">
          <button
            onClick={() => setResolvedOpen(!resolvedOpen)}
            className="flex items-center gap-2 font-mono text-[10px] font-bold uppercase tracking-widest text-zinc-400 hover:text-zinc-600 transition-colors"
          >
            <span className="text-[8px]">{resolvedOpen ? '\u25BC' : '\u25B6'}</span>
            Predominantly Supported Elements ({resolvedElements.length})
          </button>
          {resolvedOpen && resolvedElements.map(entry => renderCard(entry))}
        </div>
      )}

      {/* Well-covered empty state — positive reframe, no deflection */}
      {!hasUnknowns && (
        <div className="space-y-4">
          <DiagnosticFlag label="Evidence mapped">
            Each element has supporting evidence mapped. Review the source passages and limitations; coverage does not establish completeness or certainty.
          </DiagnosticFlag>
        </div>
      )}

      {/* Adjacent investigations — only when the explore panel actually has data */}
      {!hasUnknowns && !readOnly && checkId && token && exploreData.length > 0 && (
        <div className="border-t border-zinc-200 pt-6 space-y-3">
          <p className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">
            Adjacent investigations
          </p>
          <ExplorePanel relatedClaims={exploreData} />
        </div>
      )}

      <SeekerProvenanceNote />
    </div>
  );
}
