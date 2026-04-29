'use client';

import { useEffect } from 'react';

/**
 * Unregister any service workers that may have been registered against this
 * origin by previous deployments. The current codebase has no service worker —
 * but trueight.com had a Workbox-based SW at some earlier point that is still
 * active in returning users' browsers, intercepting fetches and serving stale
 * cached failure responses (most visibly on /api/v1/checks/{id}/progress
 * during the 2026-04-29 deploy window).
 *
 * Service workers persist for the origin until explicitly unregistered, even
 * across hard refreshes. This component runs once on every page load: if any
 * SW registration is found, it unregisters every one, clears the SW-managed
 * Cache Storage, and reloads the page so the new render bypasses the dead SW.
 *
 * Cost on healthy clients (no SW registered): one async no-op call to
 * getRegistrations() that resolves to []. No reload, no flash.
 *
 * Once every previously-affected user has loaded a single page on the new
 * site, this component has done its job and can be removed (probably safe
 * to delete after ~30 days). For now, keep it: cheap insurance.
 */
export function ServiceWorkerTombstone() {
  useEffect(() => {
    if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) {
      return;
    }
    navigator.serviceWorker
      .getRegistrations()
      .then((registrations) => {
        if (registrations.length === 0) return;
        return Promise.all(registrations.map((r) => r.unregister()))
          .then(() => {
            if (typeof window === 'undefined' || !('caches' in window)) return;
            return caches
              .keys()
              .then((names) => Promise.all(names.map((n) => caches.delete(n))))
              .then(() => undefined);
          })
          .then(() => {
            window.location.reload();
          });
      })
      .catch(() => {
        // Fail quiet — if the SW APIs throw, we are not making things worse.
      });
  }, []);
  return null;
}
