'use client';

import { CheckCircle, Clock, Users } from 'lucide-react';
import { useState } from 'react';
import { AuthModal } from '@/components/auth/auth-modal';

/**
 * Hero Section Component
 *
 * Main landing page hero with animated gradient glow and transparent text.
 *
 * Design Features:
 * - Animated gradient glow behind Tru8 text (pulsing effect)
 * - Transparent "Tru8" text with gradient showing through (background-clip: text)
 * - Backlit gradient container effect
 *
 * Content:
 * - Headline: "Tru8" (transparent with gradient)
 * - Subheadline: "Transparent Fact-Checking with Dated Evidence"
 * - Description: Brand messaging
 * - CTAs:
 *   - Primary: "Start Verifying Free" (orange, opens auth modal)
 *   - Secondary: "See How It Works" (outline, scrolls to #how-it-works)
 * - Trust Indicators:
 *   - Verified Sources (CheckCircle icon)
 *   - Real-time Results (Clock icon)
 *   - Professional Grade (Users icon)
 *
 * Backend Integration:
 * - "Start Verifying Free" triggers Clerk auth modal
 * - After auth: Redirects to /dashboard
 * - Backend auto-creates user with 3 free credits
 */
export function HeroSection() {
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  const scrollToHowItWorks = () => {
    const element = document.getElementById('how-it-works');
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <>
      <section
        id="hero"
        className="relative min-h-screen flex items-center justify-center pt-16 pb-20 px-4"
      >
        {/* Animated Gradient Glow (behind everything) */}
        <div className="absolute inset-0 flex items-center justify-center overflow-hidden">
          <div className="hero-gradient-glow" />
        </div>

        {/* Content Container */}
        <div className="relative max-w-4xl mx-auto text-center z-10">
          {/* Headline with Transparent Text + Gradient */}
          <div className="relative mb-6">
            <h1 className="hero-gradient-text text-8xl md:text-9xl font-black">
              Tru8
            </h1>
          </div>

          {/* Subheadline */}
          <h2 className="text-3xl md:text-4xl font-semibold text-white mb-6">
            Transparent Fact-Checking with Dated Evidence
          </h2>

          {/* Description */}
          <p className="text-lg md:text-xl text-slate-300 mb-12 max-w-3xl mx-auto leading-relaxed">
            Built for journalists, researchers, and content creators who demand
            accuracy. Get instant verification with transparent, sourced
            evidence—not just answers, but proof you can cite.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
            {/* Primary CTA - Opens Auth Modal */}
            <button
              onClick={() => setIsAuthModalOpen(true)}
              className="px-8 py-4 bg-[#f57a07] hover:bg-[#e06a00] text-white rounded-lg text-lg font-semibold transition-all hover:shadow-lg hover:shadow-[rgba(245,122,7,0.3)] min-w-[240px]"
              aria-label="Start verifying content for free"
            >
              Start Verifying Free
            </button>

            {/* Secondary CTA - Scroll to How It Works */}
            <button
              onClick={scrollToHowItWorks}
              className="px-8 py-4 bg-transparent border-2 border-slate-700 hover:border-[#f57a07] text-white rounded-lg text-lg font-semibold transition-all min-w-[240px]"
              aria-label="Learn how Tru8 works"
            >
              See How It Works
            </button>
          </div>

          {/* Trust Indicators */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-8 text-sm">
            {/* Verified Sources */}
            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-[#22d3ee]" />
              <span className="text-slate-400">Verified Sources</span>
            </div>

            {/* Real-time Results */}
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-[#22d3ee]" />
              <span className="text-slate-400">Real-time Results</span>
            </div>

            {/* Professional Grade */}
            <div className="flex items-center gap-2">
              <Users className="w-5 h-5 text-[#22d3ee]" />
              <span className="text-slate-400">Professional Grade</span>
            </div>
          </div>
        </div>
      </section>

      {/* Auth Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
      />
    </>
  );
}
