'use client';

import { useId, useState, type ReactNode } from 'react';

interface CodeDisclosureProps {
  /** Mono label shown on the toggle bar, e.g. "Sample response". */
  label: string;
  /** Optional right-aligned mono meta, e.g. "200 OK". */
  meta?: string;
  /** Optional always-visible action in the header (e.g. a copy button). Kept
   *  outside the toggle button and always interactive, so the collapsed panel
   *  itself holds no focusable elements (no tab-trap when hidden). */
  headerAction?: ReactNode;
  /** The code panel. Always rendered into the DOM (present in SSR HTML for
   *  AEO/SEO); only visually collapsed when closed. */
  children: ReactNode;
  defaultOpen?: boolean;
}

/**
 * Progressive-disclosure wrapper for code on the (dark) marketing surfaces.
 * Collapsed by default: leads with value, reveals code on demand. The content
 * stays server-rendered in the HTML (grid-rows 0fr→1fr visual collapse), so it
 * remains citable by search/AI engines while staying out of the lay reader's way.
 */
export function CodeDisclosure({
  label,
  meta,
  headerAction,
  children,
  defaultOpen = false,
}: CodeDisclosureProps) {
  const [open, setOpen] = useState(defaultOpen);
  const panelId = useId();

  return (
    <div className="border border-zinc-800 bg-black">
      <div className="flex items-center justify-between gap-4 px-5 py-3">
        <button
          type="button"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => setOpen((o) => !o)}
          className="group flex flex-1 items-center justify-between gap-4 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-zinc-500"
        >
          <span className="flex items-center gap-3">
            <span
              aria-hidden
              className={`inline-block h-2 w-2 bg-accent transition-transform duration-300 motion-reduce:transition-none ${
                open ? 'rotate-45' : ''
              }`}
            />
            <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-300 transition-colors group-hover:text-zinc-100">
              {label}
            </span>
          </span>
          <span className="flex items-center gap-3">
            {meta ? (
              <span className="hidden font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-500 sm:inline">
                {meta}
              </span>
            ) : null}
            <span className="font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-500 transition-colors group-hover:text-zinc-300">
              {open ? 'Hide' : 'View'}
            </span>
          </span>
        </button>
        {headerAction ? <span className="ml-2 shrink-0">{headerAction}</span> : null}
      </div>
      <div
        id={panelId}
        aria-hidden={!open}
        className={`grid border-t transition-[grid-template-rows] duration-300 motion-reduce:transition-none ${
          open ? 'grid-rows-[1fr] border-zinc-800' : 'grid-rows-[0fr] border-transparent'
        }`}
      >
        <div className="min-h-0 overflow-hidden">{children}</div>
      </div>
    </div>
  );
}
