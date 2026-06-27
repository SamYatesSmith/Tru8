import { Navigation } from '@/components/layout/navigation';
import { MobileBottomNav } from '@/components/layout/mobile-bottom-nav';
import { Footer } from '@/components/layout/footer';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import Link from 'next/link';
import { ComparisonTable } from './comparison-table';
import { ResponseTabs } from './response-tabs';
import { CHECK_ID } from './demo-data';

const PAGE_TITLE = 'Tru8 vs four grounding APIs — same claim, verbatim responses';
const PAGE_DESCRIPTION =
  'The same claim through Tru8 vs four grounding APIs — Web IQ, Google check-grounding, Perplexity, Parallel — responses verbatim. Tier and type classification, supports/challenges relationships, dispute states, named gaps, receipts, signed manifest.';

export const metadata = {
  title: PAGE_TITLE,
  description: PAGE_DESCRIPTION,
  alternates: { canonical: '/compare' },
  openGraph: {
    title: PAGE_TITLE,
    description: PAGE_DESCRIPTION,
    images: ['/api/og/compare'],
  },
  twitter: {
    card: 'summary_large_image',
    title: PAGE_TITLE,
    description: PAGE_DESCRIPTION,
    images: ['/api/og/compare'],
  },
};

// FAQPage schema for the visible "Obvious Question" Q&A below — marks up content
// that genuinely exists on the page (answer text mirrors the rendered prose), so
// it is machine-readable for AI answer engines and eligible for FAQ rich results.
const faqJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: [
    {
      '@type': 'Question',
      name: 'If grounding APIs spent 90 seconds on a claim, would they return the same thing as Tru8?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'No. Time changes how much a grounding API returns, not what it returns — give a search API longer and you get more passages, but the response contract (title, URL, snippet) is unchanged; there is no field for a dispute state to arrive in. Grounding APIs are built to ground answers fast at serving time. Tru8 answers a different question — what does the whole evidence landscape look like? — classifying every source by tier and type, mapping each to what it supports or challenges, and leaving the conflicts visible. We organise; you decide.',
      },
    },
  ],
};

export default function ComparePage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd).replace(/</g, '\\u003c') }}
      />
      <Navigation />
      <MobileBottomNav />

      <main className="min-h-screen pt-24 md:pt-32 pb-24 md:pb-20">
        {/* Header */}
        <div className="container mx-auto px-4 md:px-6 max-w-5xl">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-zinc-400 hover:text-zinc-900 transition-colors mb-6 md:mb-8"
          >
            <ArrowLeft size={20} />
            <span className="text-sm font-medium">Back to Home</span>
          </Link>

          <section className="mb-16 md:mb-20">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4">
              Module — Comparison
            </div>
            <h1 className="text-3xl sm:text-4xl md:text-6xl font-normal tracking-[-0.03em] text-zinc-900 leading-[1.05] mb-6 md:mb-8">
              Grounding APIs check sentences. <span className="font-bold">Tru8 maps evidence.</span>
            </h1>
            <p className="text-base md:text-lg text-zinc-500 leading-relaxed max-w-3xl">
              Who said it, what kind of source, who&apos;s echoing whom, what disputes it,
              what&apos;s missing — classified, receipted, signed. Below: the same claim, Tru8 vs
              four grounding APIs, responses verbatim.
            </p>
          </section>

          {/* Capability table */}
          <section className="mb-20 md:mb-28">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-6">
              Module — Capabilities
            </div>
            <ComparisonTable />
          </section>
        </div>

        {/* Dark band — same claim, verbatim responses */}
        <section className="py-20 md:py-28 bg-zinc-950 text-zinc-100">
          <div className="container mx-auto px-4 md:px-6 max-w-5xl">
            <div className="mb-12 md:mb-16 max-w-3xl">
              <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-accent mb-4 block">
                Module — Raw Responses
              </span>
              <h2 className="text-3xl md:text-5xl font-extralight tracking-[-0.02em] text-zinc-50 leading-[1.05]">
                Tru8 vs <span className="font-bold">four grounding APIs</span>
              </h2>
              <p className="text-sm md:text-base text-zinc-400 leading-relaxed mt-6 max-w-2xl">
                One claim, captured live on the same day, responses verbatim. Each panel shows its
                wall-clock response time — the difference in what comes back, and how long it
                takes, is the comparison.
              </p>
            </div>

            <ResponseTabs />
          </div>
        </section>

        {/* The obvious objection, asked and answered */}
        <section className="py-16 md:py-20 border-b border-zinc-100">
          <div className="container mx-auto px-4 md:px-6 max-w-5xl">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4">
              Module — The Obvious Question
            </div>
            <h2 className="text-2xl md:text-4xl font-normal tracking-[-0.02em] text-zinc-900 mb-6 max-w-3xl">
              If the others spent 90 seconds on this claim,{' '}
              <span className="font-bold">wouldn&apos;t they return the same thing?</span>
            </h2>
            <div className="space-y-5 text-base md:text-lg text-zinc-600 leading-relaxed max-w-3xl">
              <p>
                No — because time changes how <em>much</em> an API returns, not <em>what</em> it
                returns. Give a search API ninety seconds and you get more passages; the response
                contract — title, URL, snippet — is unchanged. There is no field for a dispute
                state to arrive in, however long you wait.
              </p>
              <p>
                These are strong APIs doing exactly what they&apos;re built for: grounding answers
                at serving time, fast and at scale. The slow case is on this page too —
                Parallel&apos;s deeper processors run for minutes and return genuinely deeper
                research. The responses differ from Tru8&apos;s not by effort but by design: each
                schema answers the question its API was built to answer, and none of those
                questions is &ldquo;what does the whole evidence landscape look like?&rdquo;
              </p>
              <p className="text-zinc-900 font-medium">
                That&apos;s the question Tru8 spends its 15–90 seconds on — every source
                classified by tier and type, mapped to what it supports or challenges, with the
                conflicts left visible. We organise; you decide.
              </p>
            </div>
          </div>
        </section>

        {/* Closing CTA strip */}
        <section className="py-20 md:py-24">
          <div className="container mx-auto px-4 md:px-6 max-w-5xl">
            <div className="border border-zinc-200 p-8 md:p-14">
              <h3 className="text-2xl md:text-4xl font-normal tracking-[-0.02em] text-zinc-900 mb-5">
                Different layer, <span className="font-bold">not a faster horse.</span>
              </h3>
              <p className="text-base md:text-lg text-zinc-500 leading-relaxed max-w-3xl mb-10">
                Grounding APIs answer in seconds because they return passages and a score.
                Tru8 takes 15–90 seconds because it returns the evidence landscape: every source
                classified by tier and type, mapped to what it supports or challenges, with
                dispute states, named gaps, exclusion receipts, archived URLs, and a signed
                manifest. If your product needs to show its working, the structure is the product.
              </p>
              <div className="flex flex-col sm:flex-row gap-4">
                <Link
                  href="/developers"
                  className="group inline-flex items-center justify-center gap-4 bg-black text-white px-8 py-4 md:px-10 md:py-5 text-xs font-bold tracking-[0.3em] uppercase transition-colors hover:bg-zinc-900"
                >
                  <span>Read the API docs</span>
                  <span className="w-2.5 h-2.5 bg-accent rotate-45 transition-transform group-hover:translate-x-1" />
                </Link>
                <Link
                  href={`/r/${CHECK_ID}`}
                  className="group inline-flex items-center justify-center gap-2 border border-zinc-200 px-8 py-4 md:px-10 md:py-5 text-xs font-bold tracking-[0.3em] uppercase text-zinc-900 transition-colors hover:border-zinc-900"
                >
                  <span>See the live report</span>
                  <ArrowRight size={14} className="transition-transform group-hover:translate-x-0.5" />
                </Link>
              </div>
            </div>

            {/* Mono metadata footer */}
            <div className="mt-12 pt-6 border-t border-zinc-100">
              <span className="font-mono text-[10px] tracking-widest uppercase text-zinc-400">
                TRU8 — COMPARE — V1.0
              </span>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </>
  );
}
