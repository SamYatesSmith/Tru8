'use client';

import { CheckCircle, Clock, Users } from 'lucide-react';
import { useState } from 'react';
import { AuthModal } from '@/components/auth/auth-modal';

/**
 * Hero Section Component
 *
 * Main landing page hero with glowing border container.
 *
 * Design Features:
 * - Dark container with rounded corners
 * - Animated orange border glow effect
 * - White "Tru8" text (solid, not transparent)
 *
 * Content:
 * - Headline: "Tru8" (white text)
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
        {/* Content Container with Backlight */}
        <div className="relative max-w-6xl w-full mx-auto">
          {/* Backlit container */}
          <div className="hero-backlight rounded-3xl p-16 md:p-20 bg-[#1e293b] border border-slate-700/50">
            {/* Content */}
            <div className="text-center">
              {/* Headline - Transparent text showing gradient through */}
              <h1 className="hero-gradient-text text-7xl md:text-8xl lg:text-9xl font-black mb-6">
                Tru8
              </h1>

              {/* Subheadline */}
              <h2 className="text-2xl md:text-3xl lg:text-4xl font-semibold text-white mb-6">
                Transparent Fact-Checking with Dated Evidence
              </h2>

              {/* Description */}
              <p className="text-base md:text-lg lg:text-xl text-slate-300 mb-12 max-w-3xl mx-auto leading-relaxed">
                Built for journalists, researchers, and content creators who demand
                accuracy. Get instant verification with transparent, sourced
                evidence—not just answers, but proof you can cite.
              </p>

              {/* CTAs */}
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12">
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
                  className="px-8 py-4 bg-transparent border-2 border-slate-600 hover:border-[#f57a07] text-white rounded-lg text-lg font-semibold transition-all min-w-[240px]"
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
