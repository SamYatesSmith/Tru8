'use client';

import { Evidence } from '@shared/types';
import { EvidenceGroupCard } from './EvidenceGroupCard';

interface EvidenceGroupsProps {
  supports: Evidence[];
  challenges: Evidence[];
  context: Evidence[];
  onCardClick?: (evidence: Evidence) => void;
}

function sortByDate(items: Evidence[]): Evidence[] {
  return [...items].sort((a, b) => {
    const da = a.publishedDate ? new Date(a.publishedDate).getTime() : 0;
    const db = b.publishedDate ? new Date(b.publishedDate).getTime() : 0;
    return db - da;
  });
}

export function EvidenceGroups({ supports, challenges, context, onCardClick }: EvidenceGroupsProps) {
  const sortedSupports = sortByDate(supports);
  const sortedChallenges = sortByDate(challenges);
  const sortedContext = sortByDate(context);

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
      {/* SUPPORTS Column */}
      <div>
        <div className="flex items-center gap-2 mb-4 pb-2 border-b border-emerald-200">
          <div className="w-[2px] h-4" style={{ background: 'var(--disposition-supports)' }}></div>
          <span className="font-mono text-[10px] uppercase tracking-[0.3em] font-bold" style={{ color: 'var(--disposition-supports)' }}>
            Supports
          </span>
        </div>
        {sortedSupports.length > 0 ? (
          sortedSupports.map((ev) => (
            <EvidenceGroupCard
              key={ev.id}
              evidence={ev}
              accentStyle="border-l-2 border-l-emerald-100"
              onClick={() => onCardClick?.(ev)}
            />
          ))
        ) : (
          <p className="font-mono text-[10px] text-zinc-300 uppercase tracking-widest">
            No sources support this element
          </p>
        )}
      </div>

      {/* CHALLENGES Column */}
      <div>
        <div className="flex items-center gap-2 mb-4 pb-2 border-b border-amber-200">
          <div className="w-[2px] h-4" style={{ background: 'var(--disposition-challenges)' }}></div>
          <span className="font-mono text-[10px] uppercase tracking-[0.3em] font-bold" style={{ color: 'var(--disposition-challenges)' }}>
            Challenges
          </span>
        </div>
        {sortedChallenges.length > 0 ? (
          sortedChallenges.map((ev) => (
            <EvidenceGroupCard
              key={ev.id}
              evidence={ev}
              accentStyle="border-l-2 border-l-amber-100 bg-amber-50/20"
              onClick={() => onCardClick?.(ev)}
            />
          ))
        ) : (
          <p className="font-mono text-[10px] text-zinc-300 uppercase tracking-widest">
            No sources challenge this element
          </p>
        )}
      </div>

      {/* CONTEXT Column */}
      <div>
        <div className="flex items-center gap-2 mb-4 pb-2 border-b border-zinc-200">
          <div className="w-[2px] h-4 bg-zinc-300"></div>
          <span className="font-mono text-[10px] uppercase tracking-[0.3em] text-zinc-500 font-bold">
            Context
          </span>
        </div>
        {sortedContext.length > 0 ? (
          sortedContext.map((ev) => (
            <EvidenceGroupCard
              key={ev.id}
              evidence={ev}
              onClick={() => onCardClick?.(ev)}
            />
          ))
        ) : (
          <p className="font-mono text-[10px] text-zinc-300 uppercase tracking-widest">
            No contextual sources for this element
          </p>
        )}
      </div>
    </div>
  );
}
