/**
 * PostHog analytics — cookieless-first.
 *
 * Design (see audit/OPEN_WORK.md INST-01 + memory project-analytics-visibility):
 *  - Init with `persistence: 'memory'` → stores NOTHING on the device → needs no
 *    consent banner under UK GDPR/PECR, so traffic is visible immediately,
 *    independent of the CookieYes banner (which is currently disabled — see
 *    INST-02/INST-04). Capture is ON in this mode.
 *  - When the visitor accepts analytics via our first-party consent banner
 *    (lib/consent + components/legal/cookie-consent), we upgrade persistence to
 *    `localStorage+cookie` for cross-session identity. If they reject, PostHog
 *    opts out entirely. Undecided → cookieless default, capture on.
 *
 * All calls are client-only and guarded; on the server every function no-ops.
 * Nothing here runs during render/hydration — initAnalytics() is invoked from a
 * useEffect in the provider.
 */
import posthog from 'posthog-js';
import { readConsent, CONSENT_CHANGED_EVENT } from './consent';

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

  // Apply any stored choice now, and react to future consent changes.
  applyConsent();
  window.addEventListener(CONSENT_CHANGED_EVENT, applyConsent);
}

/**
 * Reconcile PostHog with the user's consent choice.
 *  - accepted  → persistent cookies + opt in
 *  - rejected  → opt out, drop back to memory
 *  - undecided → leave the cookieless default (capture on, no storage)
 */
export function applyConsent(): void {
  if (!initialized || typeof window === 'undefined') return;
  const { decided, analytics } = readConsent();
  if (!decided) return;
  if (analytics) {
    posthog.set_config({ persistence: 'localStorage+cookie' });
    posthog.opt_in_capturing();
  } else {
    posthog.opt_out_capturing();
    posthog.set_config({ persistence: 'memory' });
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
  | 'upgrade_click'
  // Verification-repositioning funnel (P1, 2026-06-15). Wired to existing
  // durable surfaces now; more added in P4 when the homepage is rebuilt.
  | 'get_api_key_click' // developer-conversion CTA (nav/hero/developers)
  | 'try_in_browser_click' // legacy hero primary CTA (pre-repositioning)
  | 'research_app_click' // human-path CTA → /research (retired with /research, C1 2026-07-09)
  | 'research_start_click' // /research primary CTA → /dashboard (retired with /research, C1 2026-07-09)
  // C1 entry-point clarity (2026-07-09): the single human start funnel
  | 'start_check_click' // "Start a check" CTA → /dashboard (property: surface — nav/mobile-nav/hero/record/closing/footer)
  | 'view_sample_click' // "See a sample record" → public demo /r/ (property: surface — hero/closing)
  // Researcher funnel (Phase 1 instrumentation, 2026-06-23)
  | 'report_viewed' // a check report opened (public /r/ or dashboard)
  | 'evidence_expanded' // a supports/challenges evidence item expanded
  | 'receipt_opened' // the excluded-evidence / receipts disclosure opened
  | 'view_opened' // a profession view switched to (property: view)
  | 'share_clicked' // a share button clicked (property: platform)
  | 'export_clicked' // PDF evidence record downloaded (Phase 2; property: surface)
  // Pricing page (P3 packaging, 2026-06-24; all carry property: surface)
  | 'pricing_console_click' // Console "Start in the browser" CTA → /dashboard
  | 'pricing_free_click' // Free taster CTA → /dashboard
  | 'pricing_teams_click' // Teams "Talk to us" CTA → /contact
  | 'pricing_api_click' // quiet API band "See the API" → /developers
  | 'pricing_billing_toggle' // Console monthly/annual toggle (property: period — monthly/annual)
  | 'auth_stale_session_reset'; // wedged Clerk session auto-signed-out in AuthModal (2026-07-05 incident)

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
