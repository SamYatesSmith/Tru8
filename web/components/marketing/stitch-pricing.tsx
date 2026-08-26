'use client';

import { useState } from 'react';
import Link from 'next/link';

import { SheetHeader } from './sheet-header';
import { capture } from '@/lib/analytics';

/**
 * Pricing — Direction B: the Console (£20/mo · £200/yr) rendered as the site's
 * signature "artifact" datasheet panel (mono spine, numbered feature ledger,
 * signed-manifest footer), with Free + Teams as a supporting rail and a
 * deliberately quiet API band. Document-grammar vocabulary, zero new colours.
 *
 * P3 routes CTAs to the app / contact / developers — a real £20 Stripe checkout
 * needs a new Stripe product + price-id env (deferred to P4/deploy). The
 * monthly/annual toggle selects which price is shown; at checkout wiring it
 * also selects the Stripe price id. tiers.ts is left intact for the dashboard's
 * existing-subscriber config; this surface no longer displays the legacy
 * £7/£29 plans.
 */

const CONSOLE_FEATURES = [
  {
    n: '01',
    key: '200 checks a month',
    desc: "A working month's research, several times over.",
  },
  {
    n: '02',
    key: 'All six views',
    desc: 'Evidence, Compare, Timeline, Gaps, Map and Video.',
  },
  {
    n: '03',
    key: 'Full export',
    desc: 'Download the record as PDF, CSV or JSON.',
  },
  {
    n: '04',
    key: 'Signed record + receipts',
    desc: 'A signed evidence record, with a receipt for every exclusion.',
  },
  {
    n: '05',
    key: 'Personal API allowance',
    desc: 'Light scripting against your own account.',
  },
];

export function StitchPricing() {
  const [billing, setBilling] = useState<'monthly' | 'annual'>('monthly');

  const setPeriod = (period: 'monthly' | 'annual') => {
    if (period === billing) return;
    setBilling(period);
    capture('pricing_billing_toggle', { surface: 'pricing', period });
  };

  return (
    <section id="pricing" className="py-24 md:py-32">
      <div className="max-w-6xl mx-auto px-6">
        <SheetHeader number="05" label="Pricing" refText="CONSOLE · TEAMS · API" />

        <h2 className="text-3xl sm:text-4xl md:text-5xl font-normal tracking-[-0.03em] text-zinc-900 mb-12 md:mb-16">
          Choose how you <span className="font-bold">work.</span>
        </h2>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* CONSOLE — hero artifact panel */}
          <div className="lg:col-span-7 flex flex-col border border-zinc-200 border-t-2 border-t-accent bg-white">
            {/* spine */}
            <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between border-b border-zinc-200 px-6 py-3">
              <span className="font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-900">
                Tru8 Console
              </span>
              <span className="font-mono text-[10px] text-zinc-400">
                claimMap · export · signed
              </span>
            </div>

            {/* price block */}
            <div className="px-6 py-8">
              <div
                className="inline-flex border border-zinc-200 mb-6"
                role="group"
                aria-label="Billing period"
              >
                {(['monthly', 'annual'] as const).map((period) => (
                  <button
                    key={period}
                    type="button"
                    aria-pressed={billing === period}
                    onClick={() => setPeriod(period)}
                    className={`font-mono text-[10px] tracking-[0.2em] uppercase px-4 py-2 transition-colors ${
                      billing === period
                        ? 'bg-zinc-900 text-white'
                        : 'text-zinc-500 hover:text-zinc-900'
                    }`}
                  >
                    {period}
                  </button>
                ))}
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-5xl font-light text-zinc-900">
                  {billing === 'monthly' ? '£20' : '£200'}
                </span>
                <span className="text-lg text-zinc-400">
                  {billing === 'monthly' ? '/mo' : '/yr'}
                </span>
              </div>
              <p className="text-sm text-zinc-500 mt-2">
                {billing === 'monthly'
                  ? 'or £200/yr — two months free · evidence research in the browser.'
                  : 'billed once a year — two months free · evidence research in the browser.'}
              </p>
            </div>

            {/* feature ledger */}
            <div>
              {CONSOLE_FEATURES.map((f) => (
                <div
                  key={f.n}
                  className="px-6 py-4 border-t border-zinc-100 md:grid md:grid-cols-12 md:gap-6 md:items-baseline"
                >
                  <div className="flex items-center gap-3 md:col-span-5">
                    <span className="font-mono text-xs text-accent w-5 shrink-0">
                      {f.n}
                    </span>
                    <h3 className="font-mono text-[11px] tracking-[0.15em] uppercase font-bold text-zinc-900">
                      {f.key}
                    </h3>
                  </div>
                  <p className="text-sm text-zinc-500 leading-relaxed md:col-span-7 mt-1 md:mt-0">
                    {f.desc}
                  </p>
                </div>
              ))}
            </div>

            {/* manifest footer + primary CTA */}
            <div className="mt-auto border-t border-zinc-200 px-6 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <span className="flex items-center gap-2 font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-500">
                <span aria-hidden="true" className="w-2 h-2 bg-accent rotate-45 shrink-0" />
                signed record
              </span>
              <Link
                href="/dashboard/new-check"
                onClick={() => capture('pricing_console_click', { surface: 'pricing' })}
                className="bg-black text-white px-6 py-3 text-[11px] font-bold tracking-[0.2em] uppercase hover:bg-zinc-800 transition-colors text-center"
              >
                Start in the browser →
              </Link>
            </div>
          </div>

          {/* RAIL — Free + Teams (supporting, un-elevated) */}
          <div className="lg:col-span-5 flex flex-col gap-8">
            <div className="flex flex-col flex-1 border border-zinc-200 bg-white p-6">
              <span className="font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-900">
                Free taster
              </span>
              <div className="text-3xl font-light text-zinc-900 mt-4">Free</div>
              <p className="text-sm text-zinc-500 mt-2 flex-grow">
                3 checks · all features · all six views. See exactly what a record
                looks like.
              </p>
              <Link
                href="/dashboard/new-check"
                onClick={() => capture('pricing_free_click', { surface: 'pricing' })}
                className="mt-6 inline-block font-mono text-[11px] tracking-[0.2em] uppercase text-zinc-900 hover:text-accent transition-colors"
              >
                Start free →
              </Link>
            </div>

            <div className="flex flex-col flex-1 border border-zinc-200 bg-white p-6">
              <span className="font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-900">
                Teams
              </span>
              <div className="text-3xl font-light text-zinc-900 mt-4">
                From £75
                <span className="text-lg text-zinc-400">/mo</span>
              </div>
              <p className="text-sm text-zinc-500 mt-2 flex-grow">
                For newsrooms and research teams — shared access, priced to fit.
                Tell us what you need.
              </p>
              <Link
                href="/contact"
                onClick={() => capture('pricing_teams_click', { surface: 'pricing' })}
                className="mt-6 inline-block font-mono text-[11px] tracking-[0.2em] uppercase text-zinc-900 hover:text-accent transition-colors"
              >
                Talk to us →
              </Link>
            </div>
          </div>
        </div>

        {/* Quiet API band */}
        <div className="mt-8 border-t border-zinc-200 pt-6 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <span className="font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-500">
              API — metered
            </span>
            <p className="text-sm text-zinc-500 mt-1">
              For systems and agents: metered analysis, billed per call from a
              prepaid balance.
            </p>
          </div>
          <Link
            href="/developers"
            onClick={() => capture('pricing_api_click', { surface: 'pricing' })}
            className="font-mono text-[11px] tracking-[0.2em] uppercase text-zinc-900 hover:text-accent transition-colors whitespace-nowrap"
          >
            See the API →
          </Link>
        </div>
      </div>
    </section>
  );
}
