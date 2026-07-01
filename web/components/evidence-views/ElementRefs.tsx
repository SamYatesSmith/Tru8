'use client';

import { ElementBadge, elementNumberFromId } from './ElementBadge';

interface ElementRefsProps {
  elementIds: string[];
  /** elementId → human description, surfaced as the badge's hover title so the
   * reference stays terse (the full roster in the digest carries the wording). */
  descriptions?: Map<string, string>;
}

export function ElementRefs({ elementIds, descriptions }: ElementRefsProps) {
  if (!elementIds || elementIds.length === 0) return null;
  return (
    <span className="inline-flex flex-wrap items-center gap-1">
      {elementIds.map((id) => {
        const n = elementNumberFromId(id);
        const desc = descriptions?.get(id);
        return (
          <span key={id} title={desc || `Element ${String(n).padStart(2, '0')}`}>
            <ElementBadge n={n} size="sm" />
          </span>
        );
      })}
    </span>
  );
}
