'use client';

export function EmptyVideoState() {
  return (
    <div className="py-16 text-center">
      <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-400 mb-3">
        No relevant videos found
      </p>
      <p className="text-sm text-zinc-400">
        We searched for video content related to this claim but found no results
        that met our relevance criteria.
      </p>
    </div>
  );
}
