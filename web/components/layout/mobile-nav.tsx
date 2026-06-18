'use client';

import Link from 'next/link';
import { useState, useEffect, useRef, useCallback } from 'react';
import { Menu, X } from 'lucide-react';
import { useAuth } from '@clerk/nextjs';
import { AuthModal } from '@/components/auth/auth-modal';
import { Tru8Mark } from '@/components/brand/tru8-mark';
import { capture } from '@/lib/analytics';

/**
 * Mobile Navigation (Stitch light theme) — verification/dev-led repositioning.
 *
 * Replaces the consumer scroll-to-section bottom nav with a top bar + hamburger
 * that opens an accessible full-screen sheet (role=dialog, aria-modal, focus
 * trap, Esc-to-close, focus return). Mirrors the desktop nav links + CTAs.
 */
const NAV_LINKS = [
  { label: 'Product', href: '/#record' },
  { label: 'Compare', href: '/compare' },
  { label: 'Pricing', href: '/pricing' },
  { label: 'Developers', href: '/developers' },
];

export function MobileNav() {
  const [open, setOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const { isSignedIn } = useAuth();
  const triggerRef = useRef<HTMLButtonElement>(null);
  const sheetRef = useRef<HTMLDivElement>(null);

  const close = useCallback(() => setOpen(false), []);

  // Scroll-lock + focus management while the sheet is open
  useEffect(() => {
    if (!open) return;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const sheet = sheetRef.current;
    const focusables = sheet
      ? Array.from(
          sheet.querySelectorAll<HTMLElement>('a[href], button:not([disabled])')
        )
      : [];
    focusables[0]?.focus();

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        close();
        return;
      }
      if (e.key === 'Tab' && focusables.length > 0) {
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.style.overflow = prevOverflow;
      document.removeEventListener('keydown', onKeyDown);
      triggerRef.current?.focus();
    };
  }, [open, close]);

  return (
    <>
      <div className="md:hidden fixed top-0 left-0 right-0 z-50 bg-white/90 backdrop-blur-md border-b border-zinc-100">
        <div className="flex items-center justify-between px-5 h-16">
          <Link href="/" className="flex items-center gap-2" aria-label="Tru8 home">
            <Tru8Mark size={32} />
            <span className="text-lg font-bold tracking-tighter uppercase leading-none">
              TRU<span className="text-zinc-400 font-normal">8</span>
            </span>
          </Link>
          <button
            ref={triggerRef}
            onClick={() => setOpen(true)}
            aria-label="Open menu"
            aria-expanded={open}
            aria-controls="mobile-nav-sheet"
            className="p-2 -mr-2 text-zinc-900"
          >
            <Menu size={24} aria-hidden="true" />
          </button>
        </div>
      </div>

      {open && (
        <div
          id="mobile-nav-sheet"
          ref={sheetRef}
          role="dialog"
          aria-modal="true"
          aria-label="Site menu"
          className="md:hidden fixed inset-0 z-[60] bg-white flex flex-col"
        >
          <div className="flex items-center justify-between px-5 h-16 border-b border-zinc-100">
            <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400">
              Menu
            </span>
            <button
              onClick={close}
              aria-label="Close menu"
              className="p-2 -mr-2 text-zinc-900"
            >
              <X size={24} aria-hidden="true" />
            </button>
          </div>

          <nav
            className="flex flex-col px-5 py-8 gap-6 overflow-y-auto"
            aria-label="Mobile navigation"
          >
            {NAV_LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                onClick={close}
                className="text-sm font-bold tracking-[0.2em] uppercase text-zinc-900"
              >
                {l.label}
              </Link>
            ))}

            <div className="h-px bg-zinc-100 my-2" />

            {isSignedIn ? (
              <Link
                href="/dashboard"
                onClick={close}
                className="bg-black text-white text-xs font-bold tracking-[0.2em] uppercase px-6 py-4 text-center"
              >
                Dashboard
              </Link>
            ) : (
              <>
                <button
                  onClick={() => {
                    close();
                    setIsAuthModalOpen(true);
                  }}
                  className="text-left text-sm font-bold tracking-[0.2em] uppercase text-zinc-500"
                >
                  Sign In
                </button>
                <Link
                  href="/research"
                  onClick={() => {
                    capture('research_app_click', { surface: 'mobile-nav' });
                    close();
                  }}
                  className="border border-zinc-200 text-xs font-bold tracking-[0.2em] uppercase px-6 py-4 text-center text-zinc-900"
                >
                  Research App
                </Link>
                <Link
                  href="/developers"
                  onClick={() => {
                    capture('get_api_key_click', { surface: 'mobile-nav' });
                    close();
                  }}
                  className="bg-black text-white text-xs font-bold tracking-[0.2em] uppercase px-6 py-4 text-center"
                >
                  Get API Key
                </Link>
              </>
            )}
          </nav>
        </div>
      )}

      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
      />
    </>
  );
}
