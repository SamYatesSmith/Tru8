/**
 * Tru8 Logo Component for OG Cards
 *
 * Uses the actual logo.proper.png image
 *
 * Design reference: socials/share-cards-progress.md
 */

export interface LogoProps {
  size?: 'small' | 'medium' | 'large' | 'xlarge' | 'footer';
  baseUrl?: string; // Required for fetching the logo image
}

export function Logo({ size = 'small', baseUrl }: LogoProps) {
  // Size configurations
  const sizeConfig = {
    footer: { image: 28, font: 16, gap: 6 },
    small: { image: 32, font: 20, gap: 8 },
    medium: { image: 45, font: 26, gap: 10 },  // 40% larger than small
    large: { image: 80, font: 36, gap: 12 },
    xlarge: { image: 180, font: 48, gap: 16 },
  };

  const config = sizeConfig[size];
  const imageSize = config.image;
  const fontSize = config.font;
  const gap = config.gap;

  // Construct the logo URL
  const logoUrl = baseUrl ? `${baseUrl}/logo.proper.png` : '/logo.proper.png';

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: gap,
      }}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={logoUrl}
        width={imageSize}
        height={imageSize}
        style={{
          objectFit: 'contain',
        }}
        alt="Tru8"
      />
      {size === 'small' && (
        <span
          style={{
            color: '#FFFFFF',
            fontSize: fontSize,
            fontWeight: 700,
            letterSpacing: '0.02em',
          }}
        >
          Tru8
        </span>
      )}
    </div>
  );
}
