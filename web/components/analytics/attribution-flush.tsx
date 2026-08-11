'use client';

import { useEffect, useRef } from 'react';
import { useAuth } from '@clerk/nextjs';
import { apiClient } from '@/lib/api';
import { clearAttribution, pendingAttribution } from '@/lib/attribution';

/**
 * Delivers the stored signup-source tag once the visitor is signed in
 * (mounted in the dashboard layout, which middleware guarantees is authed).
 * The backend decides whether it lands — write-once, inside the attribution
 * window — and EVERY definitive answer clears the stored tag, including
 * refusals: an account past the window or already attributed will never
 * accept it, so retrying would just re-send it forever. Only a network
 * failure leaves the tag in place for the next visit.
 */
export function AttributionFlush() {
  const { getToken, isSignedIn } = useAuth();
  const attempted = useRef(false);

  useEffect(() => {
    if (!isSignedIn || attempted.current) return;
    const source = pendingAttribution();
    if (!source) return;
    attempted.current = true;

    (async () => {
      try {
        const token = await getToken();
        await apiClient.recordSignupSource(source, token);
        clearAttribution();
      } catch {
        // Network/server failure: keep the tag; a later visit retries.
        attempted.current = false;
      }
    })();
  }, [isSignedIn, getToken]);

  return null;
}
