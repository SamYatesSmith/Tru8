import type { Metadata } from 'next'
import { Navigation } from '@/components/layout/navigation'
import { MobileBottomNav } from '@/components/layout/mobile-bottom-nav'
import { Footer } from '@/components/layout/footer'
import { StitchHero } from '@/components/marketing/stitch-hero'
import { StitchProcess } from '@/components/marketing/stitch-process'
import { StitchFeatures } from '@/components/marketing/stitch-features'
import { StitchVideo } from '@/components/marketing/stitch-video'
import { StitchPricing } from '@/components/marketing/stitch-pricing'

const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'https://tru8.app'

export const metadata: Metadata = {
  title: 'Tru8 — AI-Powered Evidence Research',
  description: 'Submit a claim, URL, article, or image. Tru8 searches 30+ sources, classifies evidence by tier and type, and organises the results. No verdicts — just structured evidence.',
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
      description: 'AI-powered evidence research platform. We organise; you decide.',
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
        <StitchVideo />
        <StitchPricing />
      </main>

      <Footer />
    </>
  )
}
