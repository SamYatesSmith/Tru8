/**
 * Source Tier Bar Component for OG Cards
 *
 * Displays a source tier with label, progress bar, and percentage
 * e.g., "Health Authorities" with 65% bar
 *
 * Design reference: Full Report Card mockup
 */

export interface SourceTierBarProps {
  label: string;
  description?: string;
  percentage: number;
}

const COLORS = {
  primary: '#f27907',
  white: '#FFFFFF',
  white20: 'rgba(255, 255, 255, 0.2)',
  white40: 'rgba(255, 255, 255, 0.4)',
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
      {/* Label and percentage row */}
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

      {/* Progress bar */}
      <div
        style={{
          display: 'flex',
          width: '100%',
          height: '8px',
          backgroundColor: COLORS.white20,
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

      {/* Description */}
      {description && (
        <span
          style={{
            color: COLORS.white40,
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
