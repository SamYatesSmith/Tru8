'use client';

/**
 * First-party cookie consent banner.
 *
 * Renders nothing on the server and on first client render (visible starts
 * false), then a useEffect decides whether to show it — so it can NEVER cause
 * a hydration mismatch (the failure mode that took the site down with the
 * third-party CookieYes script). Writes the `tru8-consent` cookie via
 * lib/consent; analytics.ts reacts to the change to upgrade/opt-out PostHog.
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
      className="fixed inset-x-0 bottom-0 z-[90] p-4 sm:p-6"
    >
      <div className="mx-auto max-w-3xl bg-white border border-zinc-200 shadow-lg">
        <div className="p-5 sm:p-6">
          <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-2">
            Cookies
          </div>
          <h2 className="text-base font-bold text-zinc-900 mb-2">
            We use cookies
          </h2>
          <p className="text-sm text-zinc-500 leading-relaxed">
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

          <div className="mt-6 flex flex-col sm:flex-row gap-3">
            {!managing ? (
              <>
                <button
                  type="button"
                  onClick={() => decide(false)}
                  className="order-2 sm:order-1 px-5 py-3 border border-zinc-200 text-zinc-900 text-xs font-bold uppercase tracking-[0.2em] hover:bg-zinc-50 transition-colors"
                >
                  Reject non-essential
                </button>
                <button
                  type="button"
                  onClick={() => setManaging(true)}
                  className="order-3 sm:order-2 px-5 py-3 text-zinc-500 text-xs font-bold uppercase tracking-[0.2em] hover:text-zinc-900 transition-colors"
                >
                  Manage preferences
                </button>
                <button
                  type="button"
                  onClick={() => decide(true)}
                  className="order-1 sm:order-3 sm:ml-auto px-5 py-3 bg-zinc-900 text-white text-xs font-bold uppercase tracking-[0.2em] hover:bg-zinc-800 transition-colors"
                >
                  Accept all
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={() => decide(analytics)}
                className="sm:ml-auto px-5 py-3 bg-zinc-900 text-white text-xs font-bold uppercase tracking-[0.2em] hover:bg-zinc-800 transition-colors"
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
