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
    initAnalytics();
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
