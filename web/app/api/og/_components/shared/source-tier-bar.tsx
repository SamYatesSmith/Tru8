/**
 * Source Tier Bar Component for OG Cards
 *
 * Displays a source tier with label, progress bar, and percentage
 */

export interface SourceTierBarProps {
  label: string;
  description?: string;
  percentage: number;
}

const COLORS = {
  primary: '#f27907',
  text: '#18181b',
  textMuted: '#a1a1aa',
  barBg: '#e4e4e7',
};

export function SourceTierBar({ label, description, percentage }: SourceTierBarProps) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        width: '100%',
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
            color: COLORS.text,
            fontSize: 16,
            fontWeight: 600,
          }}
        >
          {label}
        </span>
        <span
          style={{
            color: COLORS.primary,
            fontSize: 16,
            fontWeight: 700,
          }}
        >
          {percentage}%
        </span>
      </div>

      <div
        style={{
          display: 'flex',
          width: '100%',
          height: '8px',
          backgroundColor: COLORS.barBg,
          borderRadius: 4,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: `${percentage}%`,
            height: '100%',
            backgroundColor: COLORS.primary,
            borderRadius: 4,
          }}
        />
      </div>

      {description && (
        <span
          style={{
            color: COLORS.textMuted,
            fontSize: 11,
            fontWeight: 500,
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
          }}
        >
          {description}
        </span>
      )}
    </div>
  );
}
