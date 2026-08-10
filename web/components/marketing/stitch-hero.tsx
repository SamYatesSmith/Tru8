'use client';

import Link from 'next/link';
import { ArrowUpRight } from 'lucide-react';
import { capture } from '@/lib/analytics';
import { SAMPLE_REPORT_PATH } from '@/lib/marketing';

/**
 * Stitch Hero — human-first (C1 entry-point clarity, 2026-07-09).
 *
 * The best message+action moment on the site (formerly stranded on /research)
 * is now the front door: "See the evidence for and against. Show your working."
 * Primary CTA = "Start a check" (the single start label sitewide) →
 * /dashboard/new-check; middleware bounces a signed-out visitor into the auth
 * modal with a redirect back to that same path. Secondary = a real public
 * sample record (proof, not pictures).
 *
 * 2026-08-10 — this pointed at /dashboard, the ACCOUNT OVERVIEW, not the check
 * form. A signed-in visitor clicking "Start a check" landed on usage cards and
 * recent-checks history with no form in sight, which reads as a dead button.
 * Signed-out was worse: they signed in and arrived at the same wrong page.
 * Every CTA that promises a check now targets the form; links that say
 * "Dashboard" still say /dashboard.
 *
 * 2026-08-07 — the illustrative record fragment that stood in the right column
 * was REPLACED by the mark at hero scale (founder call). The §2.2 state-colour
 * and manifest-footer locks were about that panel and no longer have anything
 * to bind; they still apply anywhere the record shape is shown. Proof did not
 * leave the hero — the secondary CTA is still a real public record.
 *
 * Locks that DO still apply here: no "policy" (D15), UK spelling (D13),
 * accent lives only in the marks.
 */

export function StitchHero() {
  return (
    <section className="relative pt-24 pb-16 md:pt-28 md:pb-24 bg-grid-dot overflow-hidden border-b border-zinc-100">
      <div className="max-w-7xl mx-auto px-5 md:px-6 relative z-10">
        {/* The mark stands beside the WHOLE hero block, not just the copy below
            the headline. When it flanked only the lower half (2026-08-07), its
            420px set a grid row the left column could not fill, and the surplus
            read as ~250px of dead white. Both columns now share one centred
            row, so the taller of the two defines the height and the other
            centres against it — no gap can open under either. */}
        <div className="lg:grid lg:grid-cols-12 lg:gap-10 xl:gap-14 lg:items-center">
          {/* Left — the argument + actions */}
          <div className="lg:col-span-8">
            {/* Category eyebrow (zinc — accent lives only in the marks) */}
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-500 mb-5 md:mb-6">
              Evidence research — not fact-checking
            </div>

            {/* Statement. Founder-chosen 2026-07-09: the whole positioning in
                three words. Wraps to two lines inside the column, which is why
                leading is tight. */}
            <h1 className="text-4xl sm:text-6xl md:text-7xl lg:text-[80px] xl:text-[92px] font-normal tracking-[-0.03em] text-zinc-900 leading-[0.95] mb-8 md:mb-10">
              Evidence, <span className="font-bold">not verdicts.</span>
            </h1>
            <p className="text-sm md:text-base lg:text-lg text-zinc-500 mb-4 max-w-2xl leading-relaxed">
              Paste a claim, a question, or an article. Tru8 breaks it into its
              checkable parts, gathers evidence from published sources, and
              returns a signed, organised evidence record.
            </p>
            <p className="text-sm md:text-base text-zinc-900 mb-8 md:mb-10">
              We organise; you decide.
            </p>

            <div className="flex flex-col sm:flex-row sm:items-stretch gap-4">
              <Link
                href="/dashboard/new-check"
                onClick={() => capture('start_check_click', { surface: 'hero' })}
                className="group inline-flex items-center justify-center gap-4 bg-black text-white px-8 py-4 md:px-12 md:py-6 text-xs md:text-sm font-bold tracking-[0.3em] uppercase w-full sm:w-auto transition-all hover:bg-zinc-900"
              >
                <span>Start a check</span>
                {/* Orange diamond signature — decorative, inside the button bounds */}
                <span
                  aria-hidden="true"
                  className="w-2 h-2 bg-accent rotate-45 transition-transform group-hover:translate-x-1"
                />
              </Link>
              <a
                href={SAMPLE_REPORT_PATH}
                target="_blank"
                rel="noopener"
                onClick={() => capture('view_sample_click', { surface: 'hero' })}
                className="group inline-flex items-center justify-center gap-2 border border-zinc-200 px-8 py-4 md:px-10 md:py-6 text-xs md:text-sm font-bold tracking-[0.3em] uppercase text-zinc-900 w-full sm:w-auto transition-colors hover:border-zinc-900"
              >
                <span>See a sample record</span>
                <ArrowUpRight size={14} className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
              </a>
            </div>

            {/* Reassurance microline — facts only */}
            <p className="mt-7 md:mt-8 font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-400">
              Free to try · a record in ~90 seconds · no API needed
            </p>
          </div>

          {/* Right — the mark (lg+ only). Generated art: `design/mobius-mark/`,
              emitted by build_assets.py. Decorative — the h1 carries the
              meaning — so alt="" and hidden from assistive tech.
              Sized by HEIGHT because the mark is 1 wide : 2.15 high; at the
              column's full width it would run past 1000px tall. The heights
              here are tuned to sit just above the left column's own height at
              each breakpoint, so the mark leads the composition without
              stretching the row. */}
          <div className="hidden lg:col-span-4 lg:flex lg:justify-center lg:items-center">
            {/* eslint-disable-next-line @next/next/no-img-element -- generated
                SVG art; next/image would neither optimise nor resize it. */}
            <img
              src="/brand/tru8-hero.svg"
              alt=""
              aria-hidden="true"
              draggable={false}
              className="h-[380px] xl:h-[440px] w-auto motion-reduce:hidden"
            />
            {/* eslint-disable-next-line @next/next/no-img-element -- see above */}
            <img
              src="/brand/tru8-hero-static.svg"
              alt=""
              aria-hidden="true"
              draggable={false}
              className="hidden h-[380px] xl:h-[440px] w-auto motion-reduce:block"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
