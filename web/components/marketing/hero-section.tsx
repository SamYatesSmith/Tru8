'use client';

import { CheckCircle, Clock, Users } from 'lucide-react';
import { useState } from 'react';
import { AuthModal } from '@/components/auth/auth-modal';
import { scrollToSection } from '@/lib/scroll-utils';

/**
 * Hero Section Component
 *
 * Main landing page hero with glowing border container.
 *
 * Design Features:
 * - Dark container with rounded corners
 * - Animated orange border glow effect
 * - Gradient "Tru8" text with swirling animation
 *
 * Content:
 * - Headline: "Tru8" (gradient text)
 * - Subheadline: "Stop Guessing. Start Knowing."
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

  return (
    <>
      <section
        id="hero"
        className="relative min-h-screen flex items-center justify-center pt-16 pb-20 px-4 overflow-hidden"
      >
        {/* Content Container with Backlight */}
        <div className="relative max-w-6xl w-full mx-auto">
          {/* Backlit container with multi-layer glow */}
          <div className="hero-backlight hero-container-depth rounded-3xl p-16 md:p-20 bg-[#1e293b] border border-slate-700/50">
            {/* Inner wrapper for additional glow layers */}
            <div>
              {/* Content */}
              <div className="text-center">
                {/* Headline - Gradient text with swirling animation */}
                <h1 className="hero-gradient-text text-7xl md:text-8xl lg:text-9xl font-black mb-6 tracking-wider">
                  Tru8
                </h1>

                {/* Subheadline */}
                <h2 className="text-2xl md:text-3xl lg:text-4xl font-semibold text-white mb-6">
                  Stop Guessing. Start Knowing.
                </h2>

                {/* Description */}
                <p className="text-base md:text-lg lg:text-xl text-slate-300 mb-12 max-w-3xl mx-auto leading-relaxed">
                  In a world of misinformation, or fake news, verify what you read and share. Quick fact-checking backed by credible sources you can cite.
                </p>

                {/* CTAs */}
                <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12">
                  {/* Primary CTA - Opens Auth Modal */}
                  <button
                    onClick={() => setIsAuthModalOpen(true)}
                    className="px-8 py-4 bg-[#f57a07] hover:bg-[#e06a00] text-white rounded-lg text-lg font-semibold transition-all hover:shadow-lg hover:shadow-[rgba(245,122,7,0.3)] min-w-[240px] cta-pulse btn-scale-hover"
                    aria-label="Start verifying content for free"
                  >
                    Start Verifying Free
                  </button>

                  {/* Secondary CTA - Scroll to How It Works */}
                  <button
                    onClick={() => scrollToSection('how-it-works')}
                    className="px-8 py-4 bg-transparent border-2 border-slate-600 hover:border-[#f57a07] text-white rounded-lg text-lg font-semibold transition-all min-w-[240px] btn-scale-hover"
                    aria-label="Learn how Tru8 works"
                  >
                    See How It Works
                  </button>
                </div>

                {/* Trust Indicators */}
                <div className="flex flex-col sm:flex-row items-center justify-center gap-8 text-sm">
                  {/* Verified Sources */}
                  <div className="flex items-center gap-2 trust-badge-1">
                    <CheckCircle className="w-5 h-5 text-[#22d3ee]" />
                    <span className="text-slate-400">Verified Sources</span>
                  </div>

                  {/* Real-time Results */}
                  <div className="flex items-center gap-2 trust-badge-2">
                    <Clock className="w-5 h-5 text-[#22d3ee]" />
                    <span className="text-slate-400">Real-time Results</span>
                  </div>

                  {/* Professional Grade */}
                  <div className="flex items-center gap-2 trust-badge-3">
                    <Users className="w-5 h-5 text-[#22d3ee]" />
                    <span className="text-slate-400">Professional Grade</span>
                  </div>
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

      {/* Hero styles - global needed for class selectors to work */}
      <style jsx global>{`
        /* Gentle pulse animation - pulses intensity only */
        @keyframes gentlePulse {
          0%, 100% {
            opacity: 0.8;
            filter: brightness(1);
          }
          50% {
            opacity: 1;
            filter: brightness(1.15);
          }
        }

        /* Sunburst rays - pulses outward from card (includes translate to maintain centering) */
        @keyframes rayPulse {
          0%, 100% {
            transform: translate(-50%, -50%) scale(1);
            opacity: 0.6;
          }
          50% {
            transform: translate(-50%, -50%) scale(1.08);
            opacity: 1;
          }
        }

        /* Breathing animation - expands outer glow spread while keeping inner edge anchored */
        @keyframes breathe {
          0%, 100% {
            box-shadow:
              0 0 0 5px rgba(245, 122, 7, 1),
              0 0 0 8px rgba(245, 122, 7, 0.95),
              0 0 2px 10px rgba(245, 122, 7, 0.9),
              0 0 4px 13px rgba(245, 122, 7, 0.85),
              0 0 8px 16px rgba(245, 122, 7, 0.8),
              0 0 12px 20px rgba(245, 122, 7, 0.75),
              0 0 18px 25px rgba(245, 122, 7, 0.65),
              0 0 25px 32px rgba(251, 146, 60, 0.5),
              0 0 35px 40px rgba(251, 146, 60, 0.38),
              0 0 48px 50px rgba(252, 165, 87, 0.28),
              0 0 65px 62px rgba(253, 186, 116, 0.2),
              0 0 85px 76px rgba(255, 220, 180, 0.14),
              0 0 110px 92px rgba(255, 235, 215, 0.09),
              0 0 140px 110px rgba(255, 245, 235, 0.05),
              0 0 175px 130px rgba(255, 255, 255, 0.02);
          }
          50% {
            box-shadow:
              0 0 0 5px rgba(245, 122, 7, 1),
              0 0 0 8px rgba(245, 122, 7, 0.95),
              0 0 2px 10px rgba(245, 122, 7, 0.9),
              0 0 4px 13px rgba(245, 122, 7, 0.85),
              0 0 8px 16px rgba(245, 122, 7, 0.8),
              0 0 12px 22px rgba(245, 122, 7, 0.75),
              0 0 20px 28px rgba(245, 122, 7, 0.65),
              0 0 30px 38px rgba(251, 146, 60, 0.55),
              0 0 42px 48px rgba(251, 146, 60, 0.42),
              0 0 58px 60px rgba(252, 165, 87, 0.32),
              0 0 78px 75px rgba(253, 186, 116, 0.24),
              0 0 100px 92px rgba(255, 220, 180, 0.18),
              0 0 130px 112px rgba(255, 235, 215, 0.12),
              0 0 165px 135px rgba(255, 245, 235, 0.07),
              0 0 205px 160px rgba(255, 255, 255, 0.03);
          }
        }

        /* Serene color rotation through orange/white spectrum */
        @keyframes colorRotate {
          0% {
            filter: hue-rotate(0deg) brightness(1);
          }
          33% {
            filter: hue-rotate(10deg) brightness(1.2);
          }
          66% {
            filter: hue-rotate(-10deg) brightness(1.1);
          }
          100% {
            filter: hue-rotate(0deg) brightness(1);
          }
        }

        /* Swirling color animation - rotates the gradient BEHIND the text */
        @keyframes swirlColors {
          0% {
            background-position: 50% 50%;
          }
          25% {
            background-position: 0% 50%;
          }
          50% {
            background-position: 50% 100%;
          }
          75% {
            background-position: 100% 50%;
          }
          100% {
            background-position: 50% 50%;
          }
        }

        .hero-backlight {
          position: relative;
          overflow: visible;
        }

        /* Single glow layer - animates spread values directly for breathing effect */
        .hero-backlight::before {
          position: absolute;
          content: "";
          inset: 0;
          z-index: -1;
          border-radius: 3rem;
          animation: breathe 10s ease-in-out infinite, colorRotate 20s ease-in-out infinite;
        }

        /* Sunburst rays - subtle god rays emanating from behind the card */
        .hero-backlight::after {
          position: absolute;
          content: "";
          top: 50%;
          left: 50%;
          width: 180%;
          height: 180%;
          transform: translate(-50%, -50%);
          z-index: -2;
          pointer-events: none;
          background: conic-gradient(
            from 0deg at 50% 50%,
            transparent 0deg,
            rgba(251, 146, 60, 0.18) 2deg,
            transparent 5deg,
            transparent 16deg,
            rgba(245, 122, 7, 0.15) 18deg,
            transparent 21deg,
            transparent 34deg,
            rgba(253, 186, 116, 0.2) 36deg,
            transparent 39deg,
            transparent 52deg,
            rgba(251, 146, 60, 0.12) 54deg,
            transparent 57deg,
            transparent 72deg,
            rgba(245, 122, 7, 0.18) 74deg,
            transparent 77deg,
            transparent 90deg,
            rgba(253, 186, 116, 0.15) 92deg,
            transparent 95deg,
            transparent 110deg,
            rgba(251, 146, 60, 0.2) 112deg,
            transparent 115deg,
            transparent 128deg,
            rgba(245, 122, 7, 0.12) 130deg,
            transparent 133deg,
            transparent 148deg,
            rgba(253, 186, 116, 0.18) 150deg,
            transparent 153deg,
            transparent 166deg,
            rgba(251, 146, 60, 0.15) 168deg,
            transparent 171deg,
            transparent 186deg,
            rgba(245, 122, 7, 0.2) 188deg,
            transparent 191deg,
            transparent 204deg,
            rgba(253, 186, 116, 0.12) 206deg,
            transparent 209deg,
            transparent 224deg,
            rgba(251, 146, 60, 0.18) 226deg,
            transparent 229deg,
            transparent 242deg,
            rgba(245, 122, 7, 0.15) 244deg,
            transparent 247deg,
            transparent 262deg,
            rgba(253, 186, 116, 0.2) 264deg,
            transparent 267deg,
            transparent 280deg,
            rgba(251, 146, 60, 0.12) 282deg,
            transparent 285deg,
            transparent 300deg,
            rgba(245, 122, 7, 0.18) 302deg,
            transparent 305deg,
            transparent 318deg,
            rgba(253, 186, 116, 0.15) 320deg,
            transparent 323deg,
            transparent 338deg,
            rgba(251, 146, 60, 0.18) 340deg,
            transparent 343deg,
            transparent 360deg
          );
          filter: blur(20px);
          mask-image: radial-gradient(ellipse at center, transparent 10%, black 20%, black 50%, transparent 75%);
          animation: rayPulse 8s ease-in-out infinite;
        }

        .hero-backlight > div {
          position: relative;
        }

        /* Gradient text with swirling colors */
        .hero-gradient-text {
          background:
            radial-gradient(ellipse at 20% 30%, #f57a07 0%, transparent 50%),
            radial-gradient(ellipse at 80% 70%, #fb923c 0%, transparent 50%),
            radial-gradient(ellipse at 50% 50%, #fca55f 0%, transparent 40%),
            radial-gradient(ellipse at 70% 20%, #fdc9a0 0%, transparent 45%),
            radial-gradient(ellipse at 30% 80%, #ffffff 0%, transparent 50%),
            linear-gradient(135deg,
              #f57a07 0%,
              #fb923c 20%,
              #fca55f 40%,
              #fdc9a0 60%,
              #ffffff 80%,
              #fca55f 100%
            );
          background-size: 400% 400%;
          background-position: center;
          animation: swirlColors 15s ease-in-out infinite;
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          color: transparent;

          /* Fine orange border/stroke for emphasis - subtle */
          -webkit-text-stroke: 1px #f57a07;
          text-stroke: 1px #f57a07;
          paint-order: stroke fill;

          /* Warm orange glow shadow */
          filter: drop-shadow(0 4px 12px rgba(245, 122, 7, 0.6))
                  drop-shadow(0 8px 24px rgba(251, 146, 60, 0.4))
                  drop-shadow(0 12px 32px rgba(252, 165, 87, 0.3));
        }

        /* Hero container inner shadow for depth */
        .hero-container-depth {
          box-shadow: inset 0 3px 16px 0 rgba(0, 0, 0, 0.15),
                      inset 0 6px 24px 0 rgba(0, 0, 0, 0.1),
                      inset 0 -3px 16px 0 rgba(0, 0, 0, 0.15),
                      inset 3px 0 16px 0 rgba(0, 0, 0, 0.15),
                      inset -3px 0 16px 0 rgba(0, 0, 0, 0.15);
        }

        /* Respect reduced motion preference */
        @media (prefers-reduced-motion: reduce) {
          .hero-backlight::before,
          .hero-backlight::after,
          .hero-gradient-text {
            animation: none;
          }

          .hero-gradient-text {
            background-position: 0% 50%;
          }
        }
      `}</style>
    </>
  );
}
