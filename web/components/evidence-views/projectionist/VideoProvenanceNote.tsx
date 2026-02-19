'use client';

export function VideoProvenanceNote() {
  return (
    <div className="border-t border-zinc-100 pt-4 mb-8">
      <p className="font-mono text-[10px] text-zinc-300 leading-relaxed">
        Videos retrieved via YouTube Data API. Classification (tier + type) is descriptive, not evaluative.
        Video content is hosted externally and not controlled by Tru8.
      </p>
    </div>
  );
}
