import type { MetadataRoute } from 'next'

const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'https://www.trueight.com'

// Date the verification/dev-led repositioning shipped. Pinning the marketing
// routes to a real content date (rather than new Date() on every deploy) keeps
// <lastmod> an honest signal instead of "everything changed today".
const REPOSITIONED = new Date('2026-06-18')
// The homepage went human-first + absorbed /research (C1, one front door).
const HUMAN_FIRST = new Date('2026-07-09')
// Second blog post publish date. Also the last time the blog INDEX changed,
// since the index changes when a post is added.
const AGENTS_POST = new Date('2026-03-25')
// Legal-details pass: correct registered company name/number/office across the
// contact and privacy pages, and the UK statutory citation on the refund page.
const LEGAL_REFRESH = new Date('2026-08-03')

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: baseUrl,
      lastModified: HUMAN_FIRST,
      changeFrequency: 'weekly',
      priority: 1.0,
    },
    {
      url: `${baseUrl}/about`,
      lastModified: REPOSITIONED,
      changeFrequency: 'monthly',
      priority: 0.8,
    },
    {
      url: `${baseUrl}/developers`,
      lastModified: REPOSITIONED,
      changeFrequency: 'weekly',
      priority: 0.8,
    },
    {
      url: `${baseUrl}/pricing`,
      lastModified: REPOSITIONED,
      changeFrequency: 'monthly',
      priority: 0.7,
    },
    {
      url: `${baseUrl}/compare`,
      lastModified: REPOSITIONED,
      changeFrequency: 'monthly',
      priority: 0.8,
    },
    {
      url: `${baseUrl}/blog`,
      lastModified: AGENTS_POST,
      changeFrequency: 'weekly',
      priority: 0.8,
    },
    {
      url: `${baseUrl}/blog/first-public-release`,
      lastModified: new Date('2026-01-06'),
      changeFrequency: 'yearly',
      priority: 0.6,
    },
    {
      url: `${baseUrl}/blog/evidence-research-for-agents`,
      lastModified: AGENTS_POST,
      changeFrequency: 'yearly',
      priority: 0.6,
    },
    {
      url: `${baseUrl}/contact`,
      lastModified: LEGAL_REFRESH,
      changeFrequency: 'monthly',
      priority: 0.5,
    },
    {
      url: `${baseUrl}/privacy-policy`,
      lastModified: LEGAL_REFRESH,
      changeFrequency: 'yearly',
      priority: 0.3,
    },
    {
      url: `${baseUrl}/terms-of-service`,
      lastModified: new Date('2026-03-09'),
      changeFrequency: 'yearly',
      priority: 0.3,
    },
    {
      url: `${baseUrl}/refund-policy`,
      lastModified: LEGAL_REFRESH,
      changeFrequency: 'yearly',
      priority: 0.3,
    },
    {
      url: `${baseUrl}/cookie-policy`,
      lastModified: new Date('2026-05-27'),
      changeFrequency: 'yearly',
      priority: 0.3,
    },
  ]
}
