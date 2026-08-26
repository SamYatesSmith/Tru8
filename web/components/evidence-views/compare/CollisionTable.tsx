'use client';

import type { CollisionRow } from '@shared/types';
import { ElementBadge, elementNumberFromId } from '../ElementBadge';

/**
 * The mechanical element-by-element breakdown — computed server-side from
 * the LIVE claim map, never by the model, so every row here is verifiable
 * against the Evidence lens.
 *
 * NO COLOUR CARRIES MEANING. A `--divergence` amber token exists in
 * globals.css; it is deliberately not used — amber here would read as a
 * warning about the claim (no-verdict lock). OPPOSED earns bold weight,
 * nothing more.
 *
 * A real <table>: this is tabular data, not a layout grid.
 */
interface CollisionTableProps {
  rows: CollisionRow[];
  /** elementId → description, for the badge hover title. */
  descriptions?: Map<string, string>;
  domainA: string;
  domainB: string;
}

const VERDICT_LABELS: Record<CollisionRow['verdict'], string> = {
  opposed: 'OPPOSED',
  aligned: 'ALIGNED',
  only_a: 'ONLY A',
  only_b: 'ONLY B',
};

function relLabel(rel: string | null): string {
  return rel ?? 'not addressed';
}

export function CollisionTable({ rows, descriptions, domainA, domainB }: CollisionTableProps) {
  if (rows.length === 0) return null;

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse">
        <caption className="sr-only">
          Element-by-element positions of {domainA} and {domainB}
        </caption>
        <thead>
          <tr className="border-b border-zinc-200">
            <th scope="col" className="py-2 pr-3 text-left font-mono text-[9px] font-bold uppercase tracking-[0.25em] text-zinc-400">
              Element
            </th>
            <th scope="col" className="py-2 pr-3 text-left font-mono text-[9px] font-bold uppercase tracking-[0.25em] text-zinc-400">
              &nbsp;
            </th>
            <th scope="col" className="py-2 pr-3 text-left font-mono text-[9px] font-bold uppercase tracking-[0.25em] text-zinc-400">
              A &middot; {domainA}
            </th>
            <th scope="col" className="py-2 text-left font-mono text-[9px] font-bold uppercase tracking-[0.25em] text-zinc-400">
              B &middot; {domainB}
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const n = elementNumberFromId(row.elementId);
            const isOpposed = row.verdict === 'opposed';
            return (
              <tr key={row.elementId} className="border-b border-zinc-100">
                <td className="py-2 pr-3">
                  <span title={descriptions?.get(row.elementId)}>
                    <ElementBadge n={n} size="sm" />
                  </span>
                </td>
                <td className="py-2 pr-3">
                  <span
                    className={`font-mono text-[10px] tracking-wider ${
                      isOpposed ? 'font-bold text-zinc-900' : 'text-zinc-400'
                    }`}
                  >
                    {VERDICT_LABELS[row.verdict]}
                  </span>
                </td>
                <td className={`py-2 pr-3 font-mono text-[10px] italic ${row.a ? 'text-zinc-600' : 'text-zinc-300'}`}>
                  {relLabel(row.a)}
                </td>
                <td className={`py-2 font-mono text-[10px] italic ${row.b ? 'text-zinc-600' : 'text-zinc-300'}`}>
                  {relLabel(row.b)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
