/**
 * Full Report Card - OG Image Component
 *
 * Displays a summary of the fact-check report with:
 * - Article title
 * - Stats (claims examined, sources analyzed, evidence pieces)
 * - Source quality breakdown
 * - Top sources list
 *
 * Size: 1200x630px (1.91:1 aspect ratio)
 *
 * Design reference: Screenshot 2026-01-28 125307.png
 */

import { Logo, StatsBlock, SourceList } from './shared';

export interface FullReportCardProps {
  title: string;
  sourceDomain?: string;
  claimsCount: number;
  sourcesCount: number;
  evidenceCount: number;
  credibilityScore?: number;
  topSources: string[];
  baseUrl?: string;
}

// Colors from the design
const COLORS = {
  primary: '#f27907',
  backgroundDark: '#0a0e12',
  backgroundGradient: 'radial-gradient(ellipse at bottom right, rgba(5, 46, 22, 0.15) 0%, #0a0e12 60%)',
  white: '#FFFFFF',
  white80: 'rgba(255, 255, 255, 0.8)',
  white40: 'rgba(255, 255, 255, 0.4)',
  white10: 'rgba(255, 255, 255, 0.1)',
  white05: 'rgba(255, 255, 255, 0.05)',
};

export function FullReportCard({
  title,
  sourceDomain,
  claimsCount,
  sourcesCount,
  evidenceCount,
  credibilityScore,
  topSources,
  baseUrl,
}: FullReportCardProps) {
  // Dynamic font sizing based on title length
  const titleLength = title.length;
  let fontSize: number;
  let maxChars: number;

  if (titleLength <= 40) {
    fontSize = 44;
    maxChars = 40;
  } else if (titleLength <= 60) {
    fontSize = 38;
    maxChars = 60;
  } else if (titleLength <= 80) {
    fontSize = 34;
    maxChars = 80;
  } else if (titleLength <= 110) {
    fontSize = 30;
    maxChars = 110;
  } else {
    // Fallback for very long titles: smallest font + truncate
    fontSize = 28;
    maxChars = 130;
  }

  const truncatedTitle = title.length > maxChars
    ? title.slice(0, maxChars - 3) + '...'
    : title;

  return (
    <div
      style={{
        width: '1200px',
        height: '630px',
        display: 'flex',
        flexDirection: 'column',
        background: COLORS.backgroundGradient,
        fontFamily: 'Inter, system-ui, sans-serif',
        padding: '40px 48px 24px 48px',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '32px',
        }}
      >
        <Logo size="medium" baseUrl={baseUrl} />

        {/* EVIDENCE REPORT badge */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            backgroundColor: COLORS.primary,
            borderRadius: 6,
            padding: '8px 16px',
          }}
        >
          <span
            style={{
              color: COLORS.white,
              fontSize: 12,
              fontWeight: 700,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
            }}
          >
            Evidence Report
          </span>
        </div>
      </div>

      {/* Title + Source */}
      <div style={{ marginBottom: '28px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {sourceDomain && (
          <span
            style={{
              color: COLORS.white40,
              fontSize: 14,
              fontWeight: 500,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            From {sourceDomain}
          </span>
        )}
        <span
          style={{
            color: COLORS.white,
            fontSize: fontSize,
            fontWeight: 700,
            lineHeight: 1.15,
          }}
        >
          &ldquo;{truncatedTitle}&rdquo;
        </span>
      </div>

      {/* Stats row */}
      <div
        style={{
          display: 'flex',
          gap: '64px',
          marginBottom: '40px',
        }}
      >
        <StatsBlock label="Claims Examined" value={claimsCount} />
        <StatsBlock label="Sources Analyzed" value={sourcesCount} />
        <StatsBlock label="Evidence Pieces" value={evidenceCount} />
      </div>

      {/* Bottom section: Credibility + Sources */}
      <div
        style={{
          display: 'flex',
          flex: 1,
          gap: '64px',
        }}
      >
        {/* Left: Average Source Credibility */}
        {credibilityScore !== undefined && (
          <div
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
            }}
          >
            <span
              style={{
                color: COLORS.white40,
                fontSize: 12,
                fontWeight: 700,
                letterSpacing: '0.15em',
                textTransform: 'uppercase',
              }}
            >
              Average Source Credibility
            </span>
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <span
                  style={{
                    color: COLORS.white,
                    fontSize: 16,
                    fontWeight: 600,
                  }}
                >
                  Based on {sourcesCount} sources analyzed
                </span>
                <span
                  style={{
                    color: COLORS.primary,
                    fontSize: 16,
                    fontWeight: 700,
                  }}
                >
                  {credibilityScore}%
                </span>
              </div>
              <div
                style={{
                  display: 'flex',
                  width: '100%',
                  height: '8px',
                  backgroundColor: 'rgba(255, 255, 255, 0.2)',
                  borderRadius: 4,
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    width: `${credibilityScore}%`,
                    height: '100%',
                    backgroundColor: COLORS.primary,
                    borderRadius: 4,
                  }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Right: Top Sources */}
        <div
          style={{
            width: '320px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
            marginBottom: '24px',
            marginRight: '-16px',
          }}
        >
          <span
            style={{
              color: COLORS.white40,
              fontSize: 12,
              fontWeight: 700,
              letterSpacing: '0.15em',
              textTransform: 'uppercase',
            }}
          >
            Sources Include
          </span>
          <SourceList sources={[...topSources.slice(0, 4), 'And many more']} />
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-end',
          justifyContent: 'space-between',
          paddingTop: '8px',
          borderTop: `1px solid ${COLORS.white05}`,
        }}
      >
        {/* CTA */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', lineHeight: 1, margin: 0, padding: 0 }}>
          <span
            style={{
              color: COLORS.white80,
              fontSize: 16,
              fontWeight: 500,
              lineHeight: 1,
            }}
          >
            Check out the full report
          </span>
          <span
            style={{
              color: COLORS.primary,
              fontSize: 18,
              fontWeight: 700,
              lineHeight: 1,
            }}
          >
            →
          </span>
        </div>

        {/* Tru8 wordmark */}
        <span
          style={{
            fontSize: 36,
            fontWeight: 700,
            letterSpacing: '-0.02em',
            color: COLORS.primary,
            lineHeight: 1,
            margin: 0,
            padding: 0,
          }}
        >
          Tru8
        </span>
      </div>
    </div>
  );
}
