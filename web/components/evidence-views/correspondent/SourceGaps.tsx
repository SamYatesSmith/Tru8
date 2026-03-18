'use client';

interface SourceGap {
  type: string;
  message: string;
}

interface SourceGapsProps {
  gaps: SourceGap[];
}

export function SourceGaps({ gaps }: SourceGapsProps) {
  if (gaps.length === 0) return null;

  return (
    <div className="space-y-3 mt-8">
      {gaps.map((gap, i) => (
        <div key={i} className="border border-dashed border-zinc-200 bg-zinc-50/30 p-4">
          <div className="font-mono text-[10px] uppercase tracking-widest text-zinc-400 mb-1">
            Source Diversity Note
          </div>
          <div className="text-sm text-zinc-500">{gap.message}</div>
        </div>
      ))}
    </div>
  );
}
