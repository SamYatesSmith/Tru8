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
 * Primary CTA = "Start a check" (the single start label sitewide) → /dashboard;
 * middleware bounces a signed-out visitor into the auth modal with a redirect
 * back. Secondary = a real public sample record (proof, not pictures).
 *
 * Locks: panel is illustrative (`sample`) and ALL-NEUTRAL mono — never a green
 * verdict (§2.2 state-colour lock). Manifest footer is a capability line, not a
 * live /verify link. No "policy" (D15). UK spelling (D13, updated 2026-06-29).
 */

// Illustrative record fragment — same field shapes as the real _meta/claimMap.
const RECORD_LINES: ReadonlyArray<{ k: string; v: string }> = [
  { k: 'claim', v: '"UK inflation fell to 2.3% in April"' },
  { k: 'elements', v: '3 examined' },
  { k: 'evidence', v: '17 sources · 4 tiers' },
  { k: 'mapped', v: '9 support · 3 challenge · 5 context' },
  { k: 'gaps', v: '2 named' },
  { k: 'excluded', v: '6 — receipts attached' },
];

export function StitchHero() {
  return (
    <section className="relative pt-24 pb-16 md:pt-32 md:pb-40 bg-grid-dot overflow-hidden border-b border-zinc-100">
      <div className="max-w-7xl mx-auto px-5 md:px-6 relative z-10">
        {/* Category eyebrow (zinc — accent lives only in the marks) */}
        <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-500 mb-5 md:mb-6">
          Evidence research — not fact-checking
        </div>

        {/* Statement — full measure. Founder-chosen 2026-07-09: the whole
            positioning in three words. */}
        <h1 className="max-w-5xl text-4xl sm:text-6xl md:text-7xl lg:text-[92px] font-normal tracking-[-0.03em] text-zinc-900 leading-[0.95] mb-10 md:mb-14">
          Evidence, <span className="font-bold">not verdicts.</span>
        </h1>

        {/* Asymmetric split — supporting copy left, proof panel right */}
        <div className="lg:grid lg:grid-cols-12 lg:gap-12 lg:items-start">
          {/* Left — the argument + actions */}
          <div className="lg:col-span-7">
            <p className="text-sm md:text-base lg:text-lg text-zinc-500 mb-4 max-w-2xl leading-relaxed">
              Paste a claim, a question, or an article. Tru8 breaks it into its
              checkable parts, gathers evidence from 30+ published sources, and
              returns a signed, organised evidence record.
            </p>
            <p className="text-sm md:text-base text-zinc-900 mb-8 md:mb-10">
              We organise; you decide.
            </p>

            <div className="flex flex-col sm:flex-row sm:items-stretch gap-4">
              <Link
                href="/dashboard"
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

          {/* Right — illustrative record fragment (fills the void, lg+ only) */}
          <div className="hidden lg:col-span-5 lg:block">
            <div className="border border-zinc-200 bg-white overflow-hidden">
              <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-2.5">
                <span className="font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-500">
                  Record
                </span>
                <span className="font-mono text-[10px] text-zinc-400">chk_8f3a · sample</span>
              </div>
              <div className="px-4 py-4 space-y-2.5">
                {RECORD_LINES.map((line) => (
                  <div key={line.k} className="flex gap-3 font-mono text-[11px] leading-relaxed">
                    <span className="w-16 shrink-0 text-zinc-400">{line.k}</span>
                    <span className="text-zinc-900 break-words">{line.v}</span>
                  </div>
                ))}
              </div>
              <div className="flex items-center gap-2 border-t border-zinc-200 px-4 py-3">
                <span aria-hidden="true" className="w-2 h-2 bg-accent rotate-45 shrink-0" />
                <span className="font-mono text-[10px] text-zinc-900">_manifest</span>
                <span className="font-mono text-[10px] text-zinc-400">hmac-sha256 · signed</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
