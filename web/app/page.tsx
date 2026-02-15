import { Navigation } from '@/components/layout/navigation'
import { MobileBottomNav } from '@/components/layout/mobile-bottom-nav'
import { Footer } from '@/components/layout/footer'
import { StitchHero } from '@/components/marketing/stitch-hero'
import { StitchProcess } from '@/components/marketing/stitch-process'
import { StitchFeatures } from '@/components/marketing/stitch-features'
import { StitchVideo } from '@/components/marketing/stitch-video'
import { StitchPricing } from '@/components/marketing/stitch-pricing'

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
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[100] focus:px-4 focus:py-2 focus:bg-zinc-900 focus:text-white"
      >
        Skip to main content
      </a>

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
