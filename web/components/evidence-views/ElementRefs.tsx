'use client';

interface ElementRefsProps {
  elementIds: string[];
}

export function ElementRefs({ elementIds }: ElementRefsProps) {
  if (!elementIds || elementIds.length === 0) return null;
  return (
    <span className="inline-flex items-center gap-1">
      {elementIds.map((id) => {
        const num = id.replace(/^e/i, '').padStart(2, '0');
        return (
          <span
            key={id}
            className="font-mono text-[9px] font-bold text-zinc-700 border border-zinc-200 px-1 py-px leading-none"
          >
            E{num}
          </span>
        );
      })}
    </span>
  );
}
