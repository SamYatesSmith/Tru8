'use client';

interface ElementRefsProps {
  elementIds: string[];
  /** elementId → human description. When present, the chip shows the (truncated)
   * description instead of the cryptic "E01" code; the full text is the title. */
  descriptions?: Map<string, string>;
}

function truncate(s: string, n: number): string {
  return s.length > n ? `${s.slice(0, n - 1).trimEnd()}…` : s;
}

export function ElementRefs({ elementIds, descriptions }: ElementRefsProps) {
  if (!elementIds || elementIds.length === 0) return null;
  return (
    <span className="inline-flex flex-wrap items-center gap-1">
      {elementIds.map((id) => {
        const desc = descriptions?.get(id);
        const num = id.replace(/^e/i, '').padStart(2, '0');
        return (
          <span
            key={id}
            title={desc || undefined}
            className="font-mono text-[9px] text-zinc-600 border border-zinc-200 px-1 py-px leading-none max-w-[12rem] truncate"
          >
            {desc ? truncate(desc, 26) : `E${num}`}
          </span>
        );
      })}
    </span>
  );
}
