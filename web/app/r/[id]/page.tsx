/**
 * Public Report Page
 *
 * /r/[id] - Public view of a completed check
 * /r/[id]?claim=[n] - Scrolled/highlighted to specific claim
 *
 * No authentication required.
 * This is the landing page for all social shares.
 */

import { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { Navigation } from '@/components/layout/navigation';
import { MobileBottomNav } from '@/components/layout/mobile-bottom-nav';
import { Footer } from '@/components/layout/footer';
import { PublicReportClient } from './public-report-client';

interface PageProps {
  params: { id: string };
  searchParams: { claim?: string };
}

// Fetch public check data
async function getPublicCheck(id: string, detailed: boolean = false) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const url = `${apiUrl}/api/v1/checks/public/${id}${detailed ? '?detailed=true' : ''}`;

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
}

// Generate dynamic OG metadata
export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const check = await getPublicCheck(params.id, false);

  if (!check) {
    return {
      title: 'Report Not Found | Tru8',
      description: 'This evidence report could not be found.',
    };
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

  const ogImageUrl = `${process.env.NEXT_PUBLIC_BASE_URL || 'https://tru8.app'}/api/og/social/${params.id}`;

  return {
    title: `${title} | Tru8 Evidence Report`,
    description,
    openGraph: {
      title: `${title} | Tru8`,
      description,
      type: 'article',
      images: [ogImageUrl],
      siteName: 'Tru8',
    },
    twitter: {
      card: 'summary_large_image',
      title: `${title} | Tru8`,
      description,
      images: [ogImageUrl],
    },
  };
}

export default async function PublicReportPage({ params, searchParams }: PageProps) {
  // Fetch full check data for the report
  const check = await getPublicCheck(params.id, true);

  if (!check) {
    notFound();
  }

  return (
    <>
      {/* Navigation */}
      <Navigation />
      <MobileBottomNav />

      {/* Main Content */}
      <main className="min-h-screen bg-white pt-24 md:pt-32 pb-24 md:pb-20">
        <div className="container mx-auto px-4 md:px-6 max-w-4xl">
          <PublicReportClient
            check={check}
            highlightClaim={searchParams.claim ? parseInt(searchParams.claim, 10) : undefined}
          />
        </div>
      </main>

      {/* Footer */}
      <Footer />
    </>
  );
}
