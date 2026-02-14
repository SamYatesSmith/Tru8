'use client';

import type { Claim } from '@shared/types';
import { ClaimTypeBadge } from './claim-type-badge';
import { ElementList } from './element-list';
import { OrientationLine } from './orientation-line';

interface ClaimMapViewProps {
  claim: Claim;
}

export function ClaimMapView({ claim }: ClaimMapViewProps) {
  if (!claim.claimMap) {
    return (
      <div className="border border-zinc-200 p-6 text-sm text-zinc-400">
        No claim map available
      </div>
    );
  }

  const { claimType, normalisedClaim, elements, orientation } = claim.claimMap;

  return (
    <div className="border border-zinc-200 p-6 space-y-4">
      <ClaimTypeBadge claimType={claimType} />

      <p className="text-base font-medium text-zinc-800">{normalisedClaim}</p>

      <hr className="border-zinc-200" />

      <ElementList elements={elements} />

      <hr className="border-zinc-200" />

      <OrientationLine orientation={orientation} />
    </div>
  );
}
