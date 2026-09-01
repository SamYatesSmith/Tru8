import { ScrollReveal } from './scroll-reveal';
import { SheetHeader } from './sheet-header';

/**
 * Homepage — Sheet 03, Edges (C1 entry-point clarity, 2026-07-09; renumbered
 * 2026-09-01 when Sheets 00+01 folded and How-it-works was removed).
 *
 * 2026-09-01: "Not a verdict." left this list — the headline says it, FAQ Q2
 * says it, and a third telling was noise. In its place, the edge the claim
 * field newly implies away: a check is not instant. "Under a minute" is the
 * ONE timing phrase sitewide (founder: 30–60 s measured); never a number here.
 *
 * The honest-limitations section, ported home from the retired /research page
 * (301 → / since C1 S2; its copy was already locked there). Trust-builder: an
 * evidence platform that names its own edges. No verdict language; UK spelling.
 */
const LIMITS: ReadonlyArray<{ head: string; body: string }> = [
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
  {
    head: 'Under a minute — not instant.',
    body: 'A check runs a live search and reads every source it keeps, so it takes tens of seconds rather than milliseconds. You get a permanent link to the record when it is done.',
  },
];

export function StitchEdges() {
  return (
    <section className="pt-0 pb-24 md:pb-32 bg-white">
      <div className="max-w-7xl mx-auto px-6">
        <SheetHeader number="03" label="Edges" refText="STATED, NOT HIDDEN" />
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
