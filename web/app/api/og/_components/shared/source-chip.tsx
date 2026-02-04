/**
 * Source Chip Component for OG Cards
 *
 * Matches the Tailwind design:
 * bg-white/5 border border-white/10 rounded-lg px-6 py-3 min-w-[120px]
 */

export interface SourceChipProps {
  name: string;
}

export function SourceChip({ name }: SourceChipProps) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'rgba(255, 255, 255, 0.05)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        borderRadius: 8,
        padding: '12px 24px',
        minWidth: '120px',
      }}
    >
      <span
        style={{
          color: '#FFFFFF',
          fontSize: 16,
          fontWeight: 600,
        }}
      >
        {name}
      </span>
    </div>
  );
}

export interface MoreChipProps {
  count: number;
}

export function MoreChip({ count }: MoreChipProps) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'rgba(255, 255, 255, 0.05)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        borderRadius: 8,
        padding: '12px 24px',
      }}
    >
      <span
        style={{
          color: 'rgba(255, 255, 255, 0.6)',
          fontSize: 14,
          fontWeight: 500,
        }}
      >
        +{count} more
      </span>
    </div>
  );
}
