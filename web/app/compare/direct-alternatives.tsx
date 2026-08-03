/**
 * C3 (2026-07-09): the shortlist comparison — Tru8 vs the tools a buyer
 * actually evaluates us against (Webcite, scite, Factiverse), replacing the
 * page's framing gap where only grounding APIs appeared.
 *
 * Grounding rules (audit/2026-07-08_f8_implementation_plan.md C3 row):
 * - Facts from audit/2026-06-24_pricing_research_plan.md (§B, verified) +
 *   the 2026-07-09 live re-check (OPEN_WORK session log). Shape, features
 *   and published price ONLY — no quality claims about competitors.
 * - No-verdict copy uses the qualified form: "no verdict ON THE CLAIM"
 *   (element states describe the evidence; nothing aggregates to true/false).
 * - Vendor prices shown in the vendor's own currency, dated in the footnote.
 */

import Link from 'next/link';
import { SAMPLE_REPORT_PATH } from '@/lib/marketing';

interface Rival {
  name: string;
  domain: string;
  whatItIs: string;
  comesBack: string;
  scope: string;
  price: string;
  chooseItWhen: string;
}

const RIVALS: Rival[] = [
  {
    name: 'Webcite',
    domain: 'webcite.co',
    whatItIs: 'Claim-verification API and playground, built for agent pipelines.',
    comesBack:
      'A verdict on the claim — supported, contradicted or mixed — with a 0–100 confidence score, plus per-source stance and credibility scores.',
    scope: 'Web claims.',
    price: 'Builder $20/mo · 500 credits · full verification ≈ 4 credits (≈ $0.12/call)',
    chooseItWhen:
      'You want a machine-readable answer on the claim itself — a verdict your pipeline can consume without a human reading the evidence.',
  },
  {
    name: 'scite',
    domain: 'scite.ai',
    whatItIs: 'Smart Citations — how published papers cite other published papers.',
    comesBack:
      'Citation-stance counts and excerpts — supporting, mentioning, contrasting — for a paper in the academic literature.',
    scope: 'Academic literature only. A claim has to live in journals for scite to see it.',
    price: 'Personal $20/mo (≈ $12/mo billed annually)',
    chooseItWhen:
      'Your question is how a specific paper has been received by the literature that cites it.',
  },
  {
    name: 'Factiverse',
    domain: 'factiverse.ai',
    whatItIs: 'Broadcast and video monitoring (Gather), with newsroom heritage.',
    comesBack:
      'Supported / Disputed labels on claims detected in live media streams.',
    scope: 'Broadcast and video monitoring workflows.',
    price: 'Gather $6.99/mo (annual)',
    chooseItWhen:
      'You are monitoring live broadcasts and need claims flagged for review as they air.',
  },
];

const TABLE_ROWS: { label: string; cells: [string, string, string, string] }[] = [
  {
    label: 'What comes back on the claim',
    cells: [
      'The evidence record — no verdict on the claim',
      'Verdict (supported · contradicted · mixed) + confidence',
      'Citation stances for published papers',
      'Supported / Disputed labels',
    ],
  },
  {
    label: 'Scope',
    cells: [
      'Any claim or URL · web + specialist APIs',
      'Web claims',
      'Academic literature only',
      'Broadcast / video streams',
    ],
  },
  {
    label: 'Per-source labelling',
    cells: [
      'Tier × type + relationship to each claim element',
      'Stance + credibility score',
      'Citation type (supporting · mentioning · contrasting)',
      'Claim-level labels',
    ],
  },
  {
    label: 'Receipts, archives, signed record',
    cells: [
      'Every exclusion receipted · archived URLs · signed manifest + public verify URL',
      'None published',
      'None published',
      'None published',
    ],
  },
  {
    label: 'Self-serve price',
    cells: [
      'Console £20/mo · API from £0.02/call, full check £0.15',
      'Builder $20/mo · ≈ $0.12/full verification',
      'Personal $20/mo',
      'Gather $6.99/mo (annual)',
    ],
  },
];

const TABLE_COLUMNS = ['Tru8', 'Webcite', 'scite', 'Factiverse'];

export function DirectAlternatives() {
  return (
    <section className="mb-20 md:mb-28">
      <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-6">
        Module — The Shortlist
      </div>

      {/* The three rivals — what each hands you */}
      <div className="grid md:grid-cols-3 gap-4 md:gap-5 mb-5">
        {RIVALS.map((rival) => (
          <div key={rival.name} className="border border-zinc-200 p-6 flex flex-col">
            <div className="flex items-baseline justify-between mb-1">
              <h3 className="text-lg font-bold text-zinc-900">{rival.name}</h3>
              <span className="font-mono text-[10px] tracking-wider uppercase text-zinc-400">
                {rival.domain}
              </span>
            </div>
            <p className="text-sm text-zinc-500 leading-relaxed mb-4">{rival.whatItIs}</p>

            <div className="font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-400 mb-1.5">
              What comes back
            </div>
            <p className="text-sm text-zinc-900 leading-relaxed mb-4">{rival.comesBack}</p>

            <div className="font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-400 mb-1.5">
              Scope
            </div>
            <p className="text-sm text-zinc-600 leading-relaxed mb-4">{rival.scope}</p>

            <div className="mt-auto pt-4 border-t border-zinc-100">
              <p className="font-mono text-[11px] text-zinc-600 mb-3">{rival.price}</p>
              <p className="text-xs text-zinc-500 leading-relaxed italic">
                Choose it when: {rival.chooseItWhen}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Tru8 — the record, as the payoff */}
      <div className="border border-zinc-900 bg-zinc-950 text-zinc-100 p-6 md:p-8 mb-10">
        <div className="flex items-baseline justify-between mb-1">
          <h3 className="text-lg font-bold text-zinc-50">Tru8</h3>
          <span className="font-mono text-[10px] tracking-wider uppercase text-zinc-500">
            trueight.com
          </span>
        </div>
        <div className="font-mono text-[10px] tracking-[0.2em] uppercase text-accent mb-2 mt-3">
          What comes back
        </div>
        <p className="text-sm md:text-base text-zinc-200 leading-relaxed max-w-3xl mb-4">
          The evidence record. Every source classified by tier and type, mapped to the
          claim&apos;s elements as supports, challenges or context, with dispute states left
          visible, named gaps, exclusion receipts, archived URLs, a signed manifest and a
          public verify URL. No verdict on the claim — element states describe the evidence;
          nothing aggregates to true or false.
        </p>
        <div className="flex flex-col sm:flex-row sm:items-center gap-x-6 gap-y-2">
          <p className="font-mono text-[11px] text-zinc-400">
            Console £20/mo (£200/yr) · API from £0.02/call, full check £0.15 · Teams from £75/mo
          </p>
          <Link
            href={SAMPLE_REPORT_PATH}
            target="_blank"
            rel="noopener noreferrer"
            className="font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-300 hover:text-white transition-colors"
          >
            See a live record →
          </Link>
        </div>
      </div>

      {/* Compact facts table for scanners */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse min-w-[720px]">
          <thead>
            <tr className="border-b border-zinc-200">
              <th className="py-3 pr-4 font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-400 font-medium w-[18%]">
                &nbsp;
              </th>
              {TABLE_COLUMNS.map((col, i) => (
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
            {TABLE_ROWS.map((row) => (
              <tr key={row.label} className="border-b border-zinc-200">
                <td className="py-3.5 pr-4 text-sm text-zinc-900 font-medium align-top">
                  {row.label}
                </td>
                {row.cells.map((cell, i) => (
                  <td
                    key={i}
                    className={`py-3.5 px-3 align-top text-xs leading-snug ${
                      i === 0 ? 'bg-zinc-50/60 text-zinc-900' : 'text-zinc-500'
                    }`}
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="mt-4 font-mono text-[10px] tracking-wider uppercase text-zinc-400 leading-relaxed">
        Competitor facts as published by each vendor, checked June–July 2026. Vendor prices in
        their own currency.
      </p>
    </section>
  );
}
