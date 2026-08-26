'use client';

import type { ComparisonBasis } from '@shared/types';

/**
 * What the model actually read for one side — the honesty seam of the tab.
 *
 * LOAD-BEARING, not decorative: measured on corpus URLs, ~38% of comparisons
 * run on the pipeline's stored text because the publisher blocks the fetch.
 * Without this line, a summary built from a snippet reads as a summary of the
 * article — the truncated-headline defect (2026-08-25) in a new coat.
 *
 * Same idiom as EvidenceQualityNote: grey only, mono 10px, △ glyph. Never a
 * warning colour — this describes OUR read, not the source's quality.
 */
interface TextBasisReceiptProps {
  basis: ComparisonBasis;
  words?: number | null;
}

export function TextBasisReceipt({ basis, words }: TextBasisReceiptProps) {
  const label =
    basis === 'full'
      ? `full article${words ? ` (${words.toLocaleString('en-GB')} words)` : ''}`
      : 'stored extract — the publisher blocked our fetch';

  return (
    <span className="inline-flex items-center gap-1.5 font-mono text-[10px] text-zinc-500">
      <span aria-hidden className="text-zinc-400">
        &#9651;
      </span>
      <span className="text-zinc-400 uppercase tracking-wider">Read</span>
      <span className="text-zinc-300">&middot;</span>
      <span>{label}</span>
    </span>
  );
}
