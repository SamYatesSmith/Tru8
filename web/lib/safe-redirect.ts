/**
 * safeInternalPath — accept a post-sign-in destination ONLY if it is a path
 * on this site (2026-09-01 security pass on the claim-field front door).
 *
 * `?redirect_url=` arrives on `/` from the middleware bounce and is handed to
 * Clerk's `forceRedirectUrl`, which trusts whatever the app gives it. Read
 * straight from the query string, that is an open redirect: a link such as
 * `/?auth_redirect=true&redirect_url=https://evil.example` would sign a
 * visitor in on OUR modal and land them on someone else's page. The
 * protocol-relative form (`//evil.example`) and the backslash form
 * (`/\evil.example`, which browsers normalise to `//`) reach the same place.
 *
 * Rules: a string; starts with exactly one `/`; second character is not `/`
 * or `\`; no whitespace or control characters; bounded length; and, belt and
 * braces, resolving it against a fixed origin stays on that origin.
 * Anything else → `undefined`, and the caller falls back to its default.
 */
const MAX_LENGTH = 2048;

export function safeInternalPath(value: unknown): string | undefined {
  if (typeof value !== 'string') return undefined;
  if (value.length === 0 || value.length > MAX_LENGTH) return undefined;
  if (value[0] !== '/') return undefined;
  if (value[1] === '/' || value[1] === '\\') return undefined;
  // eslint-disable-next-line no-control-regex -- control chars are the point
  if (/[\s\u0000-\u001f\u007f]/.test(value)) return undefined;
  try {
    const probe = new URL(value, 'https://origin.invalid');
    if (probe.origin !== 'https://origin.invalid') return undefined;
  } catch {
    return undefined;
  }
  return value;
}
