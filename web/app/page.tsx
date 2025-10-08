import { AnimatedBackground } from '@/components/marketing/animated-background'
import { Navigation } from '@/components/layout/navigation'
import { MobileBottomNav } from '@/components/layout/mobile-bottom-nav'

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
        <section id="hero" className="min-h-screen flex items-center justify-center pt-16 pb-20 px-4">
          <div className="container mx-auto text-center">
            <h1 className="text-6xl md:text-7xl font-bold text-white mb-6">Tru8</h1>
            <h2 className="text-3xl md:text-4xl font-semibold text-white mb-6">
              Transparent Fact-Checking with Dated Evidence
            </h2>
            <p className="text-lg md:text-xl text-slate-300 mb-12 max-w-3xl mx-auto">
              Phase 2 Complete: Navigation with Desktop & Mobile nav + Auth modal
            </p>
          </div>
        </section>

        {/* Features Section (Placeholder) */}
        <section id="features" className="min-h-screen flex items-center justify-center px-4">
          <div className="container mx-auto text-center">
            <h2 className="text-4xl font-bold text-white mb-4">Professional Fact-Checking Tools</h2>
            <p className="text-xl text-slate-300">Carousel coming in Phase 4...</p>
          </div>
        </section>

        {/* How It Works Section (Placeholder) */}
        <section id="how-it-works" className="min-h-screen flex items-center justify-center px-4">
          <div className="container mx-auto text-center">
            <h2 className="text-4xl font-bold text-white mb-4">How Tru8 Works</h2>
            <p className="text-xl text-slate-300">3-step process coming in Phase 4...</p>
          </div>
        </section>

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
