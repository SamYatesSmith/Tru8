/**
 * Source List Component for OG Cards
 *
 * Displays a list of top sources with neutral bullets
 */

export interface SourceListProps {
  sources: string[];
}

const COLORS = {
  text: '#18181b',
  textSecondary: '#71717a',
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
          <div
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              backgroundColor: COLORS.textSecondary,
              flexShrink: 0,
            }}
          />
          <span
            style={{
              color: COLORS.text,
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
