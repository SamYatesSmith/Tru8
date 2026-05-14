'use client';

import { DiagnosticFlag } from '../DiagnosticFlag';

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
    <div className="space-y-4 mb-8">
      {gaps.map((gap, i) => (
        <DiagnosticFlag key={i} label="Diversity note">{gap.message}</DiagnosticFlag>
      ))}
    </div>
  );
}
