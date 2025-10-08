'use client';

import Link from 'next/link';
import { useState } from 'react';
import { AuthModal } from '@/components/auth/auth-modal';

/**
 * Desktop Navigation Component
 *
 * Top sticky navbar with smooth scroll to sections.
 * Desktop only (>= 768px). Hidden on mobile (replaced by bottom nav).
 *
 * Sections:
 * - Features → #features (Professional Fact-Checking Tools)
 * - How It Works → #how-it-works
 * - Pricing → #pricing
 *
 * CTAs:
 * - Sign In → Opens Clerk auth modal
 * - Get Started → Opens Clerk auth modal (same as Sign In)
 */
export function Navigation() {
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  const scrollToSection = (sectionId: string) => {
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <>
      <nav className="hidden md:block fixed top-0 left-0 right-0 z-50 bg-[#1a1f2e]/95 backdrop-blur-sm border-b border-slate-700" aria-label="Main navigation">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-2" aria-label="Tru8 home">
              <div className="text-3xl font-bold text-white" aria-hidden="true">8</div>
              <span className="text-xl font-semibold text-white">Tru8</span>
            </Link>

            {/* Navigation Links */}
            <div className="flex items-center gap-8" role="navigation">
              <button
                onClick={() => scrollToSection('features')}
                className="text-slate-300 hover:text-[#f57a07] transition-colors text-sm font-medium"
                aria-label="Navigate to features section"
              >
                FEATURES
              </button>
              <button
                onClick={() => scrollToSection('how-it-works')}
                className="text-slate-300 hover:text-[#f57a07] transition-colors text-sm font-medium"
                aria-label="Navigate to how it works section"
              >
                HOW IT WORKS
              </button>
              <button
                onClick={() => scrollToSection('pricing')}
                className="text-slate-300 hover:text-[#f57a07] transition-colors text-sm font-medium"
                aria-label="Navigate to pricing section"
              >
                PRICING
              </button>
            </div>

            {/* Auth CTAs */}
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
