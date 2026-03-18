import { ClaimElement } from '@shared/types';

interface CoverageMapProps {
  elements: ClaimElement[];
}

export function CoverageMap({ elements }: CoverageMapProps) {
  if (elements.length === 0) return null;

  const withEvidence = elements.filter(
    (el) => el.evidenceRefs && el.evidenceRefs.length > 0
  ).length;

  return (
    <div className="border border-zinc-200 p-4">
      <p className="font-mono text-xs font-bold uppercase tracking-widest text-zinc-500 mb-3">
        Coverage Map
      </p>
      <div className="h-4 flex gap-px">
        {elements.map((el) => {
          const isGap = !el.evidenceRefs || el.evidenceRefs.length === 0;
          const isUnresolved = el.state === 'unresolved' || !el.state;
          const segmentClass = isGap
            ? 'bg-zinc-100 border border-dashed border-zinc-300'
            : isUnresolved
              ? 'bg-zinc-300'
              : 'bg-zinc-600';
          return (
            <div
              key={el.elementId}
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
