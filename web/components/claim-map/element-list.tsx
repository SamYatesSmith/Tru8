'use client';

import type { ClaimElement } from '@shared/types';
import { ElementStateBadge } from './element-state-badge';
import { EvidenceRefChip } from './evidence-ref-chip';

interface ElementListProps {
  elements: ClaimElement[];
}

export function ElementList({ elements }: ElementListProps) {
  return (
    <div className="flex flex-col gap-4">
      {elements.map((element, index) => (
        <div key={element.elementId} className="flex flex-col gap-2">
          <div className="flex items-start gap-3">
            <span className="font-mono text-xs text-zinc-300 pt-0.5">
              {String(index + 1).padStart(2, '0')}
            </span>
            <div className="flex flex-col gap-2 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm text-zinc-700">{element.description}</span>
                {element.state && (
                  <ElementStateBadge state={element.state} size="sm" basis={element.basis} />
                )}
              </div>

              {element.evidenceRefs.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {element.evidenceRefs.map((ref) => (
                    <EvidenceRefChip
                      key={`${ref.evidenceId}-${ref.relationship}`}
                      evidenceId={ref.evidenceId}
                      relationship={ref.relationship}
                    />
                  ))}
                </div>
              )}

              {element.uncertainty && (
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-amber-600">{'\u26A0'}</span>
                  <span className="text-xs italic text-amber-600">{element.uncertainty}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
