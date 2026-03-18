interface ChronologistProvenanceNoteProps {
  hasUndated?: boolean;
}

export function ChronologistProvenanceNote({ hasUndated }: ChronologistProvenanceNoteProps) {
  return (
    <div className="border-t border-zinc-100 pt-4 mb-8">
      <p className="font-mono text-[10px] text-zinc-300 leading-relaxed">
        Dates are extracted from source metadata. Not all sources include publication dates.
        {hasUndated
          ? ' Sources without dates appear in the \u201CDate Unknown\u201D section.'
          : ' All sources in this analysis have publication dates.'}
      </p>
    </div>
  );
}
