import { ClaimElement } from '@shared/types';
import { evidenceCoverage, needsEvidenceReview } from '@/lib/evidence-coverage';

interface CoverageMapProps {
  elements: ClaimElement[];
}

export function CoverageMap({ elements }: CoverageMapProps) {
  if (elements.length === 0) return null;

  const { withEvidence } = evidenceCoverage(elements);

  return (
    <div className="border border-zinc-200 p-4">
      <p className="font-mono text-xs font-bold uppercase tracking-widest text-zinc-500 mb-3">
        Coverage Map
      </p>
      <div className="h-4 flex gap-px">
        {elements.map((el) => {
          const isGap = !el.evidenceRefs || el.evidenceRefs.length === 0;
          const isUnresolved = needsEvidenceReview(el);
          const segmentClass = isGap
            ? 'bg-zinc-100 border border-dashed border-zinc-300'
            : isUnresolved
              ? 'bg-zinc-300'
              : 'bg-zinc-600';
          return (
            <div
              key={el.elementId}
              title={`${el.description}: ${isGap ? 'no mapped evidence' : isUnresolved ? 'needs review' : 'supporting evidence mapped'}`}
              className={`flex-1 ${segmentClass}`}
            />
          );
        })}
      </div>
      <p className="font-mono text-[10px] text-zinc-400 mt-2">
        {withEvidence} of {elements.length} elements have evidence
      </p>
    </div>
  );
}
