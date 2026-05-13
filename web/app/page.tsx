import type { Metadata } from 'next'
import { Navigation } from '@/components/layout/navigation'
import { MobileBottomNav } from '@/components/layout/mobile-bottom-nav'
import { Footer } from '@/components/layout/footer'
import { StitchHero } from '@/components/marketing/stitch-hero'
import { StitchProcess } from '@/components/marketing/stitch-process'
import { StitchFeatures } from '@/components/marketing/stitch-features'
import { StitchProductPreview } from '@/components/marketing/stitch-product-preview'
import { StitchApiBand } from '@/components/marketing/stitch-api-band'
import { StitchDeveloperShowcase } from '@/components/marketing/stitch-developer-showcase'
import { StitchPricing } from '@/components/marketing/stitch-pricing'

const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'https://www.trueight.com'

export const metadata: Metadata = {
  title: 'Tru8 — AI-Powered News Evidence Research',
  description: 'Paste a news article, headline, or claim. Tru8 searches multiple source types, classifies evidence by tier and type, and maps the full evidence landscape. No verdicts — just structured evidence so you can form your own view.',
  alternates: { canonical: '/' },
}

const jsonLd = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'Organization',
      name: 'Tru8',
      url: baseUrl,
      logo: `${baseUrl}/favicon.proper.png`,
      description: 'AI-powered news evidence research platform. Research what\u2019s behind the headlines. We organise; you decide.',
    },
    {
      '@type': 'WebSite',
      name: 'Tru8',
      url: baseUrl,
    },
  ],
}

/**
 * Home Page (Stitch W-01 Landing)
 *
 * Unified Auth Flow Integration:
 * - Detects auth_redirect=true parameter (set by middleware)
 * - Auto-opens auth modal when user tried to access protected route
 * - Stores redirect_url to send user back after sign-in
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
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, '\\u003c') }}
      />
      <Navigation initialAuthOpen={shouldOpenAuth} redirectUrl={redirectUrl} />
      <MobileBottomNav />

      <main id="main-content" className="relative">
        <StitchHero />
        <StitchProcess />
        <StitchFeatures />
        <StitchProductPreview />
        <StitchApiBand />
        <StitchDeveloperShowcase />
        <StitchPricing />
      </main>

      <Footer />
    </>
  )
}
