/**
 * PostHog analytics — cookieless-first.
 *
 * Design (see audit/OPEN_WORK.md INST-01 + memory project-analytics-visibility):
 *  - Init with `persistence: 'memory'` → stores NOTHING on the device → needs no
 *    consent banner under UK GDPR/PECR, so traffic is visible immediately,
 *    independent of the CookieYes banner (which is currently disabled — see
 *    INST-02/INST-04). Capture is ON in this mode.
 *  - When the visitor later grants the *analytics* category via CookieYes, we
 *    upgrade persistence to `localStorage+cookie` for cross-session identity.
 *    That path is dormant until the CookieYes banner is re-enabled, but wired
 *    so it "just works" when it returns.
 *
 * All calls are client-only and guarded; on the server every function no-ops.
 * Nothing here runs during render/hydration — initAnalytics() is invoked from a
 * useEffect in the provider.
 */
import posthog from 'posthog-js';

const KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY;
const HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://eu.i.posthog.com';

let initialized = false;

/** Idempotent. Safe to call from anywhere; no-ops on the server or without a key. */
export function initAnalytics(): void {
  if (initialized) return;
  if (typeof window === 'undefined') return;
  if (!KEY) return; // analytics disabled when the build-time key is absent

  posthog.init(KEY, {
    api_host: HOST,
    persistence: 'memory', // cookieless-first — no device storage, no consent required
    person_profiles: 'identified_only',
    capture_pageview: false, // captured manually for App Router client-side nav
    capture_pageleave: true,
    autocapture: true,
    disable_session_recording: true,
  });
  initialized = true;

  // Upgrade now if analytics consent was already granted in a prior visit, and
  // react to future consent changes (dormant until the CookieYes banner is live).
  applyConsentFromCookieYes();
  document.addEventListener(
    'cookieyes_consent_update',
    applyConsentFromCookieYes as EventListener,
  );
}

/** Promote memory → persistent storage once the CookieYes analytics category is granted. */
export function applyConsentFromCookieYes(): void {
  if (!initialized || typeof document === 'undefined') return;
  if (readAnalyticsConsent()) {
    posthog.set_config({ persistence: 'localStorage+cookie' });
  }
}

function readAnalyticsConsent(): boolean {
  try {
    const cookie = document.cookie
      .split('; ')
      .find((c) => c.startsWith('cookieyes-consent='));
    if (!cookie) return false;
    // CookieYes stores e.g. "...,analytics:yes,advertisement:no,..."
    const value = decodeURIComponent(cookie.split('=')[1] || '');
    return /analytics:yes/.test(value);
  } catch {
    return false;
  }
}

/** Manual pageview — App Router doesn't fire PostHog's auto pageview on client nav. */
export function capturePageview(pathname: string | null, search?: string): void {
  initAnalytics();
  if (!initialized || typeof window === 'undefined' || !pathname) return;
  let url = window.location.origin + pathname;
  if (search) url += `?${search}`;
  posthog.capture('$pageview', { $current_url: url });
}

/** Funnel events — keep this list small and meaningful. */
export type AnalyticsEvent =
  | 'signup'
  | 'check_submitted'
  | 'paywall_hit'
  | 'upgrade_click';

export function capture(
  event: AnalyticsEvent,
  properties?: Record<string, unknown>,
): void {
  initAnalytics();
  if (!initialized || typeof window === 'undefined') return;
  posthog.capture(event, properties);
}

/** Associate subsequent events with a known user (e.g. after Clerk auth). */
export function identifyUser(
  id: string,
  properties?: Record<string, unknown>,
): void {
  initAnalytics();
  if (!initialized || typeof window === 'undefined') return;
  posthog.identify(id, properties);
}
