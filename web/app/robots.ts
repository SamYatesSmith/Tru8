import type { MetadataRoute } from 'next'

const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'https://www.trueight.com'

// Public surface every crawler may read; private/auth + non-OG API stay blocked.
const ALLOW = ['/', '/api/og/']
const DISALLOW = ['/dashboard/', '/api/', '/sign-in/', '/sign-up/']

// AI answer-engine crawlers we explicitly welcome (AEO/GEO): we WANT to be
// retrievable/citable by ChatGPT, Claude, Perplexity, Gemini and Google AI
// Overviews on our public pages. Listing them with the same allow/disallow as
// '*' makes the intent unambiguous (and signals we are not blocking them, which
// many sites now do). They still cannot reach the auth-walled app or raw API.
const AI_BOTS = [
  'GPTBot',
  'OAI-SearchBot',
  'ChatGPT-User',
  'ClaudeBot',
  'anthropic-ai',
  'Claude-Web',
  'PerplexityBot',
  'Perplexity-User',
  'Google-Extended',
]

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        // Allow the dynamic OG image routes even though /api/ is otherwise blocked,
        // so social/link unfurlers can fetch share-card images.
        allow: ALLOW,
        disallow: DISALLOW,
      },
      {
        userAgent: AI_BOTS,
        allow: ALLOW,
        disallow: DISALLOW,
      },
    ],
    sitemap: `${baseUrl}/sitemap.xml`,
  }
}
