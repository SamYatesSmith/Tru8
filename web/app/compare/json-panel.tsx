import type { ReactNode } from 'react';

/**
 * Verbatim JSON panel for the response tabs. Optional line-level highlighter
 * (Tru8 panel only): lines whose key matches HIGHLIGHT_KEYS render in accent.
 * String-split on lines — no syntax-highlight library, no new deps.
 */

const HIGHLIGHT_KEYS = [
  'tier',
  'evidenceType',
  'relationship',
  'state',
  'gaps',
  'uncertainty',
  'receiptStatus',
  'archivedUrl',
  '_manifest',
  'orientation',
];

const HIGHLIGHT_PATTERN = new RegExp(`"(${HIGHLIGHT_KEYS.join('|')})"\\s*:`);

interface JsonPanelProps {
  label: string;
  json: string;
  highlight?: boolean;
  footer: ReactNode;
  /** Wall-clock response time of the live capture, e.g. "71.2s" or "0.4s". */
  capturedIn?: string;
}

export function JsonPanel({ label, json, highlight = false, footer, capturedIn }: JsonPanelProps) {
  const lines = json.split('\n');

  return (
    <div className="border border-zinc-800 bg-black overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-800">
        <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-accent">
          {label}
        </span>
        <span className="font-mono text-[10px] text-zinc-500">
          200 OK{capturedIn ? ` · ${capturedIn}` : ''}
        </span>
      </div>

      <pre className="px-5 py-5 font-mono text-[11px] md:text-xs text-zinc-300 leading-relaxed overflow-x-auto max-h-[560px] overflow-y-auto">
        {lines.map((line, i) => (
          <div key={i} className={highlight && HIGHLIGHT_PATTERN.test(line) ? 'text-accent' : undefined}>
            {line || ' '}
          </div>
        ))}
      </pre>

      <div className="px-5 py-3 border-t border-zinc-800 font-mono text-[10px] text-zinc-500 leading-relaxed">
        {footer}
      </div>
    </div>
  );
}
