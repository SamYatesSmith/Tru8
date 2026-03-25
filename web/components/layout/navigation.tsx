'use client';

import Link from 'next/link';
import Image from 'next/image';
import { useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { AuthModal } from '@/components/auth/auth-modal';

/**
 * Desktop Navigation Component (Stitch W-01)
 *
 * Flat white nav bar with page links.
 * Desktop only (>= 768px). Hidden on mobile (replaced by bottom nav).
 *
 * Layout:
 * - Left: Logo + "Tru8" text
 * - Centre: Page links (Features, Pricing, Blog, About)
 * - Right: Sign In (text) + Get Started (black button)
 */
export function Navigation({
  initialAuthOpen = false,
  redirectUrl
}: {
  initialAuthOpen?: boolean;
  redirectUrl?: string;
}) {
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(initialAuthOpen);
  const { isSignedIn } = useAuth();

  return (
    <>
      <nav className="hidden md:block fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-zinc-100" aria-label="Main navigation">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          {/* Left: Logo */}
          <Link href="/" className="flex items-center gap-3" aria-label="Tru8 home">
            <Image
              src="/logo.proper.png"
              alt="Tru8 logo"
              width={40}
              height={40}
              className="object-contain md:w-[50px] md:h-[50px]"
            />
            <span className="text-xl font-bold tracking-tighter uppercase">
              TRU<span className="text-zinc-400 font-normal">8</span>
            </span>
          </Link>

          {/* Centre: Page links + Auth CTAs */}
          <div className="flex items-center gap-10">
            <div className="flex gap-8 text-[11px] font-semibold tracking-[0.2em] uppercase text-zinc-500">
              <Link href="/#features" className="hover:text-black transition-colors">Features</Link>
              <Link href="/#pricing" className="hover:text-black transition-colors">Pricing</Link>
              <Link href="/about" className="hover:text-black transition-colors">About</Link>
              <Link href="/developers" className="hover:text-black transition-colors">Developers</Link>
            </div>

            {/* Right: Auth CTAs */}
            <div className="flex items-center gap-4">
              {isSignedIn ? (
                <Link
                  href="/dashboard"
                  className="bg-black text-white text-[11px] font-bold tracking-[0.2em] uppercase px-8 py-3 border border-black hover:bg-zinc-800 transition-colors"
                >
                  Dashboard
                </Link>
              ) : (
                <>
                  <button
                    onClick={() => setIsAuthModalOpen(true)}
                    className="text-[11px] font-bold tracking-[0.2em] uppercase px-6 py-3 hover:bg-zinc-50 transition-colors"
                    aria-label="Sign in to your account"
                  >
                    Sign In
                  </button>
                  <button
                    onClick={() => setIsAuthModalOpen(true)}
                    className="bg-black text-white text-[11px] font-bold tracking-[0.2em] uppercase px-8 py-3 border border-black hover:bg-zinc-800 transition-colors"
                    aria-label="Get started with Tru8"
                  >
                    Get Started
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Auth Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        redirectUrl={redirectUrl}
      />
    </>
  );
}
