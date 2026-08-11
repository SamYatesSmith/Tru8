'use client';

import Link from 'next/link';
import { capture } from '@/lib/analytics';
import { SAMPLE_REPORT_PATH } from '@/lib/marketing';

/**
 * Homepage — closing CTA (C1 entry-point clarity, 2026-07-09).
 *
 * Lets a convinced visitor act without scrolling back up. Same single start
 * label as everywhere else ("Start a check") + the sample record as the
 * lower-commitment alternative. UK spelling; no verdict language.
 */
export function StitchClosingCta() {
  return (
    <section className="py-20 md:py-28 bg-white border-t border-zinc-100">
      <div className="max-w-7xl mx-auto px-6">
        <div className="max-w-2xl">
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-normal tracking-[-0.02em] text-zinc-900 mb-5 leading-[1.05]">
            See the record for <span className="font-bold">your claim.</span>
          </h2>
          <p className="text-sm md:text-base text-zinc-500 leading-relaxed max-w-xl mb-9">
            Paste a claim and read the evidence for and against — in your
            browser. We organise; you decide.
          </p>
          <div className="flex flex-col sm:flex-row sm:items-center gap-5">
            <Link
              href="/dashboard/new-check"
              onClick={() => capture('start_check_click', { surface: 'closing' })}
              className="group inline-flex items-center justify-center gap-4 bg-black text-white px-10 py-5 text-xs md:text-sm font-bold tracking-[0.3em] uppercase transition-all hover:bg-zinc-900 w-full sm:w-auto"
            >
              <span>Start a check</span>
              <span
                aria-hidden="true"
                className="w-2 h-2 bg-accent rotate-45 transition-transform group-hover:translate-x-1"
              />
            </Link>
            <a
              href={SAMPLE_REPORT_PATH}
              target="_blank"
              rel="noopener"
              onClick={() => capture('view_sample_click', { surface: 'closing' })}
              className="text-sm text-zinc-500 underline underline-offset-2 hover:text-zinc-900 transition-colors"
            >
              or see a sample record first
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
