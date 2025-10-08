import { AnimatedBackground } from '@/components/marketing/animated-background'
import { Navigation } from '@/components/layout/navigation'
import { MobileBottomNav } from '@/components/layout/mobile-bottom-nav'
import { HeroSection } from '@/components/marketing/hero-section'
import { HowItWorks } from '@/components/marketing/how-it-works'
import { FeatureCarousel } from '@/components/marketing/feature-carousel'
import { VideoDemo } from '@/components/marketing/video-demo'

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

        {/* Pricing Section (Placeholder) */}
        <section id="pricing" className="min-h-screen flex items-center justify-center px-4">
          <div className="container mx-auto text-center">
            <h2 className="text-4xl font-bold text-white mb-4">Choose Your Plan</h2>
            <p className="text-xl text-slate-300">Pricing cards coming in Phase 5...</p>
          </div>
        </section>
      </main>
    </>
  )
}
