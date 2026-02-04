/**
 * Social Share Card - OG Image Component
 *
 * Optimised for mobile social platforms:
 * - WhatsApp (~300px)
 * - X mobile (~320-420px)
 * - LinkedIn feed (~400-500px)
 *
 * Prioritises: Big headline → 1 metric → brand → CTA
 *
 * Size: 1200x630px (renders large, scales down well)
 */

export interface SocialShareCardProps {
  headline: string;
  metricValue: string | number;
  metricLabel: string;
  ctaText?: string;
  baseUrl?: string;
}

// Colors
const COLORS = {
  primary: '#f27907',
  backgroundGradient: 'radial-gradient(ellipse at bottom right, rgba(5, 46, 22, 0.15) 0%, #0a0e12 60%)',
  white: '#FFFFFF',
  white60: 'rgba(255, 255, 255, 0.6)',
  white40: 'rgba(255, 255, 255, 0.4)',
};

export function SocialShareCard({
  headline,
  metricValue,
  metricLabel,
  ctaText = 'See the evidence',
  baseUrl,
}: SocialShareCardProps) {
  // Dynamic font size for headline
  const headlineLength = headline.length;
  const headlineFontSize = headlineLength <= 30 ? 72 : headlineLength <= 50 ? 60 : headlineLength <= 70 ? 52 : 44;

  // Construct logo URL
  const logoUrl = baseUrl ? `${baseUrl}/logo.proper.png` : '/logo.proper.png';

  return (
    <div
      style={{
        width: '1200px',
        height: '630px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: COLORS.backgroundGradient,
        fontFamily: 'Inter, system-ui, sans-serif',
        padding: '60px 80px',
        textAlign: 'center',
      }}
    >
      {/* Logo at top */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          marginBottom: '40px',
        }}
      >
        <img
          src={logoUrl}
          width={50}
          height={50}
          style={{ objectFit: 'contain' }}
          alt="Tru8"
        />
        <span
          style={{
            fontSize: 32,
            fontWeight: 700,
            color: COLORS.primary,
          }}
        >
          Tru8
        </span>
      </div>

      {/* Main headline - BIG */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          marginBottom: '48px',
          maxWidth: '1000px',
        }}
      >
        <span
          style={{
            color: COLORS.white,
            fontSize: headlineFontSize,
            fontWeight: 700,
            lineHeight: 1.1,
            textAlign: 'center',
          }}
        >
          {headline}
        </span>
      </div>

      {/* Single metric - prominent */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '8px',
          marginBottom: '48px',
        }}
      >
        <span
          style={{
            color: COLORS.primary,
            fontSize: 96,
            fontWeight: 700,
            lineHeight: 1,
          }}
        >
          {metricValue}
        </span>
        <span
          style={{
            color: COLORS.white60,
            fontSize: 24,
            fontWeight: 500,
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
          }}
        >
          {metricLabel}
        </span>
      </div>

      {/* CTA */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
        }}
      >
        <span
          style={{
            color: COLORS.white,
            fontSize: 28,
            fontWeight: 600,
          }}
        >
          {ctaText}
        </span>
        <span
          style={{
            color: COLORS.primary,
            fontSize: 32,
            fontWeight: 700,
          }}
        >
          →
        </span>
      </div>
    </div>
  );
}
