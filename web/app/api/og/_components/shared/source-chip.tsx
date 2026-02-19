/**
 * Source Chip Component for OG Cards
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
        backgroundColor: '#f4f4f5',
        border: '1px solid #e4e4e7',
        borderRadius: 8,
        padding: '12px 24px',
        minWidth: '120px',
      }}
    >
      <span
        style={{
          color: '#18181b',
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
        backgroundColor: '#f4f4f5',
        border: '1px solid #e4e4e7',
        borderRadius: 8,
        padding: '12px 24px',
      }}
    >
      <span
        style={{
          color: '#71717a',
          fontSize: 14,
          fontWeight: 500,
        }}
      >
        +{count} more
      </span>
    </div>
  );
}
