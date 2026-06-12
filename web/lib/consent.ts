/**
 * First-party cookie consent — single source of truth.
 *
 * Replaces the third-party CookieYes CMP (which crashed hydration). The choice
 * is stored in our own `tru8-consent` cookie; the banner writes it, analytics.ts
 * reads it to decide whether PostHog runs cookieless (memory) or persistent.
 *
 * Legal model:
 *  - Necessary cookies (Clerk auth, Stripe) are exempt — always on.
 *  - Analytics is the only non-essential category. Until the user decides,
 *    PostHog runs cookieless (no device storage → consent-exempt under PECR).
 *  - Accept → PostHog upgrades to persistent cookies. Reject → PostHog opts out.
 *
 * Writing the consent cookie itself is "strictly necessary" (it records the
 * user's choice), so it needs no prior consent.
 */
export const CONSENT_COOKIE = 'tru8-consent';
export const CONSENT_VERSION = 1;
/** Fired on window when the user makes/changes a choice. */
export const CONSENT_CHANGED_EVENT = 'tru8-consent-changed';
/** Fired on window to re-open the banner (e.g. footer "Cookie Preferences"). */
export const OPEN_CONSENT_EVENT = 'tru8-open-consent';

export interface ConsentState {
  /** Has the user made an explicit choice yet? */
  decided: boolean;
  /** Whether analytics (non-essential) is permitted. */
  analytics: boolean;
}

const UNDECIDED: ConsentState = { decided: false, analytics: false };

export function readConsent(): ConsentState {
  if (typeof document === 'undefined') return UNDECIDED;
  try {
    const raw = document.cookie
      .split('; ')
      .find((c) => c.startsWith(`${CONSENT_COOKIE}=`));
    if (!raw) return UNDECIDED;
    const parsed = JSON.parse(decodeURIComponent(raw.split('=').slice(1).join('=')));
    // A version bump invalidates old consent and re-prompts.
    if (!parsed || parsed.v !== CONSENT_VERSION) return UNDECIDED;
    return { decided: true, analytics: !!parsed.analytics };
  } catch {
    return UNDECIDED;
  }
}

export function writeConsent(analytics: boolean): void {
  if (typeof document === 'undefined') return;
  const payload = encodeURIComponent(
    JSON.stringify({ v: CONSENT_VERSION, analytics, ts: Date.now() }),
  );
  const maxAge = 60 * 60 * 24 * 180; // 180 days
  const secure = window.location.protocol === 'https:' ? '; Secure' : '';
  document.cookie = `${CONSENT_COOKIE}=${payload}; Max-Age=${maxAge}; Path=/; SameSite=Lax${secure}`;
  window.dispatchEvent(
    new CustomEvent(CONSENT_CHANGED_EVENT, { detail: { analytics } }),
  );
}

/** Re-open the consent banner (footer / cookie-policy links). */
export function openConsentBanner(): void {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent(OPEN_CONSENT_EVENT));
}
