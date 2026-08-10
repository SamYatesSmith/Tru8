'use client';

import Link from 'next/link';
import { useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { AuthModal } from '@/components/auth/auth-modal';
import { Tru8Mark } from '@/components/brand/tru8-mark';
import { capture } from '@/lib/analytics';

/**
 * Desktop Navigation (Stitch W-01) — human-first (C1, 2026-07-09).
 *
 * Desktop only (>= 768px); mobile uses <MobileNav/>.
 * - Left: logo
 * - Centre: Product · Compare · Pricing · Developers (MCP/Docs are /developers sections)
 * - Right (signed out): Sign In (AuthModal) · Start a check (→/dashboard/new-check,
 *   filled primary — the CHECK FORM, not the account overview; see stitch-hero)
 *   The dev path is the Developers centre link; "Get API Key" lives on /developers.
 *
 * Per design-review B2: the primary CTAs NAVIGATE (Link), they do not open the
 * auth modal. Only "Sign In" opens the modal. A signed-out /dashboard visit is
 * bounced back by middleware with ?auth_redirect=true, which opens the modal
 * and returns the visitor to /dashboard after sign-in.
 */
const NAV_LINKS = [
  { label: 'Product', href: '/#record' },
  { label: 'Compare', href: '/compare' },
  { label: 'Pricing', href: '/pricing' },
  { label: 'Developers', href: '/developers' },
];

export function Navigation({
  initialAuthOpen = false,
  redirectUrl,
}: {
  initialAuthOpen?: boolean;
  redirectUrl?: string;
}) {
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(initialAuthOpen);
  const { isSignedIn } = useAuth();

  return (
    <>
      <nav
        className="hidden md:block fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-zinc-100"
        aria-label="Main navigation"
      >
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between gap-8">
          {/* Left: Logo */}
          <Link href="/" className="flex items-center gap-3 shrink-0" aria-label="Tru8 home">
            <Tru8Mark height={48} />
            <span className="text-xl font-bold tracking-tighter uppercase">
              TRU<span className="text-zinc-400 font-normal">8</span>
            </span>
          </Link>

          {/* Centre: links + Right: CTAs */}
          <div className="flex items-center gap-8">
            <div className="flex gap-7 text-[11px] font-semibold tracking-[0.2em] uppercase text-zinc-500">
              {NAV_LINKS.map((l) => (
                <Link
                  key={l.href}
                  href={l.href}
                  className="hover:text-black transition-colors whitespace-nowrap"
                >
                  {l.label}
                </Link>
              ))}
            </div>

            <div className="flex items-center gap-4 shrink-0">
              {isSignedIn ? (
                <>
                  <Link
                    href="/developers"
                    onClick={() => capture('get_api_key_click', { surface: 'nav' })}
                    className="text-[11px] font-bold tracking-[0.2em] uppercase px-4 py-3 text-zinc-500 hover:text-black transition-colors whitespace-nowrap"
                  >
                    Get API Key
                  </Link>
                  <Link
                    href="/dashboard"
                    className="bg-black text-white text-[11px] font-bold tracking-[0.2em] uppercase px-8 py-3 border border-black hover:bg-zinc-800 transition-colors"
                  >
                    Dashboard
                  </Link>
                </>
              ) : (
                <>
                  <button
                    onClick={() => setIsAuthModalOpen(true)}
                    className="text-[11px] font-bold tracking-[0.2em] uppercase px-3 py-3 text-zinc-500 hover:text-black transition-colors"
                    aria-label="Sign in to your account"
                  >
                    Sign In
                  </button>
                  <Link
                    href="/dashboard/new-check"
                    onClick={() => capture('start_check_click', { surface: 'nav' })}
                    className="bg-black text-white text-[11px] font-bold tracking-[0.2em] uppercase px-8 py-3 border border-black hover:bg-zinc-800 transition-colors whitespace-nowrap"
                  >
                    Start a check
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Auth Modal — only opened by "Sign In" */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        redirectUrl={redirectUrl}
      />
    </>
  );
}
