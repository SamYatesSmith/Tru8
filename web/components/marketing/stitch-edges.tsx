import { ScrollReveal } from './scroll-reveal';
import { SheetHeader } from './sheet-header';

/**
 * Homepage — Sheet 04, Edges (C1 entry-point clarity, 2026-07-09).
 *
 * The honest-limitations section, ported home from /research (which retires in
 * C1 slice S2 — its copy was already locked there). Trust-builder: an evidence
 * platform that names its own edges. No verdict language; UK spelling.
 */
const LIMITS: ReadonlyArray<{ head: string; body: string }> = [
  {
    head: 'Not a verdict.',
    body: 'Tru8 organises the evidence and shows how it relates to each claim. It does not score truth or tell you what to conclude — you read the record and decide.',
  },
  {
    head: "Bounded by what's public.",
    body: 'Evidence comes from external published sources — official data, research, legislation, and reporting — not private records, leaks, or primary fieldwork.',
  },
  {
    head: 'Best on a focused set of claims.',
    body: 'Depth per claim beats breadth. A handful of claims gets the fullest record; very long inputs are decomposed and ranked.',
  },
  {
    head: 'A snapshot in time.',
    body: 'The record reflects what was retrievable when you ran it. Re-running later can surface sources that did not exist before.',
  },
];

export function StitchEdges() {
  return (
    <section className="py-20 md:py-28 bg-zinc-50 border-t border-zinc-100">
      <div className="max-w-7xl mx-auto px-6">
        <SheetHeader number="04" label="Edges" refText="STATED, NOT HIDDEN" />
        <ScrollReveal>
          <h2 className="text-2xl sm:text-3xl md:text-4xl font-normal tracking-[-0.02em] text-zinc-900 mb-12 max-w-3xl">
            An honest record has <span className="font-bold">edges.</span>
          </h2>
          <div className="grid gap-x-12 gap-y-8 sm:grid-cols-2 max-w-4xl">
            {LIMITS.map((l) => (
              <div key={l.head} className="border-l-2 border-zinc-200 pl-5">
                <h3 className="text-sm font-bold text-zinc-900 mb-2">{l.head}</h3>
                <p className="text-sm text-zinc-500 leading-relaxed">{l.body}</p>
              </div>
            ))}
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
}
