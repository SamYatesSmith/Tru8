'use client';

import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { capture } from '@/lib/analytics';

/**
 * Stitch Hero — verification/dev-led, Phase 2 art-direction.
 *
 * 84px headline full-width across the top; below it an asymmetric 7/5 split —
 * the tight sub + tagline + CTAs (left) and a light "record-fragment" proof panel
 * (right, lg+ only) that fills the former grid-dot void with product proof.
 *
 * Locks: panel is illustrative (`sample`) and ALL-NEUTRAL mono — "supported" is a
 * plain zinc token, never a green verdict (§2.2 state-colour lock). Manifest footer
 * is a capability line, not a live /verify link. No "policy" (D15). Eyebrow zinc-400
 * (accent only in the CTA square + the manifest seal). US spelling (D13).
 */

// Illustrative record fragment — same field shapes as the real _meta/claimMap.
const RECORD_LINES: ReadonlyArray<{ k: string; v: string }> = [
  { k: 'claim', v: '"global avg temp rose 1.1°C…"' },
  { k: 'element', v: '1.1°C rise — supported' },
  { k: 'evidence', v: '6 support · 1 challenge' },
  { k: 'sources', v: '18 domains · 3 tiers' },
  { k: 'gap', v: 'no_academic_sources' },
];

export function StitchHero() {
  return (
    <section className="relative pt-24 pb-16 md:pt-32 md:pb-40 bg-grid-dot overflow-hidden border-b border-zinc-100">
      <div className="max-w-7xl mx-auto px-5 md:px-6 relative z-10">
        {/* Category eyebrow (zinc-400 — accent lives only in the marks) */}
        <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-500 mb-5 md:mb-6">
          Evidence Research Infrastructure
        </div>

        {/* Statement — full measure */}
        <h1 className="max-w-5xl text-3xl sm:text-5xl md:text-7xl lg:text-[84px] font-normal tracking-[-0.03em] text-zinc-900 leading-[0.95] mb-10 md:mb-14">
          The evidence behind every factual claim &mdash;
          <br />
          <span className="font-bold">before it ships.</span>
        </h1>

        {/* Asymmetric split — supporting copy left, proof panel right */}
        <div className="lg:grid lg:grid-cols-12 lg:gap-12 lg:items-start">
          {/* Left — the argument + actions */}
          <div className="lg:col-span-7">
            <p className="text-sm md:text-base lg:text-lg text-zinc-500 mb-4 max-w-2xl leading-relaxed">
              Tru8 decomposes AI-generated content into checkable claims and returns a
              structured evidence record &mdash; what supports each, what challenges it,
              what&rsquo;s missing. You decide what to publish, escalate, re-check or block.
            </p>
            <p className="text-sm md:text-base text-zinc-900 mb-8 md:mb-10">
              We organize; you decide.
            </p>

            <div className="flex flex-col sm:flex-row sm:items-stretch gap-4">
              <Link
                href="/developers"
                onClick={() => capture('get_api_key_click', { surface: 'hero' })}
                className="group inline-flex items-center justify-center gap-4 bg-black text-white px-8 py-4 md:px-12 md:py-6 text-xs md:text-sm font-bold tracking-[0.3em] uppercase w-full sm:w-auto transition-all hover:bg-zinc-900"
              >
                <span>Get API Key</span>
                {/* Orange diamond signature — decorative, inside the button bounds */}
                <span
                  aria-hidden="true"
                  className="w-2 h-2 bg-accent rotate-45 transition-transform group-hover:translate-x-1"
                />
              </Link>
              <a
                href="#preview"
                className="group inline-flex items-center justify-center gap-2 border border-zinc-200 px-8 py-4 md:px-10 md:py-6 text-xs md:text-sm font-bold tracking-[0.3em] uppercase text-zinc-900 w-full sm:w-auto transition-colors hover:border-zinc-900"
              >
                <span>See a Sample</span>
                <ArrowRight size={14} className="transition-transform group-hover:translate-x-0.5" />
              </a>
            </div>

            {/* Quiet human path — the secondary audience, never a splash */}
            <p className="mt-7 md:mt-8 text-xs md:text-sm text-zinc-500 max-w-xl leading-relaxed">
              Need the human review console?{' '}
              <Link
                href="/research"
                onClick={() => capture('research_app_click', { surface: 'hero' })}
                className="underline underline-offset-2 hover:text-zinc-900 transition-colors"
              >
                Open the Research App
              </Link>
              .
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
