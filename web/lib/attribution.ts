/**
 * Signup-source attribution — the frontend half (audit/OUTREACH.md).
 *
 * Outreach links carry ?src=<tag> (utm_source also honoured). The tag is
 * stored FIRST-TOUCH in localStorage on any page load, survives the Clerk
 * signup hop because both sides of it are this origin, and is flushed ONCE to
 * the backend after the user is signed in. The backend enforces write-once
 * and a post-signup time window; this side only remembers and delivers.
 *
 * An untagged visitor stores nothing and stays UNKNOWN — never "direct".
 */

const STORAGE_KEY = 'tru8_src';

// Mirror of the backend rule (app/core/attribution.py). A tag that fails
// here would be refused server-side anyway; rejecting early stores nothing.
const SOURCE_RE = /^[a-z0-9][a-z0-9_.-]{0,63}$/;

export function normaliseSource(raw: string | null): string | null {
  if (!raw) return null;
  const tag = raw.trim().toLowerCase();
  return SOURCE_RE.test(tag) ? tag : null;
}

/** Read ?src= (preferred) or ?utm_source= from a query string. */
export function sourceFromSearch(search: string): string | null {
  const params = new URLSearchParams(search);
  return normaliseSource(params.get('src')) ?? normaliseSource(params.get('utm_source'));
}

/**
 * Store the current page's source tag, first-touch: an existing stored tag is
 * never overwritten. Call on every page load; no-ops when untagged.
 */
export function captureAttribution(search: string): void {
  const source = sourceFromSearch(search);
  if (!source) return;
  try {
    if (localStorage.getItem(STORAGE_KEY) !== null) return; // first touch wins
    localStorage.setItem(STORAGE_KEY, source);
  } catch {
    // Storage unavailable (private mode etc.) — attribution is best-effort.
  }
}

/** The stored tag awaiting flush, if any. */
export function pendingAttribution(): string | null {
  try {
    return normaliseSource(localStorage.getItem(STORAGE_KEY));
  } catch {
    return null;
  }
}

/** Forget the stored tag — call once the backend has answered (either way). */
export function clearAttribution(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Nothing to do.
  }
}
