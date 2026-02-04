/**
 * Source List Component for OG Cards
 *
 * Displays a list of top sources with neutral bullets (not green checkmarks)
 *
 * Design reference: Full Report Card mockup
 */

export interface SourceListProps {
  sources: string[];
}

const COLORS = {
  white: '#FFFFFF',
  white60: 'rgba(255, 255, 255, 0.6)',
};

export function SourceList({ sources }: SourceListProps) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
      }}
    >
      {sources.map((source, idx) => (
        <div
          key={idx}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          {/* Neutral bullet */}
          <div
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              backgroundColor: COLORS.white60,
              flexShrink: 0,
            }}
          />
          <span
            style={{
              color: COLORS.white,
              fontSize: 16,
              fontWeight: 500,
            }}
          >
            {source}
          </span>
        </div>
      ))}
    </div>
  );
}
