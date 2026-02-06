/**
 * Twitter/X URL utilities for detecting tweets and building share/reply intents
 */

// Regex pattern for twitter.com and x.com status URLs
const TWEET_URL_PATTERN = /^https?:\/\/(?:www\.)?(?:twitter\.com|x\.com)\/([^\/]+)\/status\/(\d+)/i;

/**
 * Check if a URL is a Twitter/X tweet URL
 */
export function isTweetUrl(url: string | null | undefined): boolean {
  if (!url) return false;
  return TWEET_URL_PATTERN.test(url);
}

/**
 * Extract the tweet ID from a Twitter/X URL
 * Returns null if not a valid tweet URL
 */
export function extractTweetId(url: string | null | undefined): string | null {
  if (!url) return null;
  const match = url.match(TWEET_URL_PATTERN);
  return match ? match[2] : null;
}

/**
 * Build a Twitter intent URL for replying to a specific tweet
 */
export function buildTwitterReplyUrl(tweetId: string, shareUrl: string, shareText: string): string {
  const params = new URLSearchParams({
    in_reply_to: tweetId,
    url: shareUrl,
    text: shareText,
  });
  return `https://twitter.com/intent/tweet?${params.toString()}`;
}

/**
 * Build a Twitter intent URL for sharing (new tweet, not a reply)
 */
export function buildTwitterShareUrl(shareUrl: string, shareText: string): string {
  const params = new URLSearchParams({
    url: shareUrl,
    text: shareText,
  });
  return `https://twitter.com/intent/tweet?${params.toString()}`;
}
