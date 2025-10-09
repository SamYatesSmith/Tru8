'use client';

import Link from 'next/link';
import Image from 'next/image';
import { useState } from 'react';
import { AuthModal } from '@/components/auth/auth-modal';

/**
 * Desktop Navigation Component
 *
 * Hover pill navigation with centered "Tru8" branding.
 * Desktop only (>= 768px). Hidden on mobile (replaced by bottom nav).
 *
 * Design:
 * - Left: "8" logo
 * - Center: Rounded pill container (~12px radius)
 *   - Default: "Tru8" heading visible
 *   - Hover: Navigation items fade in (1s transition)
 * - Right: Sign In + Get Started buttons
 *
 * Sections:
 * - Features → #features
 * - How It Works → #how-it-works
 * - Demo → #video-demo
 * - Pricing → #pricing
 *
 * CTAs:
 * - Sign In → Opens Clerk auth modal
 * - Get Started → Opens Clerk auth modal (same as Sign In)
 */
export function Navigation() {
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  const scrollToSection = (sectionId: string) => {
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <>
      <nav className="hidden md:block fixed top-0 left-0 right-0 z-50 py-4" aria-label="Main navigation">
        <div className="container mx-auto px-4">
          <div className="relative flex items-center justify-between">
            {/* Left: Logo */}
            <Link href="/" className="flex items-center" aria-label="Tru8 home">
              <Image
                src="/logo.proper.png"
                alt="Tru8 logo"
                width={80}
                height={80}
                className="object-contain"
              />
            </Link>

            {/* Center: Hover Pill Container - Absolutely centered */}
            <div
              className="absolute left-1/2 -translate-x-1/2"
              onMouseEnter={() => setIsHovered(true)}
              onMouseLeave={() => setIsHovered(false)}
              role="navigation"
            >
              {/* Primary Pill - Tru8 Heading - 40% larger, no border */}
              <div className="bg-[#1e293b] rounded-xl px-10 py-3 mt-2.5">
                <h1 className="text-3xl font-bold text-white text-center whitespace-nowrap">
                  Tru8
                </h1>
              </div>

              {/* Secondary Pill - Navigation Links - Container appears instantly, links fade */}
              {isHovered && (
                <div className="absolute top-[85%] left-1/2 -translate-x-1/2 bg-[#1e293b] rounded-xl px-12 py-4">
                  {/* Links fade in on hover */}
                  <div className="flex items-center justify-center gap-8 whitespace-nowrap animate-fade-in">

                  <button
                    onClick={() => scrollToSection('features')}
                    className="text-slate-300 hover:text-[#f57a07] transition-colors text-base font-medium"
                    aria-label="Navigate to features section"
                  >
                    FEATURES
                  </button>
                  <span className="text-slate-700">|</span>
                  <button
                    onClick={() => scrollToSection('how-it-works')}
                    className="text-slate-300 hover:text-[#f57a07] transition-colors text-base font-medium"
                    aria-label="Navigate to how it works section"
                  >
                    HOW IT WORKS
                  </button>
                  <span className="text-slate-700">|</span>
                  <button
                    onClick={() => scrollToSection('video-demo')}
                    className="text-slate-300 hover:text-[#f57a07] transition-colors text-base font-medium"
                    aria-label="Navigate to demo section"
                  >
                    DEMO
                  </button>
                  <span className="text-slate-700">|</span>
                  <button
                    onClick={() => scrollToSection('pricing')}
                    className="text-slate-300 hover:text-[#f57a07] transition-colors text-base font-medium"
                    aria-label="Navigate to pricing section"
                  >
                    PRICING
                  </button>
                </div>
              </div>
              )}
            </div>

            {/* Right: Auth CTAs */}
            <div className="flex items-center gap-4">
              <button
                onClick={() => setIsAuthModalOpen(true)}
                className="text-white hover:text-[#f57a07] transition-colors text-sm font-medium"
                aria-label="Sign in to your account"
              >
                Sign In
              </button>
              <button
                onClick={() => setIsAuthModalOpen(true)}
                className="px-6 py-2 bg-[#f57a07] hover:bg-[#e06a00] text-white rounded-md text-sm font-medium transition-colors"
                aria-label="Get started with Tru8"
              >
                Get Started
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Auth Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
      />
    </>
  );
}
