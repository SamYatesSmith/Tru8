/**
 * Stats Block Component for OG Cards
 *
 * Displays a stat with label above and large orange number below
 */

export interface StatsBlockProps {
  label: string;
  value: number | string;
}

const COLORS = {
  primary: '#f27907',
  textMuted: '#a1a1aa',
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
          color: COLORS.textMuted,
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
