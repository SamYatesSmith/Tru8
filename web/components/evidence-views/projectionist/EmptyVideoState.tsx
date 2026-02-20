'use client';

export function EmptyVideoState() {
  return (
    <div className="py-16 text-center">
      <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-400 mb-3">
        No relevant videos found
      </p>
      <p className="text-sm text-zinc-400">
        No videos found matching this claim.
      </p>
    </div>
  );
}
