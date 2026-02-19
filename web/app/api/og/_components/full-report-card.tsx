/**
 * Full Report Card - OG Image Component
 *
 * Displays a summary of the evidence report with:
 * - Article title
 * - Stats (claims examined, sources analyzed, evidence pieces)
 * - Top sources list
 *
 * Size: 1200x630px (1.91:1 aspect ratio)
 */

import { Logo, StatsBlock, SourceList } from './shared';

export interface FullReportCardProps {
  title: string;
  sourceDomain?: string;
  claimsCount: number;
  sourcesCount: number;
  evidenceCount: number;
  topSources: string[];
  baseUrl?: string;
}

const COLORS = {
  primary: '#f27907',
  background: '#ffffff',
  text: '#18181b',
  textSecondary: '#71717a',
  textMuted: '#a1a1aa',
  border: '#e4e4e7',
  borderLight: '#f4f4f5',
};

export function FullReportCard({
  title,
  sourceDomain,
  claimsCount,
  sourcesCount,
  evidenceCount,
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
        background: COLORS.background,
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
              color: '#ffffff',
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
              color: COLORS.textMuted,
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
            color: COLORS.text,
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

      {/* Bottom section: Sources */}
      <div
        style={{
          display: 'flex',
          flex: 1,
          gap: '64px',
        }}
      >
        {/* Top Sources */}
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
              color: COLORS.textMuted,
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
          borderTop: `1px solid ${COLORS.border}`,
        }}
      >
        {/* CTA */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', lineHeight: 1, margin: 0, padding: 0 }}>
          <span
            style={{
              color: COLORS.textSecondary,
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
