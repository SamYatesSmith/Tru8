/**
 * Verdict Badge Component for OG Cards
 *
 * Displays SUPPORTED / CONTRADICTED / UNCERTAIN badge
 * Matches the Tailwind design: px-8 py-5 rounded-xl min-w-[300px]
 */

export type Verdict = 'supported' | 'contradicted' | 'uncertain';

export interface VerdictBadgeProps {
  verdict: Verdict;
}

const VERDICT_COLORS: Record<Verdict, string> = {
  supported: '#059669',
  contradicted: '#DC2626',
  uncertain: '#D97706',
};

const VERDICT_LABELS: Record<Verdict, string> = {
  supported: 'SUPPORTED',
  contradicted: 'CONTRADICTED',
  uncertain: 'UNCERTAIN',
};

export function VerdictBadge({ verdict }: VerdictBadgeProps) {
  const bgColor = VERDICT_COLORS[verdict];
  const label = VERDICT_LABELS[verdict];

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: bgColor,
        borderRadius: 12,
        padding: '20px 32px',
        gap: 4,
        minWidth: '200px',
      }}
    >
      <span
        style={{
          color: 'rgba(255, 255, 255, 0.9)',
          fontSize: 14,
          fontWeight: 900,
          letterSpacing: '0.15em',
          textTransform: 'uppercase',
        }}
      >
        Verdict
      </span>
      <span
        style={{
          color: '#FFFFFF',
          fontSize: 30,
          fontWeight: 700,
          lineHeight: 1,
        }}
      >
        {label}
      </span>
    </div>
  );
}
