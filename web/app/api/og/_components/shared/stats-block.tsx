/**
 * Stats Block Component for OG Cards
 *
 * Displays a stat with label above and large orange number below
 * e.g., "CLAIMS EXAMINED" with "8"
 *
 * Design reference: Full Report Card mockup
 */

export interface StatsBlockProps {
  label: string;
  value: number | string;
}

const COLORS = {
  primary: '#f27907',
  white40: 'rgba(255, 255, 255, 0.4)',
};

export function StatsBlock({ label, value }: StatsBlockProps) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
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
        {label}
      </span>
      <span
        style={{
          color: COLORS.primary,
          fontSize: 64,
          fontWeight: 700,
          lineHeight: 1,
        }}
      >
        {value}
      </span>
    </div>
  );
}
