'use client';

import { RelatedClaim } from '@shared/types';
import { ElementStateBadge } from '@/components/claim-map/element-state-badge';

interface RelatedClaimCardProps {
  claim: RelatedClaim;
}

const CLAIM_TYPE_LABELS: Record<string, string> = {
  empirical: 'Empirical',
  definitional: 'Definitional',
  causal_interpretive: 'Causal',
  predictive: 'Predictive',
  normative_flagged: 'Normative',
};

export function RelatedClaimCard({ claim }: RelatedClaimCardProps) {
  return (
    <div className="border border-zinc-200 p-5">
      {/* Claim text */}
      <p className="text-sm text-zinc-900 leading-relaxed mb-3">
        {claim.normalisedClaim}
      </p>

      {/* Claim type + consensus badge row */}
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        {claim.claimType && (
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400 border border-zinc-200 px-1.5 py-0.5">
            {CLAIM_TYPE_LABELS[claim.claimType] || claim.claimType}
          </span>
        )}
        {claim.consensus && (
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-400 border border-zinc-200 px-1.5 py-0.5">
            {claim.consensus.independentChecks} checks &middot; {claim.consensus.stability}
          </span>
        )}
      </div>

      {/* Elements list */}
      {claim.elements.length > 0 && (
        <div className="space-y-1.5 mb-3">
          {claim.elements.map((el, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <span className="font-mono text-[10px] text-zinc-300 font-bold shrink-0">
                {String(idx + 1).padStart(2, '0')}
              </span>
              {el.state && <ElementStateBadge state={el.state} size="sm" />}
              <span className="text-[12px] text-zinc-600 truncate">
                {el.description}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Entity overlap chips */}
      {claim.entityOverlap.length > 0 && (
        <div className="flex flex-wrap gap-1">
          <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-300 pt-0.5">
            Shared:
          </span>
          {claim.entityOverlap.map((entity) => (
            <span
              key={entity}
              className="font-mono text-[10px] text-zinc-500 bg-zinc-100 px-1.5 py-0.5"
            >
              {entity}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
