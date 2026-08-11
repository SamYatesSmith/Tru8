'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
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
 * - Right (signed out): Sign In (AuthModal) · Start a check (filled primary)
 * - Right (signed in):  Get API Key (lg+) · Dashboard · Start a check (filled primary)
 *
 * BOTH states end in the same filled primary, "Start a check" →
 * /dashboard/new-check — the CHECK FORM, not the account overview (see
 * stitch-hero.tsx for what that cost us). One secondary text link per role,
 * then one primary; do not add a second filled button to either branch.
 *
 * Per design-review B2: the primary CTAs NAVIGATE (Link), they do not open the
 * auth modal. Only "Sign In" opens the modal. A signed-out visit to a protected
 * route is bounced back by middleware with ?auth_redirect=true, which opens the
 * modal and returns the visitor to THAT route (not a fixed /dashboard) after
 * sign-in, via AuthModal's forceRedirectUrl.
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
  const router = useRouter();

  // The middleware bounce reaches this component two ways. On a full page
  // load, useState reads initialAuthOpen and the modal opens. On a CLIENT-SIDE
  // navigation (hero/nav "Start a check" clicked from "/"), this component is
  // already mounted, useState ignores the prop change, and the modal silently
  // failed to open — a signed-out visitor's primary CTA did nothing
  // (2026-08-11, reproduced in-browser). This effect closes that path.
  useEffect(() => {
    if (initialAuthOpen) setIsAuthModalOpen(true);
  }, [initialAuthOpen]);

  const closeAuthModal = () => {
    setIsAuthModalOpen(false);
    // Strip the bounce params so the next bounce is a fresh false→true
    // transition, and a refresh or shared URL doesn't reopen the modal.
    if (initialAuthOpen) router.replace('/', { scroll: false });
  };

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
                  {/* Signed-in mirrors the signed-out shape: secondary text
                      links, then ONE filled primary. Until 2026-08-10 the
                      primary here was "Dashboard", so a signed-in visitor on
                      /pricing or /compare had no way to start a check without
                      going via the dashboard first. The primary is now the same
                      action in both states, which is also what makes "Start a
                      check" the single start label sitewide.

                      "Get API Key" drops below lg: at md the row is logo + four
                      links + three CTAs, which overflows. It is the least
                      urgent of the three and /developers is in the centre nav
                      anyway. */}
                  <Link
                    href="/developers"
                    onClick={() => capture('get_api_key_click', { surface: 'nav' })}
                    className="hidden lg:inline-flex text-[11px] font-bold tracking-[0.2em] uppercase px-4 py-3 text-zinc-500 hover:text-black transition-colors whitespace-nowrap"
                  >
                    Get API Key
                  </Link>
                  <Link
                    href="/dashboard"
                    className="text-[11px] font-bold tracking-[0.2em] uppercase px-3 py-3 text-zinc-500 hover:text-black transition-colors whitespace-nowrap"
                  >
                    Dashboard
                  </Link>
                  <Link
                    href="/dashboard/new-check"
                    onClick={() => capture('start_check_click', { surface: 'nav' })}
                    className="bg-black text-white text-[11px] font-bold tracking-[0.2em] uppercase px-8 py-3 border border-black hover:bg-zinc-800 transition-colors whitespace-nowrap"
                  >
                    Start a check
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

      {/* Auth Modal — opened by "Sign In" or the middleware bounce */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={closeAuthModal}
        redirectUrl={redirectUrl}
      />
    </>
  );
}
