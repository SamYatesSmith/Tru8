'use client';

interface OrientationLineProps {
  orientation: string | null;
}

export function OrientationLine({ orientation }: OrientationLineProps) {
  if (orientation === null) {
    return null;
  }

  return (
    <div className="flex flex-col gap-1.5">
      <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400">
        ORIENTATION
      </span>
      <p className="text-sm font-medium text-zinc-700 leading-relaxed">{orientation}</p>
    </div>
  );
}
