interface GapHighlightProps {
  gapIndex?: number;
  totalGaps?: number;
}

export function GapHighlight({ gapIndex, totalGaps }: GapHighlightProps) {
  return (
    <div className="bg-zinc-100 border-2 border-dashed border-zinc-300 px-4 py-3 mb-3">
      <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-400">
        <span className="font-bold text-zinc-500">GAP</span>
        {typeof gapIndex === 'number' && typeof totalGaps === 'number' && (
          <>
            <span className="mx-1">&middot;</span>
            <span className="text-zinc-500">{gapIndex + 1} of {totalGaps}</span>
          </>
        )}
        <span className="mx-2">&middot;</span>
        No evidence found for this element
      </p>
    </div>
  );
}
