import type { CitedSourceGap } from '@shared/types';

interface CitedSourceGapsProps {
  gaps: CitedSourceGap[];
}

/**
 * Cited-source gap note (Build B, audit/2026-10-05_cited_source_lane_design.md
 * §§11.8, 12.6, 17). Sources in the record attribute the claim to an original
 * that is not itself in the record. Name and cue are verbatim page text,
 * never model prose. Says "not in this record", never "searched and not
 * found": with the lane off, nothing was searched. Neutral styling — a gap,
 * not a verdict. Wraps at phone width; nothing is truncated or hover-only.
 */
export function CitedSourceGaps({ gaps }: CitedSourceGapsProps) {
  if (gaps.length === 0) return null;
  return (
    <section className="space-y-3" aria-label="Cited but not in this record">
      <p className="font-mono text-[10px] font-bold uppercase tracking-widest text-zinc-500">
        Cited but not in this record
      </p>
      <ul className="space-y-2">
        {gaps.map((gap) => (
          <li
            key={gap.name}
            data-testid="cited-source-gap"
            className="border-l-4 border-l-zinc-300 border border-dashed border-zinc-300 px-4 py-3 text-sm text-zinc-700 leading-relaxed break-words"
          >
            Sources here attribute this to{' '}
            <span className="font-medium text-zinc-900">{gap.name}</span> (&quot;{gap.cue}&quot;); that
            source is not in this record.
          </li>
        ))}
      </ul>
    </section>
  );
}

const COUNT_WORDS = ['no', 'one', 'two', 'three', 'four', 'five'];

/** "one cited original is" / "two cited originals are" — for the all-covered line. */
export function citedOriginalsPhrase(n: number): string {
  const count = COUNT_WORDS[n] ?? String(n);
  return n === 1 ? `${count} cited original is` : `${count} cited originals are`;
}
