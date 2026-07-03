'use client';

import type { Evidence } from '@shared/types';
import {
  DATE_HINT_TEXT,
  DATE_HINT_TOOLTIP,
  isSuspectDate,
} from '@/lib/evidence-date';

/**
 * Grey provenance hint rendered beside a suspect published date (F2).
 * Neutral styling only — provenance is information, not a verdict.
 * Renders nothing for confirmed/engine/API dates.
 */
export function DateHint({
  evidence,
}: {
  evidence: Pick<Evidence, 'dateBasis'>;
}) {
  if (!isSuspectDate(evidence)) return null;
  return (
    <span className="italic text-zinc-400" title={DATE_HINT_TOOLTIP}>
      {' '}
      &middot; {DATE_HINT_TEXT}
    </span>
  );
}
