'use client';

/**
 * Bridges Clerk auth state into PostHog:
 *  - identifies the signed-in user so their events tie together;
 *  - fires the `signup` funnel event once for brand-new accounts.
 *
 * Runs entirely in a useEffect (post-mount) — no hydration involvement.
 * Lives inside <ClerkProvider> (it uses useUser).
 */
import { useEffect } from 'react';
import { useUser } from '@clerk/nextjs';
import { capture, identifyUser } from '@/lib/analytics';

// A freshly-created account is treated as a signup if seen within this window.
const SIGNUP_WINDOW_MS = 2 * 60 * 1000;

export function AnalyticsIdentify() {
  const { isLoaded, isSignedIn, user } = useUser();

  useEffect(() => {
    if (!isLoaded || !isSignedIn || !user) return;

    identifyUser(user.id, {
      email: user.primaryEmailAddress?.emailAddress,
    });

    // Fire `signup` once for a just-created account. Dedup via sessionStorage
    // (survives the post-signup redirect, clears on tab close — minimal,
    // consent-light footprint consistent with the cookieless-first design).
    const createdAt = user.createdAt ? new Date(user.createdAt).getTime() : 0;
    if (createdAt && Date.now() - createdAt < SIGNUP_WINDOW_MS) {
      const key = `t8_signup_${user.id}`;
      try {
        if (!sessionStorage.getItem(key)) {
          capture('signup', { method: 'clerk' });
          sessionStorage.setItem(key, '1');
        }
      } catch {
        // sessionStorage unavailable — fire anyway; minor over-count is fine.
        capture('signup', { method: 'clerk' });
      }
    }
  }, [isLoaded, isSignedIn, user]);

  return null;
}
