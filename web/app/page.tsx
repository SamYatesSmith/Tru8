import dynamic from 'next/dynamic'
import { Navigation } from '@/components/layout/navigation'
import { MobileBottomNav } from '@/components/layout/mobile-bottom-nav'
import { Footer } from '@/components/layout/footer'
import { HeroSection } from '@/components/marketing/hero-section'
import { HowItWorks } from '@/components/marketing/how-it-works'
import { FeatureCarousel } from '@/components/marketing/feature-carousel'
import { VideoDemo } from '@/components/marketing/video-demo'
import { PricingCards } from '@/components/marketing/pricing-cards'

// Dynamic import for AnimatedBackground to prevent SSR issues
// Loads only on client side with proper loading fallback
const AnimatedBackground = dynamic(
  () => import('@/components/marketing/animated-background').then((mod) => ({
    default: mod.AnimatedBackground,
  })),
  {
    ssr: false,
    loading: () => <div className="fixed inset-0 bg-[#0f1419] -z-10" />,
  }
)

export default function Home() {
  return (
    <>
      {/* Skip to main content for accessibility */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[100] focus:px-4 focus:py-2 focus:bg-[#f57a07] focus:text-white focus:rounded-md"
      >
        Skip to main content
      </a>

      {/* Animated Background - wrapped in Suspense for better error handling */}
      <AnimatedBackground key="animated-bg" />

      {/* Navigation */}
      <Navigation />
      <MobileBottomNav />

      {/* Main Content */}
      <main id="main-content" className="relative">
        {/* Hero Section */}
        <HeroSection />

        {/* How It Works Section */}
        <HowItWorks />

        {/* Features Carousel Section */}
        <FeatureCarousel />

        {/* Video Demo Section */}
        <VideoDemo />

        {/* Pricing Section */}
        <PricingCards />
      </main>

      {/* Footer */}
      <Footer />
    </>
  )
}
