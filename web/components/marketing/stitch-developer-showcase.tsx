import Link from 'next/link';
import { ArrowUpRight } from 'lucide-react';

import { ScrollReveal } from './scroll-reveal';
import { CopyCodeButton } from './copy-code-button';
import { SheetHeader } from './sheet-header';

const SAMPLE_RESPONSE = `{
  "id": "chk_8f3a...",
  "status": "complete",
  "claims": [
    {
      "id": "clm_01",
      "text": "Global average temperature rose 1.1°C since pre-industrial times",
      "claimMap": {
        "normalisedClaim": "...",
        "claimType": "scientific",
        "elements": [
          {
            "elementId": "el_01",
            "description": "1.1°C rise figure",
            "state": "supported",
            "evidenceRefs": [
              { "evidenceId": "ev_a1", "relationship": "supports" },
              { "evidenceId": "ev_b2", "relationship": "supports" }
            ]
          }
        ],
        "orientation": "Evidence converges on the 1.1°C figure across primary and academic sources."
      }
    }
  ],
  "_meta": {
    "executedTier": "quick",
    "chargedPence": 7,
    "landscape": {
      "elementCount": 4,
      "elementStates": { "supported": 3, "unresolved": 1 },
      "evidenceDensity": 24,
      "sourcesConsidered": 24,
      "sourceDiversity": {
        "tierSpread": { "primary": 6, "reporting": 12, "commentary": 6 },
        "uniqueDomains": 18,
        "typeCoverage": 5
      },
      "freshness": { "freshestDaysAgo": 3, "dateSpanDays": 412 },
      "gaps": [{ "reason": "no_academic_sources" }]
    },
    "limitations": ["heuristic_classification", "single_query_per_element"]
  },
  "_manifest": {
    "checkId": "chk_8f3a...",
    "landscapeHash": "9c14...",
    "signature": "hmac-sha256:...",
    "verifyUrl": "/verify/chk_8f3a..."
  }
}`;

const SAMPLE_CURL = `curl -X POST https://api.trueight.com/api/v1/agent/quick \\
  -H "X-API-Key: $TRU8_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{ "claim": "Global average temperature rose 1.1°C since pre-industrial times" }'`;

const CALLOUTS: ReadonlyArray<{ key: string; description: string }> = [
  {
    key: 'claimMap',
    description:
      'Per-claim decomposition. Elements, evidence refs with relationship, mechanical orientation line.',
  },
  {
    key: '_meta.landscape',
    description:
      'Computed metrics — element states, tier spread, unique domains, freshness, identified gaps.',
  },
  {
    key: '_manifest',
    description:
      'Signed payload + verify URL. Your downstream caller can prove what you sent them.',
  },
];

export function StitchDeveloperShowcase() {
  return (
    <section id="developer-showcase" className="py-24 md:py-32 bg-zinc-950 text-zinc-100">
      <div className="max-w-7xl mx-auto px-6">
        <SheetHeader number="03" label="API" refText="POST /agent/*" tone="dark" />
        <ScrollReveal>
          <div className="mb-16 md:mb-20 max-w-3xl">
            <h2 className="text-4xl md:text-6xl lg:text-7xl font-normal tracking-[-0.02em] text-zinc-50 leading-[0.95]">
              One submission,<br />
              structured for agents.
            </h2>
            <p className="text-sm md:text-base text-zinc-400 leading-relaxed mt-6 max-w-2xl">
              The same structured evidence record, returned as a stable JSON contract. Per-claim
              element decomposition, computed landscape metrics, and a signed manifest your callers
              can verify.
            </p>
          </div>
        </ScrollReveal>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12">
          {/* JSON response panel */}
          <ScrollReveal className="lg:col-span-7">
            <div className="border border-zinc-800 bg-black overflow-hidden">
              <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-800">
                <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-accent">
                  POST /agent/quick — Response
                </span>
                <span className="font-mono text-[10px] text-zinc-500">200 OK</span>
              </div>
              <pre className="px-5 py-5 overflow-x-auto text-[11px] md:text-xs font-mono leading-relaxed text-zinc-300">
                {SAMPLE_RESPONSE}
              </pre>
            </div>
          </ScrollReveal>

          {/* Right column — callouts, curl, CTA */}
          <ScrollReveal className="lg:col-span-5" delay={120}>
            <div className="space-y-10">
              {/* Callouts */}
              <div className="space-y-6">
                <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-500 block">
                  What&rsquo;s in the response
                </span>
                <ul className="space-y-5">
                  {CALLOUTS.map((callout) => (
                    <li key={callout.key} className="flex flex-col gap-2 border-l border-zinc-800 pl-4">
                      <code className="font-mono text-sm text-accent tracking-tight">{callout.key}</code>
                      <p className="text-sm text-zinc-400 leading-relaxed">{callout.description}</p>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Curl */}
              <div className="border border-zinc-800 bg-black overflow-hidden">
                <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-800">
                  <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-500">
                    Curl — one call
                  </span>
                  <CopyCodeButton value={SAMPLE_CURL} />
                </div>
                <pre className="px-5 py-4 overflow-x-auto text-[11px] font-mono leading-relaxed text-zinc-300">
                  {SAMPLE_CURL}
                </pre>
              </div>

              {/* CTA */}
              <div className="flex flex-col sm:flex-row gap-4 items-stretch sm:items-center">
                <Link
                  href="/developers"
                  className="group inline-flex items-center justify-between gap-6 bg-white text-zinc-950 px-8 py-5 text-xs font-bold tracking-[0.3em] uppercase transition-colors hover:bg-zinc-100"
                >
                  <span>Read the docs</span>
                  <ArrowUpRight
                    size={18}
                    className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
                  />
                </Link>
                <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-500 leading-relaxed">
                  Signed manifests, MCP server, webhooks
                </div>
              </div>

              <Link
                href="/compare"
                className="inline-block text-sm text-zinc-400 underline underline-offset-2 hover:text-zinc-200 transition-colors"
              >
                See how this compares to Web IQ, check-grounding and Sonar →
              </Link>
            </div>
          </ScrollReveal>
        </div>
      </div>
    </section>
  );
}
