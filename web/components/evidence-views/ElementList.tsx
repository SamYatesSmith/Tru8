'use client';

import { ClaimElement } from '@shared/types';
import { ElementBadge } from './ElementBadge';
import { ElementStateBadge, ElementStateKey } from './ElementStateBadge';
import { EvidenceQualityNote } from './EvidenceQualityNote';
import { TopUpButton } from './TopUpButton';
import { elementIsThin } from '@/lib/support-structure';
import { elementCaveatNote } from '@/lib/element-caveat';

/** Dashboard-only capability to top up a thin element. Absent on the public report. */
export interface TopUpCapability {
  checkId: string;
  claimId: string;
  token: string | null;
  onComplete?: () => void;
}

interface ElementListProps {
  elements: ClaimElement[];
  /** When present, thin elements show a "Get more sources" trigger. */
  topUp?: TopUpCapability;
}

/**
 * The platformed element roster — the reader's introduction to the sub-elements
 * the claim was broken into. Lives in the digest (ClaimSummaryPanel), above the
 * distribution bar, so the reader meets the elements before the rest of the
 * report cites them. Each row leads with the ElementBadge (the recurring
 * reference token) and carries the element's state + any source-quality note.
 *
 * Migrated up out of the Map lens, where it used to sit at the bottom.
 */
export function ElementList({ elements, topUp }: ElementListProps) {
  if (elements.length === 0) return null;

  return (
    <div className="space-y-1.5">
      {elements.map((element, i) => {
        const sourceCount = element.evidenceRefs?.length || 0;
        const state = (element.state || 'unresolved') as ElementStateKey;
        const isGap = sourceCount === 0;
        // Fix 1 (2026-09-02): the mapper's one-sentence caveat, gated so only a
        // genuine limit of the evidence reaches the page — never an adjudication
        // restating the badge. Grey, no colour, verbatim or nothing.
        // Design: audit/2026-09-02_fix1_element_caveat_render_design.md
        const caveat = isGap ? null : elementCaveatNote(element.uncertainty);

        return (
          <div
            key={element.elementId}
            className={`px-3 py-2.5 border ${
              isGap ? 'border-dashed border-zinc-200 bg-zinc-50/40' : 'border-zinc-100'
            }`}
          >
            <div className="flex items-start gap-3">
              <ElementBadge n={i + 1} size="md" className={isGap ? 'opacity-60' : ''} />
              <div className="flex-grow min-w-0">
                <div className="flex items-start justify-between gap-3">
                  <span
                    className={`text-sm font-medium leading-snug ${
                      isGap ? 'text-zinc-400' : 'text-zinc-900'
                    }`}
                  >
                    {element.description}
                  </span>
                  <div className="flex items-center gap-2 shrink-0">
                    <span
                      className={`font-mono text-[10px] ${isGap ? 'text-zinc-400' : 'text-zinc-500'}`}
                    >
                      {sourceCount} {sourceCount === 1 ? 'source' : 'sources'}
                    </span>
                    <ElementStateBadge
                      state={isGap ? 'unresolved' : state}
                      label={isGap ? 'Gap' : undefined}
                      basis={element.basis}
                      size="md"
                    />
                  </div>
                </div>
                {!isGap && <EvidenceQualityNote basis={element.basis} />}
                {caveat && (
                  <p
                    title={caveat}
                    data-testid="element-caveat"
                    className="mt-1.5 font-mono text-[10px] leading-relaxed text-zinc-500 line-clamp-2"
                  >
                    <span className="text-zinc-400 uppercase tracking-wider">Note</span>
                    <span className="text-zinc-300"> &middot; </span>
                    {caveat}
                  </p>
                )}
                {topUp && !isGap && elementIsThin(element) && (
                  <div className="mt-2">
                    <TopUpButton
                      mode="element"
                      checkId={topUp.checkId}
                      claimId={topUp.claimId}
                      token={topUp.token}
                      elementId={element.elementId}
                      onComplete={topUp.onComplete}
                    />
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
