import type { Metadata } from 'next'
import { Navigation } from '@/components/layout/navigation'
import { MobileNav } from '@/components/layout/mobile-nav'
import { Footer } from '@/components/layout/footer'
import { StitchHero } from '@/components/marketing/stitch-hero'
import { StitchRecord } from '@/components/marketing/stitch-record'
import { StitchProductPreview } from '@/components/marketing/stitch-product-preview'
import { StitchEdges } from '@/components/marketing/stitch-edges'
import { StitchDeveloperShowcase } from '@/components/marketing/stitch-developer-showcase'
import { StitchFaq } from '@/components/marketing/stitch-faq'
import { StitchClosingCta } from '@/components/marketing/stitch-closing-cta'

const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'https://www.trueight.com'

export const metadata: Metadata = {
  title: 'Tru8 — Evidence Research Infrastructure',
  description: 'See the evidence for and against any claim — and show your working. Tru8 organises external published sources into a structured, signed evidence record: what supports each claim, what challenges it, and what is missing. No verdict — we organise; you decide.',
  alternates: { canonical: '/' },
}

const jsonLd = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'Organization',
      '@id': `${baseUrl}/#organization`,
      name: 'Tru8',
      alternateName: 'Trueight',
      url: baseUrl,
      logo: `${baseUrl}/icon-512.png`,
      description: 'Evidence research infrastructure for factual AI-generated content. Tru8 returns a structured, inspectable evidence record — supports, challenges, gaps and a signed manifest — so you decide what ships. We organise; you decide.',
      sameAs: [
        'https://x.com/tru8app',
        'https://pypi.org/project/tru8-mcp/',
      ],
    },
    {
      '@type': 'WebSite',
      '@id': `${baseUrl}/#website`,
      name: 'Tru8',
      url: baseUrl,
      publisher: { '@id': `${baseUrl}/#organization` },
    },
    {
      '@type': 'SoftwareApplication',
      name: 'Tru8',
      applicationCategory: 'DeveloperApplication',
      operatingSystem: 'Web',
      url: `${baseUrl}/developers`,
      publisher: { '@id': `${baseUrl}/#organization` },
      description: 'Evidence research API and MCP server for AI agents. Decomposes factual AI output into checkable claims, retrieves external published sources, and returns a structured, signed evidence record.',
    },
  ],
}

/**
 * Home Page — the claim field is the front door (2026-09-01; C1 human-first
 * single front door since 2026-07-09).
 * Order: hero (field) → 01 inside a check (proof) → 02 the record (what comes
 * back; old sheets 00+01 folded) → 03 edges → 04 for developers → FAQ → close
 * (the field again). How-it-works removed — the field demonstrates step one and
 * the record sheet covers the rest. Decisions:
 * audit/2026-09-01_landing_below_hero_review.md §Decisions.
 *
 * Auth-redirect handling: middleware sets ?auth_redirect=true when a user hits a
 * protected route signed-out; the nav opens the auth modal and stores redirect_url.
 */
export default function Home({
  searchParams,
}: {
  searchParams: { auth_redirect?: string; redirect_url?: string };
}) {
  const shouldOpenAuth = searchParams.auth_redirect === 'true';
  const redirectUrl = searchParams.redirect_url;

  return (
    <>
      <Navigation initialAuthOpen={shouldOpenAuth} redirectUrl={redirectUrl} />
      <MobileNav />

      <main id="main-content" className="relative">
        {/* JSON-LD lives INSIDE main, not as a direct body child: posthog-js
            inserts its lazy scripts before the first `body > script`, which
            breaks React positional hydration (#418/#422) if that's ours. */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, '\\u003c') }}
        />
        {/* Document edge — one decisive accent stroke (Phase 1 art-direction) */}
        <div aria-hidden="true" className="h-[2px] w-full bg-accent" />
        {/* Persistent title-block spine in the left margin (wide screens only) */}
        <div
          aria-hidden="true"
          className="pointer-events-none fixed left-1.5 top-1/2 z-40 hidden -translate-y-1/2 rotate-180 select-none font-mono text-[9px] tracking-[0.3em] text-zinc-300 [writing-mode:vertical-rl] xl:block"
        >
          TRU8 · EVIDENCE RESEARCH INFRASTRUCTURE · REV 2026.07
        </div>
        {/* Inset document frame — continuous 1px column edges at the max-w-7xl
            boundary, drawn over every section/room so the stacked sheets read as
            one document. xl+ only (where a gutter exists), matching the spine. */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-y-0 left-1/2 z-30 hidden w-full max-w-7xl -translate-x-1/2 xl:block"
        >
          <div className="absolute inset-y-0 left-0 w-px bg-zinc-200" />
          <div className="absolute inset-y-0 right-0 w-px bg-zinc-200" />
        </div>
        <StitchHero />
        <StitchProductPreview />
        <StitchRecord />
        <StitchEdges />
        <StitchDeveloperShowcase />
        <StitchFaq />
        <StitchClosingCta />
      </main>

      <Footer />
    </>
  )
}
