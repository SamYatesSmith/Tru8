/**
 * Full Report Card OG Image Endpoint
 *
 * GET /api/og/check/[id]
 * Returns a PNG image for the full report card.
 *
 * Used for social media link previews (X, LinkedIn, WhatsApp).
 */

import { ImageResponse } from '@vercel/og';
import { FullReportCard } from '../../_components';

export const runtime = 'edge';

// Cache the image for 1 hour
export const revalidate = 3600;

interface PublicCheckData {
  id: string;
  title?: string;
  sourceUrl?: string;
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

    // Get base URL for assets
    const url = new URL(request.url);
    const baseUrl = `${url.protocol}//${url.host}`;

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
            backgroundColor: '#0f1419',
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

    // Render FullReportCard
    return new ImageResponse(
      <FullReportCard
        title={check.title || 'Evidence Report'}
        sourceDomain={check.sourceDomain}
        claimsCount={check.claimsCount}
        sourcesCount={check.sourcesCount}
        evidenceCount={check.evidenceCount}
        topSources={check.topSources}
        baseUrl={baseUrl}
      />,
      {
        width: 1200,
        height: 630,
      }
    );
  } catch (error) {
    console.error('OG Image generation error:', error);

    return new ImageResponse(
      <div
        style={{
          width: '1200px',
          height: '630px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#0f1419',
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
