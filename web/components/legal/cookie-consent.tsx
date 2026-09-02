'use client';

/**
 * First-party cookie consent banner.
 *
 * Renders nothing on the server and on first client render (visible starts
 * false), then a useEffect decides whether to show it — so it can NEVER cause
 * a hydration mismatch (the failure mode that took the site down with the
 * third-party CookieYes script). Writes the `tru8-consent` cookie via
 * lib/consent; analytics.ts reacts to the change to upgrade/opt-out PostHog.
 *
 * Compact below `sm` (2026-09-02): the first Playwright screenshot of the live
 * homepage as an iPhone 15 showed this sheet covering the lower ~55% of the
 * first screen — headline cut in half, lede and claim field hidden — so a
 * stranger met a cookie box before the front door. On phones it is now a
 * bottom strip: one sentence, two side-by-side buttons, "Manage preferences"
 * as a small link. Same choices, same cookie, same copy locks; only the
 * layout and the mobile button label ("Reject analytics" — analytics IS the
 * only non-essential category, see the Manage panel) differ. Desktop unchanged.
 */
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { readConsent, writeConsent, OPEN_CONSENT_EVENT } from '@/lib/consent';

export function CookieConsent() {
  const [visible, setVisible] = useState(false);
  const [managing, setManaging] = useState(false);
  const [analytics, setAnalytics] = useState(true);

  useEffect(() => {
    const current = readConsent();
    if (!current.decided) {
      setVisible(true); // first visit — prompt
    } else {
      setAnalytics(current.analytics);
    }

    // Footer / cookie-policy "Cookie Preferences" re-opens the banner.
    const open = () => {
      const c = readConsent();
      setAnalytics(c.decided ? c.analytics : true);
      setManaging(true);
      setVisible(true);
    };
    window.addEventListener(OPEN_CONSENT_EVENT, open);
    return () => window.removeEventListener(OPEN_CONSENT_EVENT, open);
  }, []);

  if (!visible) return null;

  const decide = (analyticsChoice: boolean) => {
    writeConsent(analyticsChoice);
    setVisible(false);
    setManaging(false);
  };

  return (
    <div
      role="dialog"
      aria-label="Cookie consent"
      aria-live="polite"
      className="fixed inset-x-0 bottom-0 z-[90] p-3 sm:p-6"
    >
      <div className="mx-auto max-w-3xl bg-white border border-zinc-200 shadow-lg">
        <div className="p-4 sm:p-6">
          <div className="hidden sm:block font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-2">
            Cookies
          </div>
          {/* Heading stays for screen readers on phones; visually only from sm. */}
          <h2 className="sr-only sm:not-sr-only sm:text-base sm:font-bold sm:text-zinc-900 sm:mb-2">
            We use cookies
          </h2>
          {/* Phones: one sentence. */}
          <p className="sm:hidden text-xs text-zinc-500 leading-relaxed">
            Necessary cookies are always on; analytics only if you allow them.{' '}
            <Link
              href="/cookie-policy"
              className="underline underline-offset-2 hover:text-zinc-900 transition-colors"
            >
              Cookie Policy
            </Link>
            .
          </p>
          <p className="hidden sm:block text-sm text-zinc-500 leading-relaxed">
            Necessary cookies keep you signed in and secure — they&apos;re always
            on. Analytics cookies help us understand how Tru8 is used so we can
            improve it. You decide.{' '}
            <Link
              href="/cookie-policy"
              className="underline underline-offset-2 hover:text-zinc-900 transition-colors"
            >
              Cookie Policy
            </Link>
            .
          </p>

          {managing && (
            <div className="mt-5 space-y-4 border-t border-zinc-100 pt-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-bold text-zinc-900">Necessary</p>
                  <p className="text-xs text-zinc-500">
                    Sign-in, security, and payments. Required — cannot be turned off.
                  </p>
                </div>
                <span className="font-mono text-[10px] tracking-widest uppercase text-zinc-400 pt-1">
                  Always on
                </span>
              </div>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-bold text-zinc-900">Analytics</p>
                  <p className="text-xs text-zinc-500">
                    Anonymous usage data (PostHog) to improve the product.
                  </p>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={analytics}
                  onClick={() => setAnalytics((a) => !a)}
                  className={`relative mt-1 h-5 w-9 shrink-0 transition-colors ${
                    analytics ? 'bg-zinc-900' : 'bg-zinc-300'
                  }`}
                  aria-label="Toggle analytics cookies"
                >
                  <span
                    className={`absolute top-0.5 h-4 w-4 bg-white transition-transform ${
                      analytics ? 'translate-x-4' : 'translate-x-0.5'
                    }`}
                  />
                </button>
              </div>
            </div>
          )}

          {/* Phones: a 2-column grid — Reject | Accept, Manage as a small link
              beneath. From sm: the original row (Reject · Manage · Accept). */}
          <div className="mt-3 sm:mt-6 grid grid-cols-2 gap-2 sm:flex sm:flex-row sm:gap-3">
            {!managing ? (
              <>
                <button
                  type="button"
                  onClick={() => decide(false)}
                  className="order-1 px-3 py-2.5 sm:px-5 sm:py-3 border border-zinc-200 text-zinc-900 text-[11px] sm:text-xs font-bold uppercase tracking-[0.12em] sm:tracking-[0.2em] hover:bg-zinc-50 transition-colors"
                >
                  <span className="sm:hidden">Reject analytics</span>
                  <span className="hidden sm:inline">Reject non-essential</span>
                </button>
                <button
                  type="button"
                  onClick={() => setManaging(true)}
                  className="order-3 col-span-2 sm:order-2 sm:col-span-1 px-3 py-1.5 sm:px-5 sm:py-3 text-zinc-500 text-[10px] sm:text-xs font-bold uppercase tracking-[0.12em] sm:tracking-[0.2em] hover:text-zinc-900 transition-colors"
                >
                  Manage preferences
                </button>
                <button
                  type="button"
                  onClick={() => decide(true)}
                  className="order-2 sm:order-3 sm:ml-auto px-3 py-2.5 sm:px-5 sm:py-3 bg-zinc-900 text-white text-[11px] sm:text-xs font-bold uppercase tracking-[0.12em] sm:tracking-[0.2em] hover:bg-zinc-800 transition-colors"
                >
                  Accept all
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={() => decide(analytics)}
                className="col-span-2 sm:col-span-1 sm:ml-auto px-5 py-3 bg-zinc-900 text-white text-xs font-bold uppercase tracking-[0.2em] hover:bg-zinc-800 transition-colors"
              >
                Save preferences
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
