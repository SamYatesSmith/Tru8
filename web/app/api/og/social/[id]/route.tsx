/**
 * Social Share Card OG Image Endpoint
 *
 * GET /api/og/social/[id]
 * Returns a PNG image optimized for mobile social platforms.
 *
 * Query params for marketing customization:
 * - headline: Custom headline text (default: article title or "Fact-Checked Report")
 * - metricValue: The big metric number (default: sources count)
 * - metricLabel: Label below metric (default: "Sources Verified")
 * - cta: Call-to-action text (default: "See the evidence")
 */

import { ImageResponse } from '@vercel/og';
import { SocialShareCard } from '../../_components';

export const runtime = 'edge';

// Cache the image for 1 hour
export const revalidate = 3600;

interface PublicCheckData {
  id: string;
  title?: string;
  sourceDomain?: string;
  claimsCount: number;
  sourcesCount: number;
  evidenceCount: number;
  topSources: string[];
}

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const url = new URL(request.url);
    const baseUrl = `${url.protocol}//${url.host}`;

    // Get query params for customization
    const customHeadline = url.searchParams.get('headline');
    const customMetricValue = url.searchParams.get('metricValue');
    const customMetricLabel = url.searchParams.get('metricLabel');
    const customCta = url.searchParams.get('cta');

    // Fetch public check data from backend API
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const response = await fetch(`${apiUrl}/api/v1/checks/public/${id}`, {
      headers: {
        'Content-Type': 'application/json',
      },
      next: { revalidate: 300 },
    });

    if (!response.ok) {
      return new ImageResponse(
        <div
          style={{
            width: '1200px',
            height: '630px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: '#0a0e12',
            color: '#ffffff',
            fontSize: 32,
            fontFamily: 'Inter, system-ui, sans-serif',
          }}
        >
          Report not found
        </div>,
        { width: 1200, height: 630 }
      );
    }

    const check: PublicCheckData = await response.json();

    // Use custom values or defaults from check data
    const headline = customHeadline || check.title || 'Fact-Checked Report';
    const metricValue = customMetricValue || check.sourcesCount.toString();
    const metricLabel = customMetricLabel || 'Sources Verified';
    const ctaText = customCta || 'See the evidence';

    // Render SocialShareCard
    return new ImageResponse(
      <SocialShareCard
        headline={headline}
        metricValue={metricValue}
        metricLabel={metricLabel}
        ctaText={ctaText}
        baseUrl={baseUrl}
      />,
      {
        width: 1200,
        height: 630,
      }
    );
  } catch (error) {
    console.error('Social OG Image generation error:', error);

    return new ImageResponse(
      <div
        style={{
          width: '1200px',
          height: '630px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#0a0e12',
          color: '#ffffff',
          fontSize: 32,
          fontFamily: 'Inter, system-ui, sans-serif',
        }}
      >
        Unable to generate image
      </div>,
      { width: 1200, height: 630 }
    );
  }
}
