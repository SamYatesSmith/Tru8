import { Check, Minus, HelpCircle } from 'lucide-react';
import { CAPTURE_DATE } from './demo-data';

/**
 * Capability table — rows and cell judgements exactly from the 2026-06-12 gap
 * analysis (audit/2026-06-12_gap_analysis/TRU8-GAP-ANALYSIS.md), verified
 * against official documentation and the live captures on this page.
 */

type Mark = 'yes' | 'no' | 'unknown' | 'text';

interface Cell {
  mark: Mark;
  note?: string;
}

interface Row {
  capability: string;
  cells: [Cell, Cell, Cell, Cell, Cell]; // Tru8 / Web IQ / Google / Perplexity / Parallel
}

const COLUMNS = ['Tru8', 'Web IQ', 'Google check-grounding', 'Perplexity', 'Parallel'];

const ROWS: Row[] = [
  {
    capability: 'Retrieves evidence',
    cells: [
      { mark: 'yes', note: 'Web + specialist APIs' },
      { mark: 'yes', note: 'Bing index' },
      { mark: 'no', note: 'caller supplies facts' },
      { mark: 'yes' },
      { mark: 'yes' },
    ],
  },
  {
    capability: 'Per-source classification',
    cells: [
      { mark: 'yes', note: 'tier × type' },
      { mark: 'no', note: 'undisclosed authority rank' },
      { mark: 'no' },
      { mark: 'no', note: 'none in Search API; Sonar has a web|attachment enum' },
      { mark: 'no' },
    ],
  },
  {
    capability: 'Claim → element decomposition',
    cells: [
      { mark: 'yes', note: '1–5 elements' },
      { mark: 'no' },
      { mark: 'unknown', note: 'partial — claim spans' },
      { mark: 'no' },
      { mark: 'no', note: 'output fields, not claim elements' },
    ],
  },
  {
    capability: 'Supports / challenges relationships',
    cells: [
      { mark: 'yes' },
      { mark: 'no' },
      { mark: 'no', note: 'supports-only schema' },
      { mark: 'no' },
      { mark: 'no' },
    ],
  },
  {
    capability: 'Dispute / unresolved states',
    cells: [
      { mark: 'yes' },
      { mark: 'no' },
      { mark: 'no', note: 'computed internally, not exposed in the API' },
      { mark: 'no' },
      { mark: 'no' },
    ],
  },
  {
    capability: 'Evidence gaps named',
    cells: [{ mark: 'yes' }, { mark: 'no' }, { mark: 'no' }, { mark: 'no' }, { mark: 'no' }],
  },
  {
    capability: 'Exclusion receipts',
    cells: [{ mark: 'yes' }, { mark: 'no' }, { mark: 'no' }, { mark: 'no' }, { mark: 'no' }],
  },
  {
    capability: 'Archived source URLs',
    cells: [{ mark: 'yes' }, { mark: 'no' }, { mark: 'no' }, { mark: 'no' }, { mark: 'no' }],
  },
  {
    capability: 'Signed manifest + public verify URL',
    cells: [
      { mark: 'yes' },
      { mark: 'unknown', note: '"provenance" mentioned, schema gated' },
      { mark: 'no' },
      { mark: 'no' },
      { mark: 'no' },
    ],
  },
  {
    capability: 'Per-citation excerpts',
    cells: [
      { mark: 'yes' },
      { mark: 'unknown', note: 'unverified' },
      { mark: 'yes', note: 'citedChunks' },
      { mark: 'yes', note: 'snippets' },
      { mark: 'yes', note: 'Basis excerpts' },
    ],
  },
  {
    capability: 'Latency',
    cells: [
      { mark: 'text', note: '15–90s (this capture: 40.4s) — different layer, not a faster horse' },
      { mark: 'text', note: '<165ms p95 (vendor claim)' },
      { mark: 'text', note: '<500ms documented (this capture: 2.8s)' },
      { mark: 'text', note: 'seconds (this capture: 1.0s)' },
      { mark: 'text', note: 'seconds–minutes (this capture: 4m 40s on core)' },
    ],
  },
];

function CellContent({ cell, isTru8 }: { cell: Cell; isTru8: boolean }) {
  return (
    <span className="inline-flex items-start gap-1.5">
      {cell.mark === 'yes' && (
        <Check size={14} className="text-accent shrink-0 mt-0.5" aria-label="Yes" />
      )}
      {cell.mark === 'no' && (
        <Minus size={14} className="text-zinc-500 shrink-0 mt-0.5" aria-label="No" />
      )}
      {cell.mark === 'unknown' && (
        <HelpCircle size={14} className="text-zinc-500 shrink-0 mt-0.5" aria-label="Unverified" />
      )}
      {cell.note && (
        <span className={`text-xs leading-snug ${isTru8 ? 'text-zinc-900' : 'text-zinc-500'}`}>
          {cell.note}
        </span>
      )}
    </span>
  );
}

export function ComparisonTable() {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left border-collapse min-w-[760px]">
        <thead>
          <tr className="border-b border-zinc-200">
            <th className="py-3 pr-4 font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-400 font-medium">
              Capability
            </th>
            {COLUMNS.map((col, i) => (
              <th
                key={col}
                className={`py-3 px-3 font-mono text-[10px] tracking-[0.2em] uppercase font-medium ${
                  i === 0 ? 'text-zinc-900' : 'text-zinc-400'
                }`}
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ROWS.map((row) => (
            <tr key={row.capability} className="border-b border-zinc-200">
              <td className="py-3.5 pr-4 text-sm text-zinc-900 font-medium align-top">
                {row.capability}
              </td>
              {row.cells.map((cell, i) => (
                <td key={i} className={`py-3.5 px-3 align-top ${i === 0 ? 'bg-zinc-50/60' : ''}`}>
                  <CellContent cell={cell} isTru8={i === 0} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>

      <p className="mt-4 font-mono text-[10px] tracking-wider uppercase text-zinc-400 leading-relaxed">
        Capabilities verified against official documentation and live API responses, captured{' '}
        {CAPTURE_DATE}. Sources linked per panel below.
      </p>
    </div>
  );
}
