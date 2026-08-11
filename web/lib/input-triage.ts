/**
 * Input triage — catch inputs the pipeline cannot serve BEFORE a check is
 * spent (2026-08-11 usage audit: of 23 external checks, ~5 were homepages,
 * video pages or paywalled papers that ate a check to learn their input was
 * unreadable, and one three-word topic failed outright).
 *
 * Rules are mechanical and deliberately narrow: refuse only what reliably
 * fails. A borderline input goes through — the backend's ingest guards fail
 * honestly and refund. Over-refusal here would block legitimate checks.
 */

export type TriageResult = { ok: true } | { ok: false; message: string };

// Platforms whose pages are video or login-walled — ingest never reads them.
const VIDEO_SOCIAL_HOSTS = [
  'youtube.com',
  'youtu.be',
  'tiktok.com',
  'instagram.com',
  'facebook.com',
  'x.com',
  'twitter.com',
];

// Publishers that paywall essentially everything they host. Open-access
// venues (PLOS, eLife, BMC…) are deliberately absent — they read fine.
const PAYWALLED_PUBLISHER_HOSTS = [
  'onlinelibrary.wiley.com',
  'sciencedirect.com',
  'jstor.org',
  'tandfonline.com',
  'link.springer.com',
  'doi.org', // resolves to a publisher page, almost always paywalled
];

function hostMatches(hostname: string, domain: string): boolean {
  return hostname === domain || hostname.endsWith(`.${domain}`);
}

/** Triage a URL input. Assumes the string already parses as a URL. */
export function triageUrl(raw: string): TriageResult {
  let url: URL;
  try {
    url = new URL(raw.trim());
  } catch {
    return { ok: true }; // not ours to judge — the existing validator handles it
  }
  const host = url.hostname.toLowerCase().replace(/^www\./, '');

  if (VIDEO_SOCIAL_HOSTS.some((d) => hostMatches(host, d))) {
    return {
      ok: false,
      message: "We can't read video or social posts. Type the claim it makes instead.",
    };
  }

  if (PAYWALLED_PUBLISHER_HOSTS.some((d) => hostMatches(host, d))) {
    return {
      ok: false,
      message:
        "This publisher paywalls its papers, so we can't read the page. Type the paper's claim instead.",
    };
  }

  // Bare homepage: no path, no query — a site, not an article.
  if ((url.pathname === '/' || url.pathname === '') && !url.search) {
    return {
      ok: false,
      message:
        "That's a site's homepage. Paste the specific article, or type the claim.",
    };
  }

  return { ok: true };
}

/** Triage a text input. Assumes length limits are already enforced. */
export function triageText(raw: string): TriageResult {
  const text = raw.trim();
  const words = text.split(/\s+/).filter(Boolean);

  // A topic, not a claim ("pink salt diet"). Questions pass — the pipeline
  // extracts the implied claim.
  if (words.length <= 3 && !text.endsWith('?')) {
    return {
      ok: false,
      message:
        "That's a topic, not a claim. Say what's claimed about it, or ask it as a question.",
    };
  }

  return { ok: true };
}
