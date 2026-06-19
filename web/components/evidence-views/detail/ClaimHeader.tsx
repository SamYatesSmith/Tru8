'use client';

import { Claim, InputType } from '@shared/types';
import { DiagnosticFlag } from '../DiagnosticFlag';
import { ELEMENT_STATE } from '../ElementStateBadge';

const CONTEXT_LABELS: Record<string, string> = {
  url: 'Extracted Claim',
  text: 'Submitted Claim',
};

interface ClaimHeaderProps {
  claim: Claim;
  position: number;
  inputType?: InputType;
}

export function ClaimHeader({ claim, position, inputType }: ClaimHeaderProps) {
  const claimMap = claim.claimMap;
  const elements = claimMap?.elements || [];
  const evidenceCount = claim.evidence?.length || 0;
  const orientation = claimMap?.orientation;
  const claimType = claimMap?.claimType || claim.claimType;

  const rankLabel = String(position + 1).padStart(2, '0');
  const contextLabel = CONTEXT_LABELS[inputType || ''] || 'Submitted Claim';

  const typeLabels: Record<string, string> = {
    empirical: 'Empirical',
    definitional: 'Definitional',
    causal_interpretive: 'Causal',
    predictive: 'Predictive',
    normative_flagged: 'Normative',
  };

  // Count element states. 2026-05-12: contextual elements have
  // evidence in the pool (context-tier only) — they're not a gap.
  const stateCounts = { supported: 0, disputed: 0, contextual: 0, gap: 0 };
  for (const el of elements) {
    if (el.state === 'supported') stateCounts.supported++;
    else if (el.state === 'disputed') stateCounts.disputed++;
    else if (el.state === 'contextual') stateCounts.contextual++;
    else stateCounts.gap++;
  }

  return (
    <div>
      {/* Position + context label + type badge */}
      <div className="flex items-center gap-3 mb-2">
        <span className="font-mono text-xs font-bold text-zinc-300">{rankLabel}</span>
        <span className="px-2.5 py-0.5 bg-zinc-50 border border-zinc-200 text-[9px] font-mono font-bold uppercase tracking-wider text-zinc-500">
          {contextLabel}
        </span>
        {claimType && (
          <span className="px-2.5 py-0.5 bg-zinc-50 border border-zinc-200 text-[9px] font-mono font-bold uppercase tracking-wider text-zinc-400">
            {typeLabels[claimType] || claimType}
          </span>
        )}
      </div>

      {/* Claim text */}
      <h2 className="text-xl font-medium text-zinc-900 leading-relaxed mb-3">
        {claim.text}
      </h2>

      {/* Element summary */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="font-mono text-[10px] text-zinc-400">
          Elements {elements.length}
        </span>
        <span className="text-zinc-200">&middot;</span>
        <span className="font-mono text-[10px] text-zinc-400">
          Sources {evidenceCount}
        </span>
        {(stateCounts.supported > 0 || stateCounts.disputed > 0 || stateCounts.contextual > 0 || stateCounts.gap > 0) && (
          <>
            <span className="text-zinc-200">&middot;</span>
            {stateCounts.supported > 0 && (
              <span className={`font-mono text-[10px] ${ELEMENT_STATE.supported.text}`}>
                {stateCounts.supported} supported
              </span>
            )}
            {stateCounts.disputed > 0 && (
              <span className={`font-mono text-[10px] ${ELEMENT_STATE.disputed.text}`}>
                {stateCounts.disputed} disputed
              </span>
            )}
            {stateCounts.contextual > 0 && (
              <span className={`font-mono text-[10px] ${ELEMENT_STATE.contextual.text}`}>
                {stateCounts.contextual} contextual
              </span>
            )}
            {stateCounts.gap > 0 && (
              <span className="font-mono text-[10px] text-zinc-400">
                {stateCounts.gap} {stateCounts.gap === 1 ? 'gap' : 'gaps'}
              </span>
            )}
          </>
        )}
      </div>

      {/* Orientation line — Tru8's mechanically-derived honest read on element states */}
      {orientation && (
        <div className="mt-4">
          <DiagnosticFlag label="Orientation">{orientation}</DiagnosticFlag>
        </div>
      )}
    </div>
  );
}
