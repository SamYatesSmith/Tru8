import { AnimatedBackground } from '@/components/marketing/animated-background'
import { Navigation } from '@/components/layout/navigation'
import { MobileBottomNav } from '@/components/layout/mobile-bottom-nav'
import { Footer } from '@/components/layout/footer'
import { HeroSection } from '@/components/marketing/hero-section'
import { HowItWorks } from '@/components/marketing/how-it-works'
import { FeatureCarousel } from '@/components/marketing/feature-carousel'
import { VideoDemo } from '@/components/marketing/video-demo'
import { PricingCards } from '@/components/marketing/pricing-cards'

export default function Home() {
  return (
    <>
      {/* Animated Background */}
      <AnimatedBackground />

      {/* Navigation */}
      <Navigation />
      <MobileBottomNav />

      {/* Main Content */}
      <main className="relative">
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
