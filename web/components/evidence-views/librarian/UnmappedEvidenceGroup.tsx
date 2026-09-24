'use client';

import { Evidence } from '@shared/types';
import { ArrowUpRight } from 'lucide-react';
import { cleanTitle, extractDomain } from '../shared-utils';

const TIER_LABEL: Record<string, string> = {
  primary: 'Primary',
  reporting: 'Reporting',
  commentary: 'Commentary',
};

/**
 * Sources gathered but connected to no part of the claim (A− H4, 2026-09-24).
 *
 * They used to sit in the tier bands, where an off-topic official page in
 * PRIMARY read as the record's primary evidence while moving no state. They
 * are shown here instead — visible and counted, never dropped (invariant #5).
 * "Not mapped", never "not related": some are on-topic and simply were not
 * connected to an element.
 */
export function UnmappedEvidenceGroup({ evidence }: { evidence: Evidence[] }) {
  if (evidence.length === 0) return null;

  return (
    <section data-testid="unmapped-evidence" className="border border-zinc-100 mb-6">
      <div className="px-4 py-3 border-b border-zinc-100">
        <p className="font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-zinc-600">
          Gathered — not mapped to any part of the claim ({evidence.length})
        </p>
        <p className="mt-1 text-[11px] text-zinc-400 leading-relaxed">
          Found during the search but not connected to any element, so they carry no weight in any state above.
        </p>
      </div>
      <ul className="divide-y divide-zinc-100">
        {evidence.map((ev) => {
          const domain = extractDomain(ev.url);
          return (
            <li key={ev.evidenceId || ev.id} className="px-4 py-2 flex items-start gap-3">
              <span className="font-mono text-[9px] uppercase tracking-wider text-zinc-400 w-20 shrink-0 pt-0.5">
                {TIER_LABEL[ev.tier || 'commentary'] || 'Commentary'}
              </span>
              <a
                href={ev.url}
                target="_blank"
                rel="noopener noreferrer"
                className="min-w-0 flex-1 text-[12px] text-zinc-600 hover:text-[var(--accent)] transition-colors"
              >
                <span className="block leading-snug">{cleanTitle(ev.title) || domain}</span>
                <span className="inline-flex items-center gap-1 font-mono text-[10px] text-zinc-400">
                  {domain} <ArrowUpRight size={10} />
                </span>
              </a>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
