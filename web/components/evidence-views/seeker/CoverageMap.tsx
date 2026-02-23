import { ClaimElement, EvidenceRelationship } from '@shared/types';

interface CoverageMapProps {
  elements: ClaimElement[];
}

const RELATIONSHIPS: EvidenceRelationship[] = ['supports', 'challenges', 'context'];
const RELATIONSHIP_LABELS: Record<EvidenceRelationship, string> = {
  supports: 'SUP',
  challenges: 'CHL',
  context: 'CTX',
};

function getCellClass(count: number): string {
  if (count === 0) return 'bg-zinc-50';
  if (count === 1) return 'bg-zinc-200';
  if (count === 2) return 'bg-zinc-300';
  return 'bg-zinc-400';
}

export function CoverageMap({ elements }: CoverageMapProps) {
  if (elements.length === 0) return null;

  // Build count matrix: element × relationship
  const matrix = elements.map((el) => {
    const counts: Record<string, number> = { supports: 0, challenges: 0, context: 0 };
    for (const ref of el.evidenceRefs || []) {
      const rel = ref.relationship || 'context';
      if (rel in counts) counts[rel]++;
    }
    return counts;
  });

  return (
    <div className="border border-zinc-200 p-4">
      <p className="font-mono text-[9px] uppercase tracking-widest text-zinc-400 mb-3">
        Coverage Map
      </p>
      <div
        className="inline-grid gap-px"
        style={{ gridTemplateColumns: 'auto repeat(3, 1fr)' }}
      >
        {/* Header row */}
        <div />
        {RELATIONSHIPS.map((rel) => (
          <div key={`header-${rel}`} className="px-2 py-1 text-center">
            <span className="font-mono text-[8px] uppercase tracking-widest text-zinc-400">
              {RELATIONSHIP_LABELS[rel]}
            </span>
          </div>
        ))}

        {/* Data rows */}
        {elements.map((el, i) => (
          <>
            <div key={`label-${el.elementId}`} className="px-2 py-1 flex items-center">
              <span className="font-mono text-[9px] font-bold text-zinc-400">e{i + 1}</span>
            </div>
            {RELATIONSHIPS.map((rel) => {
              const count = matrix[i][rel];
              return (
                <div
                  key={`${el.elementId}-${rel}`}
                  className={`w-8 h-6 ${getCellClass(count)} flex items-center justify-center`}
                >
                  {count > 0 && (
                    <span className="font-mono text-[9px] text-zinc-600 font-bold">{count}</span>
                  )}
                </div>
              );
            })}
          </>
        ))}
      </div>
    </div>
  );
}
