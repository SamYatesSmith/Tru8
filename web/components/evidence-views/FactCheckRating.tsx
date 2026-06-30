'use client';

import type { Evidence } from '@shared/types';

/**
 * Attributed fact-check rating line for a source card.
 *
 * Shows a named publisher's rating (e.g. PolitiFact — "False") ONLY for a
 * fact-check the backend confirmed is about this claim. It is the PUBLISHER's
 * assessment, never Tru8's verdict — so it's explicitly attributed ("their
 * assessment") and grey (no green/red). Renders nothing for non-fact-checks
 * or unconfirmed ones (the API omits the fields).
 */
interface FactCheckRatingProps {
  evidence: Evidence;
}

export function FactCheckRating({ evidence }: FactCheckRatingProps) {
  if (!evidence.isFactcheck || !evidence.factcheckPublisher || !evidence.factcheckRating) {
    return null;
  }

  return (
    <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-0.5 font-mono text-[10px] text-zinc-500">
      <span className="text-zinc-400 uppercase tracking-wider">Fact-check</span>
      <span className="text-zinc-300">&middot;</span>
      <span>
        <span className="text-zinc-700">{evidence.factcheckPublisher}</span> rated this:{' '}
        &ldquo;{evidence.factcheckRating}&rdquo;
      </span>
      <span className="text-zinc-300">&middot;</span>
      <span className="italic text-zinc-400">their assessment</span>
      {evidence.url && (
        <a
          href={evidence.url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="text-zinc-500 hover:text-zinc-800 transition-colors"
        >
          view review &rarr;
        </a>
      )}
    </div>
  );
}
