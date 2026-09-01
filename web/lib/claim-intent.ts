/**
 * Claim intent — how the homepage field hands a claim to the console form
 * (2026-09-01 security pass on the claim-field front door).
 *
 * The first build carried the claim in the URL (`/dashboard/new-check?text=…
 * &run=1`). That had three faults, all fixed by moving the payload here:
 *
 * 1. DRIVE-BY SPEND. `run=1` in a URL is a trigger anyone can send to a
 *    signed-in user — one click on a link and a credit is gone. Now the
 *    console auto-runs ONLY when `?run=1` is accompanied by an intent this
 *    tab wrote itself; an attacker cannot write another origin's
 *    sessionStorage without already owning the page.
 * 2. LEAKAGE. A claim in the query string reaches server logs, PostHog
 *    `$current_url`, Sentry breadcrumbs and any Referer. Claims can be
 *    sensitive. sessionStorage never leaves the tab.
 * 3. LENGTH. Claims run to 5,000 characters; URLs should not.
 *
 * Trade-off, stated: sessionStorage is tab-scoped. If sign-in completes in a
 * DIFFERENT tab (an email magic link opened elsewhere), the console form
 * opens empty rather than pre-filled — a graceful miss, never a wrong run.
 *
 * The intent is single-use (consumed on first read) and expires after
 * INTENT_TTL_MS so a claim typed this morning cannot surprise anyone this
 * afternoon.
 */

export const CLAIM_INTENT_KEY = 'tru8.claim-intent';
export const INTENT_TTL_MS = 30 * 60 * 1000;

export type ClaimIntent = {
  kind: 'text' | 'url';
  value: string;
  ts: number;
};

function storage(): Storage | null {
  try {
    return typeof window !== 'undefined' ? window.sessionStorage : null;
  } catch {
    return null;
  }
}

export function saveClaimIntent(kind: ClaimIntent['kind'], value: string, now = Date.now()): boolean {
  const s = storage();
  if (!s) return false;
  try {
    s.setItem(CLAIM_INTENT_KEY, JSON.stringify({ kind, value, ts: now } satisfies ClaimIntent));
    return true;
  } catch {
    return false;
  }
}

export function clearClaimIntent(): void {
  const s = storage();
  if (!s) return;
  try {
    s.removeItem(CLAIM_INTENT_KEY);
  } catch {
    /* ignore */
  }
}

/**
 * Read AND remove the intent. Returns null when absent, malformed or expired
 * (all three also clear the slot).
 */
export function consumeClaimIntent(now = Date.now()): ClaimIntent | null {
  const s = storage();
  if (!s) return null;
  let raw: string | null = null;
  try {
    raw = s.getItem(CLAIM_INTENT_KEY);
  } catch {
    return null;
  }
  if (!raw) return null;
  clearClaimIntent();
  try {
    const parsed = JSON.parse(raw) as Partial<ClaimIntent> | null;
    if (
      !parsed ||
      (parsed.kind !== 'text' && parsed.kind !== 'url') ||
      typeof parsed.value !== 'string' ||
      parsed.value.length === 0 ||
      typeof parsed.ts !== 'number' ||
      !Number.isFinite(parsed.ts)
    ) {
      return null;
    }
    if (now - parsed.ts > INTENT_TTL_MS || parsed.ts > now + 60_000) return null;
    return { kind: parsed.kind, value: parsed.value, ts: parsed.ts };
  } catch {
    return null;
  }
}
