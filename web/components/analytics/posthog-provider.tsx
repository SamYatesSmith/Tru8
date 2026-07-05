'use client';

/**
 * Cookieless-first PostHog provider.
 *
 * Mounts at the app root and:
 *  - initialises PostHog in a useEffect (post-mount, client-only) so it NEVER
 *    participates in SSR/hydration — structurally immune to the CookieYes-class
 *    hydration crash (see audit incident INST-02/INST-04);
 *  - captures a manual $pageview on every client-side route change, which
 *    App Router requires (PostHog's auto pageview only fires on hard loads).
 *
 * No-ops cleanly when NEXT_PUBLIC_POSTHOG_KEY is unset (initAnalytics guards it),
 * so this is safe to ship before the key is configured on Railway.
 */
import { Suspense, useEffect } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';
import { initAnalytics, capturePageview } from '@/lib/analytics';

function PageviewTracker() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    capturePageview(pathname, searchParams?.toString());
  }, [pathname, searchParams]);

  return null;
}

export function AnalyticsProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Defer init until the page has fully loaded AND the main thread is idle.
    // posthog-js lazy-loads extension scripts (web-vitals etc.) by inserting
    // <script type="text/javascript"> BEFORE the first `body > script` — if
    // that runs while React is still hydrating a route that renders a
    // body-level <script> (our JSON-LD), positional hydration matches the
    // wrong node and throws React #418/#422 (prod incident, 2026-07-05).
    let cancelled = false;
    const start = () => {
      if (cancelled) return;
      if (typeof window.requestIdleCallback === 'function') {
        window.requestIdleCallback(() => { if (!cancelled) initAnalytics(); });
      } else {
        setTimeout(() => { if (!cancelled) initAnalytics(); }, 1);
      }
    };
    if (document.readyState === 'complete') {
      start();
    } else {
      window.addEventListener('load', start, { once: true });
    }
    return () => {
      cancelled = true;
      window.removeEventListener('load', start);
    };
  }, []);

  return (
    <>
      {/* useSearchParams must sit under Suspense or it deopts the route to CSR. */}
      <Suspense fallback={null}>
        <PageviewTracker />
      </Suspense>
      {children}
    </>
  );
}
