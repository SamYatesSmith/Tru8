import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';

import { Navigation } from '@/components/layout/navigation';
import { MobileNav } from '@/components/layout/mobile-nav';
import { Footer } from '@/components/layout/footer';
import { StitchFeatures } from '@/components/marketing/stitch-features';
import { StitchCompareTeaser } from '@/components/marketing/stitch-compare-teaser';
import { ResearchStartCta } from '@/components/marketing/research-start-cta';

const PAGE_TITLE = 'Research the evidence for and against — Tru8 Research Console';
const PAGE_DESCRIPTION =
  'See the evidence for and against any claim — and show your working. Tru8 organises external published sources into a structured, inspectable record: what supports each claim, what challenges it, and what is missing. No verdict — you decide. We organise; you decide.';

export const metadata: Metadata = {
  title: PAGE_TITLE,
  description: PAGE_DESCRIPTION,
  alternates: { canonical: '/research' },
  // Page-specific social card (mirrors /compare); without this the route falls
  // back to the generic root OG copy instead of the researcher pitch. Reuses the
  // default OG image — no researcher-specific /api/og route exists yet.
  openGraph: {
    title: PAGE_TITLE,
    description: PAGE_DESCRIPTION,
    images: ['/api/og/default'],
  },
  twitter: {
    card: 'summary_large_image',
    title: PAGE_TITLE,
    description: PAGE_DESCRIPTION,
    images: ['/api/og/default'],
  },
};

/**
 * /research — the researcher-led pitch (item 2, 2026-06-23 release plan).
 *
 * Buyer = the "show-your-working" researcher (journalists, analysts, policy /
 * comms researchers, serious independent writers) who must SEE the evidence for
 * and against a claim and DEFEND their sourcing. For them, no-verdict is the
 * feature. Console-primary (CTA → /dashboard); the API stays a quiet footnote.
 *
 * Shipped as a reversible variant: `/` stays developer-led and is untouched,
 * so this is a single-commit rollback. Funnel measured via research_app_click
 * (nav) → research_start_click (here) before any flip of `/`.
 *
 * Language lock: object is always the evidence/record, never a verdict on the
 * claim; no "policy" noun; "evidence" scoped at first use; US spelling; Stitch
 * tokens only; no verdict colours; no price (gated — see project-pricing-not-set).
 */

const WORKING = [
  {
    label: 'For',
    head: 'What supports each claim',
    body: 'External published sources that back it, each classified by tier and type — so you can weigh primary data against reporting and commentary, not take one link on trust.',
  },
  {
    label: 'Against',
    head: 'What challenges it',
    body: 'The sources that complicate or contradict the claim, surfaced beside the support — not buried, and never flattened into a single number.',
  },
  {
    label: 'Missing',
    head: "What isn't there",
    body: 'Named gaps, and an exclusion receipt for every source set aside — what could not be substantiated, and why. Your working, written down and defensible.',
  },
];

const LIMITS = [
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

export default function ResearchPage() {
  return (
    <>
      <Navigation />
      <MobileNav />

      <main id="main-content" className="relative">
        {/* Hero — researcher-led: for-and-against + show your working */}
        <section className="pt-24 pb-16 md:pt-40 md:pb-24 bg-grid-dot border-b border-zinc-100">
          <div className="max-w-7xl mx-auto px-6">
            <div className="max-w-3xl">
              <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-6">
                Tru8 Research Console
              </div>
              <h1 className="text-3xl sm:text-5xl md:text-7xl font-normal tracking-[-0.03em] text-zinc-900 leading-[0.95] mb-6">
                See the evidence for and against.
                <br />
                <span className="font-bold">Show your working.</span>
              </h1>
              <p className="text-sm md:text-lg text-zinc-500 leading-relaxed max-w-xl mb-8">
                For researchers, journalists, and analysts who have to defend their
                sources. Paste a headline, article, or claim. Tru8 retrieves external
                published sources — official data, research, legislation, and reporting —
                classifies each by tier and type, and maps what supports each claim, what
                challenges it, and what is missing. You read the record and decide. We
                organise; you decide.
              </p>
              <ResearchStartCta surface="research_hero" />
            </div>
          </div>
        </section>

        {/* What the record shows — for / against / missing made concrete */}
        <section className="py-20 md:py-28 border-b border-zinc-100">
          <div className="max-w-7xl mx-auto px-6">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4">
              What the record shows
            </div>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-normal tracking-[-0.02em] text-zinc-900 mb-12 max-w-3xl">
              For, against, and what&apos;s missing —{' '}
              <span className="font-bold">every claim, every time.</span>
            </h2>
            <div className="grid gap-px bg-zinc-200 border border-zinc-200 sm:grid-cols-3">
              {WORKING.map((w) => (
                <div key={w.label} className="bg-white p-6 md:p-8">
                  <div className="flex items-center gap-2 mb-4">
                    <span aria-hidden="true" className="h-2 w-2 rotate-45 bg-accent" />
                    <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-900">
                      {w.label}
                    </span>
                  </div>
                  <h3 className="text-base md:text-lg font-bold text-zinc-900 mb-3">
                    {w.head}
                  </h3>
                  <p className="text-sm text-zinc-500 leading-relaxed">{w.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Contrast vs verdict tools — reuse the homepage compare ledger */}
        <StitchCompareTeaser />

        {/* Six ways to read the same record */}
        <StitchFeatures />

        {/* Limitations — an honest record has edges */}
        <section className="py-20 md:py-28 border-t border-zinc-100">
          <div className="max-w-7xl mx-auto px-6">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4">
              Limitations
            </div>
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
          </div>
        </section>

        {/* Closing CTA — let a convinced researcher act without scrolling back up */}
        <section className="py-16 md:py-24 border-t border-zinc-100">
          <div className="max-w-7xl mx-auto px-6">
            <div className="max-w-2xl">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-normal tracking-[-0.02em] text-zinc-900 mb-5">
                See the record for <span className="font-bold">your</span> claim.
              </h2>
              <p className="text-sm md:text-base text-zinc-500 leading-relaxed max-w-xl mb-8">
                Paste a headline, article, or claim and read the evidence for and against
                — in your browser. We organise; you decide.
              </p>
              <ResearchStartCta surface="research_footer" />
            </div>
          </div>
        </section>

        {/* Quiet API footnote — keep the developer path alive, not prominent */}
        <section className="py-12 border-t border-zinc-100 bg-zinc-50">
          <div className="max-w-7xl mx-auto px-6">
            <p className="font-mono text-[11px] tracking-wide text-zinc-400">
              Automating this in a pipeline? Tru8 also ships as an API and MCP server.{' '}
              <Link
                href="/developers"
                className="group inline-flex items-center gap-1 text-zinc-600 hover:text-accent transition-colors"
              >
                <span>For developers</span>
                <ArrowRight
                  size={12}
                  className="transition-transform group-hover:translate-x-0.5"
                />
              </Link>
            </p>
          </div>
        </section>
      </main>

      <Footer />
    </>
  );
}
