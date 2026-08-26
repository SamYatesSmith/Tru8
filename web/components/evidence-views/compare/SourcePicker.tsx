'use client';

import type { Evidence } from '@shared/types';
import { PickerRow } from './PickerRow';

/**
 * The selectable list beneath the slots. SHOWN evidence only — the endpoint
 * enforces the same rule (comparing an excluded source would re-platform
 * something the pipeline filtered out with a receipt, design §7.6).
 */
interface SourcePickerProps {
  evidence: Evidence[];
  evidenceElementMap: Map<string, string[]>;
  elementDescriptions: Map<string, string>;
  placedIds: (string | null)[];
  disabled: boolean;
  onPlace: (evidenceId: string) => void;
}

export function SourcePicker({
  evidence,
  evidenceElementMap,
  elementDescriptions,
  placedIds,
  disabled,
  onPlace,
}: SourcePickerProps) {
  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <div className="flex-1 h-px bg-zinc-200" />
        <span className="font-mono text-[10px] font-bold uppercase tracking-widest text-zinc-500">
          Sources in this claim ({evidence.length})
        </span>
        <div className="flex-1 h-px bg-zinc-200" />
      </div>
      <div className="space-y-2">
        {evidence.map((ev) => {
          const id = ev.evidenceId || ev.id;
          return (
            <PickerRow
              key={id}
              evidence={ev}
              elementIds={evidenceElementMap.get(id) || []}
              elementDescriptions={elementDescriptions}
              placed={placedIds.includes(id)}
              disabled={disabled}
              onClick={() => onPlace(id)}
            />
          );
        })}
      </div>
    </div>
  );
}
