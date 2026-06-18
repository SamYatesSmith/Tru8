import type { MetadataRoute } from 'next'

const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'https://www.trueight.com'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      // Allow the dynamic OG image routes even though /api/ is otherwise blocked,
      // so social/link unfurlers can fetch share-card images.
      allow: ['/', '/api/og/'],
      disallow: ['/dashboard/', '/api/', '/sign-in/', '/sign-up/'],
    },
    sitemap: `${baseUrl}/sitemap.xml`,
  }
}
