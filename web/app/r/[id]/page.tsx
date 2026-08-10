/**
 * Public Report Page
 *
 * /r/[id] - Public view of a completed check
 * /r/[id]?claim=[n] - Scrolled/highlighted to specific claim
 *
 * No authentication required.
 * This is the landing page for all social shares.
 */

import { cache } from 'react';
import { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { Navigation } from '@/components/layout/navigation';
import { MobileBottomNav } from '@/components/layout/mobile-bottom-nav';
import { Footer } from '@/components/layout/footer';
import { PublicReportClient } from './public-report-client';

interface PageProps {
  params: { id: string };
  searchParams: { claim?: string; view?: string };
}

/**
 * Fetch the public check ONCE per request.
 *
 * This used to be called twice with DIFFERENT urls — generateMetadata asked for
 * the summary, the page body asked for `?detailed=true`. Two consequences, both
 * seen in production on 2026-08-03:
 *
 *  1. Two API round-trips on every single report view, for one page.
 *  2. The two calls could DISAGREE. Metadata could resolve "Report Not Found"
 *     while the body rendered a report, or vice versa, because nothing tied the
 *     two answers together.
 *
 * React's `cache` dedupes within a request, so metadata and body now see one
 * answer from one call. Detailed is the superset, so it serves both.
 */
const getPublicCheck = cache(async (id: string) => {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const url = `${apiUrl}/api/v1/checks/public/${id}?detailed=true`;

  try {
    const res = await fetch(url, {
      next: { revalidate: 60 }, // Cache for 60 seconds
    });

    if (!res.ok) {
      return null;
    }

    return res.json();
  } catch (error) {
    console.error('Failed to fetch public check:', error);
    return null;
  }
});

// Generate dynamic OG metadata
export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const check = await getPublicCheck(params.id);

  // A missing report must be a REAL 404, and the decision has to be made HERE.
  //
  // This previously returned a "Report Not Found" title and let the page body
  // call notFound() afterwards. By then rendering has begun and the response
  // headers are already committed, so Next could no longer change the status:
  // the page answered HTTP 200 carrying not-found content — a soft 404.
  //
  // That is how the sample report linked from the homepage hero, the closing CTA
  // and /compare stayed broken without anyone noticing: no uptime monitor treats
  // a 200 as an outage, and search engines index it as a valid page.
  //
  // generateMetadata runs BEFORE the page streams, so notFound() here yields a
  // genuine 404. (Unmatched routes like /nonexistent already 404 correctly;
  // only routes that match and then bail were affected.)
  if (!check) {
    notFound();
  }

  // Build dynamic title and description
  const title = check.title || 'Evidence Report';
  const claimsText = check.claimsCount === 1
    ? '1 claim analysed'
    : `${check.claimsCount} claims analysed`;
  const sourcesText = check.sourcesCount === 1
    ? '1 source'
    : `${check.sourcesCount} sources`;

  const description = `${claimsText} from ${sourcesText}. Explore the evidence landscape for this content.`;

  const ogImageUrl = `${process.env.NEXT_PUBLIC_BASE_URL || 'https://www.trueight.com'}/api/og/social/${params.id}`;

  const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'https://www.trueight.com';

  return {
    // No "| Tru8" here — the root layout template already appends it. Including
    // it produced "… | Tru8 Evidence Report | Tru8" in search results.
    title: `${title} — Evidence Report`,
    description,
    alternates: {
      canonical: `${baseUrl}/r/${params.id}`,
    },
    openGraph: {
      title: `${title} | Tru8`,
      description,
      type: 'article',
      url: `${baseUrl}/r/${params.id}`,
      images: [ogImageUrl],
      siteName: 'Tru8',
    },
    twitter: {
      card: 'summary_large_image',
      site: '@tru8app',
      title: `${title} | Tru8`,
      description,
      images: [ogImageUrl],
    },
  };
}

export default async function PublicReportPage({ params, searchParams }: PageProps) {
  // Deduped by React cache — generateMetadata already resolved this, and would
  // have 404'd before we got here. Kept as a belt-and-braces guard.
  const check = await getPublicCheck(params.id);

  if (!check) {
    notFound();
  }

  const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'https://www.trueight.com';
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    name: check.title || 'Evidence Research Report',
    description: `${check.claimsCount || 0} claims examined across ${check.sourcesCount || 0} sources`,
    url: `${baseUrl}/r/${params.id}`,
    datePublished: check.created_at,
    dateModified: check.completed_at || check.created_at,
    publisher: {
      '@type': 'Organization',
      name: 'Tru8',
      url: baseUrl,
      logo: {
        '@type': 'ImageObject',
        url: `${baseUrl}/icon-512.png`,
      },
    },
    mainEntity: {
      '@type': 'Dataset',
      name: 'Evidence Landscape',
      description: `Structured evidence collection: ${check.claimsCount || 0} claims, ${check.sourcesCount || 0} sources`,
    },
  };

  return (
    <>
      {/* Navigation */}
      <Navigation />
      <MobileBottomNav />

      {/* Main Content */}
      <main className="min-h-screen bg-white pt-24 md:pt-32 pb-24 md:pb-20">
        {/* JSON-LD inside main, not a direct body child — see app/page.tsx note */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, '\\u003c') }}
        />
        <div className="container mx-auto px-4 md:px-6 max-w-4xl">
          <PublicReportClient
            check={check}
            highlightClaim={searchParams.claim ? parseInt(searchParams.claim, 10) : undefined}
            highlightView={searchParams.view}
          />
        </div>
      </main>

      {/* Footer */}
      <Footer />
    </>
  );
}
