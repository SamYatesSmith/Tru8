'use client';

import type { Comparison } from '@shared/types';
import { CollisionTable } from './CollisionTable';
import { TextBasisReceipt } from './TextBasisReceipt';

/**
 * The three prose fields + the mechanical collision table.
 *
 * The scoping line under the summaries is NON-NEGOTIABLE (design §1.1): we
 * compare positions, not articles — without it we print a partial
 * characterisation of a piece under its publisher's name.
 *
 * The prose came from one model call that read both texts; the table came
 * from code reading evidence_refs. Never blur that line.
 */
interface ComparisonResultProps {
  comparison: Comparison;
  domainA: string;
  domainB: string;
  urlA?: string;
  urlB?: string;
  elementDescriptions?: Map<string, string>;
}

function Divider({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <div className="flex-1 h-px bg-zinc-200" />
      <span className="font-mono text-[10px] font-bold uppercase tracking-[0.25em] text-zinc-500">
        {label}
      </span>
      <div className="flex-1 h-px bg-zinc-200" />
    </div>
  );
}

function SummaryColumn({
  side,
  domain,
  url,
  text,
  basis,
  words,
}: {
  side: 'A' | 'B';
  domain: string;
  url?: string;
  text: string;
  basis: Comparison['basisA'];
  words?: number | null;
}) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <span className="font-mono text-[10px] font-bold uppercase tracking-widest text-zinc-500">
          {side} &middot; {domain}
        </span>
        {url && (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:text-zinc-900 transition-colors"
          >
            Visit &rarr;
          </a>
        )}
      </div>
      <p className="text-sm text-zinc-700 leading-relaxed mb-2">{text}</p>
      <TextBasisReceipt basis={basis} words={words} />
    </div>
  );
}

export function ComparisonResult({
  comparison,
  domainA,
  domainB,
  urlA,
  urlB,
  elementDescriptions,
}: ComparisonResultProps) {
  return (
    <div aria-live="polite">
      <Divider label="What each says here" />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-3">
        <SummaryColumn
          side="A"
          domain={domainA}
          url={urlA}
          text={comparison.summaryA}
          basis={comparison.basisA}
          words={comparison.wordsA}
        />
        <SummaryColumn
          side="B"
          domain={domainB}
          url={urlB}
          text={comparison.summaryB}
          basis={comparison.basisB}
          words={comparison.wordsB}
        />
      </div>

      {/* Non-negotiable scoping line (design §1.1). */}
      <p className="text-[11px] text-zinc-400 mb-8">
        Compared on the questions in this claim, not on the articles as a whole.
      </p>

      <Divider label="Where they diverge" />
      <p className="text-sm text-zinc-700 leading-relaxed mb-6">
        {comparison.divergence}
      </p>

      <CollisionTable
        rows={comparison.collisions}
        descriptions={elementDescriptions}
        domainA={domainA}
        domainB={domainB}
      />
    </div>
  );
}
