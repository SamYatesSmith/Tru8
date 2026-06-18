import Link from 'next/link';
import { ArrowRight } from 'lucide-react';

import { ScrollReveal } from './scroll-reveal';
import { SheetHeader } from './sheet-header';

/**
 * Homepage — Sheet 04, Compare teaser.
 *
 * Full-measure datasheet ledger (aligned to the document frame, like its peers).
 * Each row connects tool → return with a hairline leader so the full width is
 * filled deliberately. Rivals each return ONE terse thing; Tru8 is the emphasised
 * final row of the SAME ledger (accent rule, not a separate box) and shows visible
 * structure (the mono strip) — defusing the "you're just search" read. D15: "you
 * decide", never "your policy".
 */
const ROWS: ReadonlyArray<{ who: string; they: string }> = [
  { who: 'Search & grounding APIs', they: 'sources' },
  { who: 'Eval & guardrails', they: 'a score' },
  { who: 'Fact-checkers', they: 'a verdict' },
];

const RECORD_PARTS =
  'elements · supports / challenges / context · states · gaps · receipts · signed manifest';

export function StitchCompareTeaser() {
  return (
    <section className="py-24 md:py-32 bg-zinc-50 border-t border-zinc-100">
      <div className="max-w-7xl mx-auto px-6">
        <SheetHeader number="04" label="Compare" refText="THE RECORD LAYER" />
        <ScrollReveal>
          <div className="max-w-3xl mb-12 md:mb-14">
            <h2 className="text-3xl md:text-5xl font-normal tracking-[-0.02em] leading-[1.1]">
              <span className="text-zinc-400">Most tools hand you a conclusion.</span>
              <br />
              <span className="text-zinc-900">
                Tru8 hands you the evidence behind it.
              </span>
            </h2>
          </div>

          {/* Full-measure ledger — tool → leader → return */}
          <div className="border-t border-zinc-200">
            {ROWS.map((r) => (
              <div
                key={r.who}
                className="flex items-baseline justify-between gap-4 border-b border-zinc-200 py-5 sm:justify-start"
              >
                <span className="text-base md:text-xl text-zinc-900 shrink-0">
                  {r.who}
                </span>
                <span
                  aria-hidden="true"
                  className="hidden flex-1 translate-y-[-0.3em] border-b border-dotted border-zinc-300 sm:block"
                />
                <span className="font-mono text-xs md:text-sm uppercase tracking-wider text-zinc-400 shrink-0">
                  {r.they}
                </span>
              </div>
            ))}

            {/* Tru8 — the emphasised final row of the same ledger */}
            <div className="border-t-2 border-accent pt-6">
              <div className="flex items-baseline justify-between gap-4 sm:justify-start">
                <span className="text-xl md:text-3xl font-normal text-zinc-900 shrink-0">
                  Tru8
                </span>
                <span
                  aria-hidden="true"
                  className="hidden flex-1 translate-y-[-0.3em] border-b border-zinc-300 sm:block"
                />
                <span className="text-base md:text-xl text-zinc-900 shrink-0">
                  a structured evidence record — you decide.
                </span>
              </div>
              <p className="mt-3 font-mono text-[10px] md:text-[11px] tracking-wide text-zinc-400 break-words">
                {RECORD_PARTS}
              </p>
            </div>
          </div>

          <Link
            href="/compare"
            className="group inline-flex items-center gap-2 mt-10 font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-900 hover:text-accent transition-colors"
          >
            <span>See the full comparison</span>
            <ArrowRight
              size={14}
              className="transition-transform group-hover:translate-x-0.5"
            />
          </Link>
        </ScrollReveal>
      </div>
    </section>
  );
}
