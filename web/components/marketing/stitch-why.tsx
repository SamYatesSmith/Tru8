import Link from 'next/link';
import { ArrowRight } from 'lucide-react';

import { ScrollReveal } from './scroll-reveal';
import { SheetHeader } from './sheet-header';

/**
 * Homepage — Sheet 00, Why Tru8 exists (C1 entry-point clarity, 2026-07-09).
 *
 * Merges the former StitchProblem + StitchCompareTeaser: "most tools hand you
 * a conclusion" IS the reason Tru8 exists, so the problem statement and the
 * tool→return ledger are one section, said once. Headline left, ledger right.
 * D15: "you decide", never "your policy". UK spelling (D13, 2026-06-29).
 */
const ROWS: ReadonlyArray<{ who: string; they: string }> = [
  { who: 'Search & grounding APIs', they: 'a list of sources' },
  { who: 'Evals & guardrails', they: 'a score' },
  { who: 'Fact-checkers', they: 'a verdict' },
];

const RECORD_PARTS =
  'elements · supports / challenges / context · states · gaps · receipts · signed manifest';

export function StitchWhy() {
  return (
    <section className="py-20 md:py-28 bg-white border-t border-zinc-100">
      <div className="max-w-7xl mx-auto px-6">
        <SheetHeader number="00" label="Why Tru8 exists" refText="THE GAP" />
        <ScrollReveal>
          <div className="lg:grid lg:grid-cols-2 lg:gap-16 lg:items-start">
            {/* Left — the problem, stated once */}
            <div className="mb-12 lg:mb-0">
              <h2 className="text-3xl md:text-5xl font-normal tracking-[-0.02em] leading-[1.08]">
                <span className="text-zinc-900">Most tools hand you </span>
                <span className="font-bold text-zinc-900">a conclusion.</span>
              </h2>
              <p className="text-base md:text-lg text-zinc-500 leading-relaxed mt-7 max-w-xl">
                Claims move faster than anyone can assemble the evidence behind
                them &mdash; and every tool answers with a verdict, a score, or a
                pile of links. If your work has to stand up to scrutiny, none of
                those is the working.
              </p>
            </div>

            {/* Right — the tool → return ledger, Tru8 as the emphasised final row */}
            <div>
              <div className="border-t border-zinc-200">
                {ROWS.map((r) => (
                  <div
                    key={r.who}
                    className="flex items-baseline justify-between gap-4 border-b border-zinc-200 py-5 sm:justify-start"
                  >
                    <span className="text-base md:text-lg text-zinc-900 shrink-0">
                      {r.who}
                    </span>
                    <span
                      aria-hidden="true"
                      className="hidden flex-1 translate-y-[-0.3em] border-b border-dotted border-zinc-300 sm:block"
                    />
                    <span className="font-mono text-xs uppercase tracking-wider text-zinc-400 shrink-0">
                      {r.they}
                    </span>
                  </div>
                ))}

                <div className="border-t-2 border-accent pt-6">
                  <div className="flex items-baseline justify-between gap-4 sm:justify-start">
                    <span className="text-xl md:text-2xl font-normal text-zinc-900 shrink-0">
                      Tru8
                    </span>
                    <span
                      aria-hidden="true"
                      className="hidden flex-1 translate-y-[-0.3em] border-b border-zinc-300 sm:block"
                    />
                    <span className="text-base md:text-lg text-zinc-900 shrink-0">
                      the evidence record &mdash; you decide.
                    </span>
                  </div>
                  <p className="mt-3 font-mono text-[10px] md:text-[11px] tracking-wide text-zinc-400 break-words">
                    {RECORD_PARTS}
                  </p>
                </div>
              </div>

              <Link
                href="/compare"
                className="group inline-flex items-center gap-2 mt-8 font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-900 hover:text-accent transition-colors"
              >
                <span>See the full comparison</span>
                <ArrowRight
                  size={14}
                  className="transition-transform group-hover:translate-x-0.5"
                />
              </Link>
            </div>
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
}
