import { Navigation } from '@/components/layout/navigation';
import { MobileNav } from '@/components/layout/mobile-nav';
import { SheetHeader } from '@/components/marketing/sheet-header';
import { Footer } from '@/components/layout/footer';
import { ArrowLeft, Key, Search, FileJson, BarChart3, ShieldCheck, Bell, Layers, Radio } from 'lucide-react';
import Link from 'next/link';
import { TrackedLink } from '@/components/analytics/tracked-link';

export const metadata = {
  title: 'API & MCP Server for AI Agents',
  description: 'Structured evidence research in one API call. Four call tiers, an MCP server hosted and self-installed, for Claude and other AI agents. From £0.02/query.',
  alternates: { canonical: '/developers' },
};

const TOC_ITEMS = [
  { id: 'quick-start', label: 'Quick Start' },
  { id: 'pricing', label: 'Tiers & Pricing' },
  { id: 'mcp', label: 'MCP' },
  { id: 'response', label: 'What You Get' },
  { id: 'limits', label: 'Limits & Ops' },
  { id: 'faq', label: 'FAQ' },
  { id: 'docs', label: 'Docs' },
];

// One source array drives both the visible FAQ and the FAQPage JSON-LD, so the
// markup always matches the rendered answers (a Google requirement). Answers are
// grounded in this page's own content. No verdict language; functional manifest
// "verify" wording mirrors the response section below.
const DEV_FAQS: ReadonlyArray<{ q: string; a: string }> = [
  {
    q: 'How do I get started with the Tru8 API?',
    a: 'Create an API key in your dashboard settings, then POST a claim or URL to /agent/check. That one endpoint tries the cheapest route first and escalates only as far as max_tier allows, so a single call returns a structured evidence landscape at the lowest price that can answer it.',
  },
  {
    q: 'What does a Tru8 API call return?',
    a: 'A structured evidence landscape: each claim is decomposed into 1–5 elements, evidence is mapped to those elements with supports, challenges or context relationships, every source is classified by tier and type, and gaps are named. It does not return a true/false verdict. We organise; you decide.',
  },
  {
    q: 'Is there an MCP server for Claude and other AI agents?',
    a: 'Yes, by three routes. Connect straight to the hosted server at https://api.trueight.com/mcp with no install, add it through the Smithery registry, or pip install tru8-mcp to run it locally over stdio. All three expose the same three tools against the same API.',
  },
  {
    q: 'How are API calls priced?',
    a: 'Calls are metered per request across four tiers — lookup, consensus, quick and full — billed from prepaid credits, and you are charged for the tier that actually executed rather than the one you requested. See the Tiers & Pricing section above for the current per-tier rates.',
  },
  {
    q: 'How can an agent confirm a result has not changed?',
    a: 'When a response carries a _manifest, its signed landscape hash can be re-checked at any time by calling GET /verify/{check_id}, a public endpoint that recomputes the hash from the stored data and reports whether it still matches.',
  },
  {
    q: 'How long does a check take?',
    a: 'Typically 15–90 seconds depending on the tier, because Tru8 retrieves and classifies evidence across the open web and specialist APIs rather than returning passages and a score. Cached and consensus routes return instantly.',
  },
];

const faqJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: DEV_FAQS.map((item) => ({
    '@type': 'Question',
    name: item.q,
    acceptedAnswer: { '@type': 'Answer', text: item.a },
  })),
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function DevelopersPage() {
  return (
    <>
      <Navigation />
      <MobileNav />

      <main id="main-content" className="min-h-screen pt-24 md:pt-32 pb-24 md:pb-20">
        {/* Inside main, not a direct body child — see app/page.tsx JSON-LD note */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd).replace(/</g, '\\u003c') }}
        />
        {/* Document-grammar spine (xl+) */}
        <div
          aria-hidden="true"
          className="pointer-events-none fixed left-1.5 top-1/2 z-40 hidden -translate-y-1/2 rotate-180 select-none font-mono text-[9px] tracking-[0.3em] text-zinc-300 [writing-mode:vertical-rl] xl:block"
        >
          TRU8 · DEVELOPERS · REV 2026.08
        </div>
        <div className="container mx-auto px-4 md:px-6 max-w-4xl">
          {/* Back Button */}
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-zinc-400 hover:text-zinc-900 transition-colors mb-6 md:mb-8"
          >
            <ArrowLeft size={20} />
            <span className="text-sm font-medium">Back to Home</span>
          </Link>

          {/* Hero */}
          <section className="mb-12 md:mb-16">
            <SheetHeader number="01" label="Developer API" />
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-normal text-zinc-900 mb-6 md:mb-8">
              The evidence landscape behind any claim. One API call.
            </h1>

            <div className="space-y-6 text-base md:text-lg text-zinc-600 leading-relaxed">
              <p>
                Submit a claim, URL, or article. Get back structured evidence — organised by source tier
                (primary, reporting, commentary) and type (data, official, news, analysis, opinion, academic),
                with element decomposition and relationship mapping.
              </p>

              <p>
                Grounding APIs return passages and a score. Tru8 returns structure:{' '}
                <code className="text-sm font-mono text-zinc-900">tier</code>,{' '}
                <code className="text-sm font-mono text-zinc-900">type</code>,{' '}
                <code className="text-sm font-mono text-zinc-900">relationship</code>,{' '}
                <code className="text-sm font-mono text-zinc-900">state</code>,{' '}
                <code className="text-sm font-mono text-zinc-900">gaps</code>,{' '}
                <code className="text-sm font-mono text-zinc-900">receipts</code>.{' '}
                <Link
                  href="/compare#grounding-apis"
                  className="text-accent underline underline-offset-2 hover:text-zinc-900 transition-colors"
                >
                  Same claim, Tru8 vs four grounding APIs →
                </Link>
              </p>

              <div className="bg-zinc-50 border-l-2 border-accent px-6 py-5 my-8">
                <p className="text-zinc-900 font-medium text-lg md:text-xl leading-relaxed">
                  One API call.<br />
                  Multi-source evidence retrieval.<br />
                  Structured, not summarised.<br />
                  <span className="text-accent">Your agent decides what matters.</span>
                </p>
              </div>

              {/* Hero CTAs (C1 S3) — act from the top, not only from §Resources */}
              <div className="flex flex-col sm:flex-row sm:items-stretch gap-4">
                <TrackedLink
                  href="/dashboard/settings?tab=developer"
                  event="get_api_key_click"
                  eventProps={{ surface: 'developers_hero' }}
                  className="group inline-flex items-center justify-center gap-4 bg-black text-white px-8 py-4 text-xs font-bold tracking-[0.3em] uppercase w-full sm:w-auto transition-all hover:bg-zinc-900"
                >
                  <span>Get API key</span>
                  <span aria-hidden="true" className="w-2 h-2 bg-accent rotate-45 transition-transform group-hover:translate-x-1" />
                </TrackedLink>
                <a
                  href="#response"
                  className="inline-flex items-center justify-center gap-2 border border-zinc-200 px-8 py-4 text-xs font-bold tracking-[0.3em] uppercase text-zinc-900 w-full sm:w-auto transition-colors hover:border-zinc-900"
                >
                  See what comes back
                </a>
              </div>
              <p className="font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-400">
                From £0.02 per call · no subscription required · charged on the tier that actually ran
              </p>

              <p className="font-mono text-[11px] tracking-[0.2em] uppercase text-zinc-500">
                Prefer to research in the browser?{' '}
                <Link
                  href="/dashboard/new-check"
                  className="text-zinc-900 underline underline-offset-2 hover:text-accent transition-colors"
                >
                  Start a check →
                </Link>
              </p>
            </div>
          </section>

          {/* Table of Contents */}
          <nav className="mb-12 md:mb-16 border border-zinc-200 bg-zinc-50/50 p-4 md:p-5">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-3">
              On this page
            </div>
            <div className="flex flex-wrap gap-x-1 gap-y-1">
              {TOC_ITEMS.map((item, i) => (
                <span key={item.id} className="flex items-center">
                  <a
                    href={`#${item.id}`}
                    className="text-xs font-mono text-zinc-500 hover:text-accent transition-colors px-2 py-1 hover:bg-zinc-100"
                  >
                    {item.label}
                  </a>
                  {i < TOC_ITEMS.length - 1 && (
                    <span className="text-zinc-200 text-xs select-none">/</span>
                  )}
                </span>
              ))}
            </div>
          </nav>

          {/* Divider */}
          <div className="border-t border-zinc-200 my-12 md:my-16" />

          {/* Quick Start */}
          <section id="quick-start" className="mb-16 md:mb-20 scroll-mt-28">
            <SheetHeader number="02" label="Quick Start" />
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-normal text-zinc-900 mb-6 md:mb-8">
              Three Steps
            </h2>

            <div className="space-y-8">
              {/* Step 1 */}
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 bg-zinc-900 text-white flex items-center justify-center font-mono text-sm font-bold">
                  1
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="text-lg font-semibold text-zinc-900 mb-2">Get an API key</h3>
                  <p className="text-zinc-600 text-sm mb-3">
                    Create a key in your{' '}
                    <Link href="/dashboard/settings?tab=developer" className="text-accent hover:underline">
                      dashboard settings
                    </Link>
                    . Your key is shown once — store it in an environment variable immediately:
                  </p>
                  <pre className="bg-zinc-950 text-zinc-300 p-4 overflow-x-auto text-xs font-mono leading-relaxed">
{`# Store your key as an environment variable — never hardcode it
export TRU8_API_KEY="tru8_sk_..."`}
                  </pre>
                  <div className="mt-4 flex gap-3 bg-zinc-50 border border-zinc-200 p-4">
                    <ShieldCheck size={18} className="text-zinc-400 flex-shrink-0 mt-0.5" />
                    <div className="text-xs text-zinc-600 space-y-1">
                      <p className="font-semibold text-zinc-900">Key security</p>
                      <p>
                        Your API key carries your identity and usage quota. Store it in environment
                        variables or a secrets manager, never in source code, logs or client-side
                        bundles. Use separate keys per agent or environment, and revoke immediately
                        in dashboard settings if one is exposed.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Step 2 */}
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 bg-zinc-900 text-white flex items-center justify-center font-mono text-sm font-bold">
                  2
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="text-lg font-semibold text-zinc-900 mb-2">Submit a claim</h3>
                  <p className="text-zinc-600 text-sm mb-3">
                    <code className="text-zinc-900 font-mono text-xs">/agent/check</code> is the endpoint
                    to reach for first. It tries the cheapest route that can answer — your own cached
                    analysis, then cross-user consensus — and only runs the pipeline if neither hits,
                    escalating no further than <code className="text-zinc-400">max_tier</code>.
                  </p>
                  <pre className="bg-zinc-950 text-zinc-300 p-4 overflow-x-auto text-xs font-mono leading-relaxed">
{`curl -X POST https://api.trueight.com/api/v1/agent/check \\
  -H "X-API-Key: $TRU8_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "claim": "Global average temperature rose 1.1°C since pre-industrial times",
    "max_tier": "full"
  }'`}
                  </pre>
                  <p className="text-zinc-500 text-xs mt-2 font-mono">
                    Returns the landscape plus _meta.executedTier and _meta.chargedPence
                  </p>
                </div>
              </div>

              {/* Step 3 */}
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 bg-zinc-900 text-white flex items-center justify-center font-mono text-sm font-bold">
                  3
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="text-lg font-semibold text-zinc-900 mb-2">Retrieve the result</h3>
                  <pre className="bg-zinc-950 text-zinc-300 p-4 overflow-x-auto text-xs font-mono leading-relaxed">
{`curl https://api.trueight.com/api/v1/agent/result/{check_id} \\
  -H "X-API-Key: $TRU8_API_KEY"`}
                  </pre>
                  <p className="text-zinc-500 text-xs mt-2 font-mono">
                    Free, and only for your own checks. Still running: {'{'}&quot;status&quot;: &quot;processing&quot;, &quot;hit&quot;: false{'}'}
                  </p>
                </div>
              </div>
            </div>

            {/* Other submission routes — the deep spec for each lives in the API reference */}
            <div className="bg-zinc-50 border border-zinc-200 p-6 mt-8">
              <h3 className="font-mono text-[10px] font-bold tracking-widest uppercase text-zinc-400 mb-4">
                Other ways to submit
              </h3>
              <dl className="space-y-3 text-sm text-zinc-600">
                <div>
                  <dt className="font-mono text-xs text-zinc-900">POST /agent/quick · POST /agent/full</dt>
                  <dd className="mt-0.5">
                    Force one tier, no fallback. Add <code className="text-zinc-400">?async=true</code> for an
                    immediate 202 carrying a <code className="text-zinc-400">pollUrl</code>, and let the
                    pipeline run in the background.
                  </dd>
                </div>
                <div>
                  <dt className="font-mono text-xs text-zinc-900">POST /agent/batch</dt>
                  <dd className="mt-0.5">
                    Up to 10 claims at one tier, run concurrently. The whole batch is costed upfront and
                    rejected with 402 if the balance cannot cover it; each claim fires its own webhook.
                  </dd>
                </div>
                <div>
                  <dt className="font-mono text-xs text-zinc-900">POST /agent/lookup</dt>
                  <dd className="mt-0.5">Cache only — returns a prior analysis or nothing. Never runs the pipeline.</dd>
                </div>
                <div>
                  <dt className="font-mono text-xs text-zinc-900">GET /agent/health · /tiers · /me</dt>
                  <dd className="mt-0.5">
                    Availability, live per-tier pricing, and your own identity and balance. The first two
                    need no key, so an agent can check we are up and what we cost before it commits.
                  </dd>
                </div>
              </dl>
              <p className="text-xs text-zinc-500 mt-4">
                Full request and response schemas for every endpoint are in the{' '}
                <Link
                  href={`${API_BASE}/api/docs`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-accent underline underline-offset-2 hover:text-zinc-900"
                >
                  interactive API reference
                </Link>
                , generated from the running code.
              </p>
            </div>
          </section>

          {/* Divider */}
          <div className="border-t border-zinc-200 my-12 md:my-16" />

          {/* Tiers & Pricing — merged Pipeline + Pricing (C1 S3, 2026-07-09):
              the tier IS the depth IS the price, so it is one table said once.
              The old #pipeline anchor is preserved for inbound links. */}
          <section id="pricing" className="mb-16 md:mb-20 scroll-mt-28">
            <span id="pipeline" className="block scroll-mt-28" aria-hidden="true" />
            <SheetHeader number="03" label="Tiers & Pricing" />
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-normal text-zinc-900 mb-6 md:mb-8">
              Four depths. One record shape.
            </h2>

            <p className="text-base text-zinc-600 leading-relaxed mb-8">
              Agent API calls are charged <strong className="text-zinc-900">per call</strong>, deducted
              from your prepaid credit balance. Every tier returns the same record shape — the price
              buys retrieval depth, not a different contract.
            </p>

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-200">
                    <th className="text-left py-3 pr-4 font-mono text-[10px] tracking-widest uppercase text-zinc-400">Tier</th>
                    <th className="text-left py-3 px-2 font-mono text-[10px] tracking-widest uppercase text-zinc-400">What runs</th>
                    <th className="text-left py-3 px-2 font-mono text-[10px] tracking-widest uppercase text-zinc-400">Time</th>
                    <th className="text-right py-3 pl-2 font-mono text-[10px] tracking-widest uppercase text-zinc-400">Per call</th>
                  </tr>
                </thead>
                <tbody className="text-zinc-600 align-top">
                  <tr className="border-b border-zinc-100">
                    <td className="py-3 pr-4"><code className="text-sm font-mono font-semibold text-zinc-900">Lookup</code></td>
                    <td className="py-3 px-2 text-xs leading-relaxed">Your own prior analysis of the same claim, matched by hash. No pipeline run.</td>
                    <td className="py-3 px-2 font-mono text-xs text-zinc-400">instant</td>
                    <td className="py-3 pl-2 text-right font-mono text-zinc-900">£0.02</td>
                  </tr>
                  <tr className="border-b border-zinc-100">
                    <td className="py-3 pr-4"><code className="text-sm font-mono font-semibold text-zinc-900">Consensus</code></td>
                    <td className="py-3 px-2 text-xs leading-relaxed">Cross-user aggregate landscape, available once three different accounts have run a full check on the same claim. No pipeline run.</td>
                    <td className="py-3 px-2 font-mono text-xs text-zinc-400">instant</td>
                    <td className="py-3 pl-2 text-right font-mono text-zinc-900">£0.03</td>
                  </tr>
                  <tr className="border-b border-zinc-100">
                    <td className="py-3 pr-4"><code className="text-sm font-mono font-semibold text-zinc-900">Quick</code></td>
                    <td className="py-3 px-2 text-xs leading-relaxed">Up to 6 web searches per claim, heuristic classification, evidence mapping and orientation. Fast triage.</td>
                    <td className="py-3 px-2 font-mono text-xs text-zinc-400">~15s</td>
                    <td className="py-3 pl-2 text-right font-mono text-zinc-900">£0.07</td>
                  </tr>
                  <tr className="border-t-2 border-accent">
                    <td className="py-3 pr-4"><code className="text-sm font-mono font-semibold text-accent">Full</code></td>
                    <td className="py-3 px-2 text-xs leading-relaxed">The complete pipeline: up to 13 searches per claim across the web plus government, academic and fact-check sources, LLM classification and relevance scoring, coverage recovery.</td>
                    <td className="py-3 px-2 font-mono text-xs text-zinc-400">~60–90s</td>
                    <td className="py-3 pl-2 text-right font-mono text-accent">£0.15</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="bg-zinc-50 border border-zinc-200 p-6 mt-8">
              <h3 className="font-mono text-[10px] font-bold tracking-widest uppercase text-zinc-400 mb-4">
                How it works
              </h3>
              <ul className="space-y-2 text-sm text-zinc-600">
                <li className="flex items-start gap-2">
                  <span className="text-accent mt-0.5">1.</span>
                  <span>Top up your agent credit balance (prepaid, in GBP pence)</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-accent mt-0.5">2.</span>
                  <span>Each API call deducts the tier price from your balance</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-accent mt-0.5">3.</span>
                  <span>
                    On <code className="text-zinc-400">/agent/check</code>, <code className="text-zinc-400">max_tier</code>{' '}
                    caps how far it may escalate. <code className="text-zinc-400">/agent/quick</code> and{' '}
                    <code className="text-zinc-400">/agent/full</code> run exactly the tier you name
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-accent mt-0.5">4.</span>
                  <span>
                    You are charged for the tier actually executed, not the tier requested — and{' '}
                    <code className="text-zinc-400">_meta.limitations</code> names every stage the executed
                    tier withheld
                  </span>
                </li>
              </ul>
            </div>

            <div className="flex gap-3 bg-zinc-50 border border-zinc-200 p-4 mt-6">
              <div className="flex-shrink-0 w-6 h-6 bg-zinc-100 text-zinc-500 flex items-center justify-center font-mono text-xs font-bold rounded">?</div>
              <div className="text-xs text-zinc-600">
                <p className="font-semibold text-zinc-900 mb-1">Agent credits vs dashboard subscription</p>
                <p>
                  The Tru8 Console subscription gives you a monthly check allowance for the web dashboard.
                  Agent API credits are a separate prepaid balance for programmatic access. Both are available on any account —
                  you can use the dashboard and the API independently.
                </p>
              </div>
            </div>
          </section>

          {/* Divider */}
          <div className="border-t border-zinc-200 my-12 md:my-16" />

          {/* MCP Server */}
          <section id="mcp" className="mb-16 md:mb-20 scroll-mt-28">
            <SheetHeader number="04" label="MCP Integration" />
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-normal text-zinc-900 mb-6 md:mb-8">
              MCP Server
            </h2>

            <p className="text-base md:text-lg text-zinc-600 mb-8 leading-relaxed">
              Tru8 exposes three tools via the{' '}
              <span className="text-zinc-900 font-medium">Model Context Protocol</span>.
              Any MCP-compatible agent can discover and use them. Three routes, same tools, same API —
              pick by how much you want to install.
            </p>

            <div className="space-y-4 mb-10">
              {/* Route 1 — hosted */}
              <div className="border border-zinc-200 border-l-2 border-l-accent p-5">
                <div className="flex items-center gap-2 mb-2">
                  <Layers size={15} className="text-accent" />
                  <h3 className="text-sm font-semibold text-zinc-900">Hosted — nothing to install</h3>
                </div>
                <pre className="bg-zinc-950 text-zinc-300 p-3 overflow-x-auto text-xs font-mono mt-3">
{`https://api.trueight.com/mcp`}
                </pre>
                <p className="text-xs text-zinc-600 mt-3">
                  Streamable HTTP. Authenticate with an <code className="text-zinc-400">X-API-Key</code> header,
                  or an <code className="text-zinc-400">apiKey</code> query parameter for clients that pass
                  configuration that way. Listing the tools needs no credential; invoking one does.
                </p>
              </div>

              {/* Route 2 — Smithery */}
              <div className="border border-zinc-200 p-5">
                <div className="flex items-center gap-2 mb-2">
                  <Radio size={15} className="text-zinc-400" />
                  <h3 className="text-sm font-semibold text-zinc-900">Smithery registry</h3>
                </div>
                <p className="text-xs text-zinc-600 mt-2">
                  Listed as{' '}
                  {/* /servers/ (plural) is deliberate. Smithery's backlink
                      verification scans this page for its own canonical URL
                      form; the singular /server/ we had here reads fine to a
                      human, redirects fine in a browser, and did NOT satisfy
                      the scan. Do not "tidy" it back. */}
                  <a
                    href="https://smithery.ai/servers/samyatessmith/tru8"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-accent underline underline-offset-2 hover:text-zinc-900"
                  >
                    samyatessmith/tru8
                  </a>{' '}
                  for clients that install from a registry. Supply your API key as the single{' '}
                  <code className="text-zinc-400">apiKey</code> configuration value.
                </p>
              </div>

              {/* Route 3 — local stdio */}
              <div className="border border-zinc-200 p-5">
                <div className="flex items-center gap-2 mb-2">
                  <FileJson size={15} className="text-zinc-400" />
                  <h3 className="text-sm font-semibold text-zinc-900">Local — stdio via PyPI</h3>
                </div>
                <pre className="bg-zinc-950 text-zinc-300 p-3 overflow-x-auto text-xs font-mono mt-3">
{`pip install tru8-mcp`}
                </pre>
                <p className="text-xs text-zinc-600 mt-3 mb-3">Then, in Claude Desktop:</p>
                <pre className="bg-zinc-950 text-zinc-300 p-3 overflow-x-auto text-xs font-mono leading-relaxed">
{`{
  "mcpServers": {
    "tru8": {
      "command": "python",
      "args": ["-m", "tru8_mcp"],
      "env": {
        "TRU8_API_KEY": "tru8_sk_..."
      }
    }
  }
}`}
                </pre>
                <p className="text-xs text-zinc-500 mt-3">
                  The <code className="text-zinc-400">env</code> block is injected at server startup — the key is never
                  sent to the model. Your Claude Desktop config file
                  (<code className="text-zinc-400">claude_desktop_config.json</code>) is local-only,
                  but keep it out of any version control or backup sync that could expose secrets.
                </p>
              </div>
            </div>

            <h3 className="font-mono text-[10px] font-bold tracking-widest uppercase text-zinc-400 mb-4">
              The three tools
            </h3>
            <div className="space-y-4">
              {[
                {
                  name: 'tru8_check',
                  desc: 'Evidence research with automatic tier fallback (lookup → consensus → quick → full). Set max_tier to cap depth and cost.',
                  time: 'varies',
                  icon: 'search' as const,
                  primary: true,
                },
                {
                  name: 'tru8_get_result',
                  desc: 'Retrieve a completed check with pre-computed analytics (_computed block)',
                  time: '<1s',
                  icon: 'chart' as const,
                  primary: false,
                },
                {
                  name: 'tru8_get_result_raw',
                  desc: 'Retrieve raw check data without computed analytics — smaller payload',
                  time: '<1s',
                  icon: 'json' as const,
                  primary: false,
                },
              ].map((tool) => (
                <div key={tool.name} className={`flex items-start gap-4 border border-zinc-200 p-4 ${tool.primary ? 'border-l-2 border-l-accent' : ''}`}>
                  <div className="flex-shrink-0 mt-0.5">
                    {tool.icon === 'search' ? <Search size={16} className="text-accent" /> :
                     tool.icon === 'chart' ? <BarChart3 size={16} className="text-zinc-400" /> :
                     <FileJson size={16} className="text-zinc-400" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <code className={`text-sm font-mono font-semibold ${tool.primary ? 'text-accent' : 'text-zinc-900'}`}>{tool.name}</code>
                    <p className="text-sm text-zinc-600 mt-1">{tool.desc}</p>
                  </div>
                  <div className="flex-shrink-0 font-mono text-xs text-zinc-400">
                    {tool.time}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Divider */}
          <div className="border-t border-zinc-200 my-12 md:my-16" />

          {/* What you get back — concepts, not a schema dump. The generated API
              reference is the single source of truth for field-level shape;
              duplicating it here is how this page drifted from the code before. */}
          <section id="response" className="mb-16 md:mb-20 scroll-mt-28">
            <SheetHeader number="05" label="Response" />
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-normal text-zinc-900 mb-6 md:mb-8">
              What You Get Back
            </h2>

            <p className="text-base text-zinc-600 leading-relaxed mb-8">
              Every tier returns the same record. No verdict, no credibility score — a landscape your
              agent can reason over.
            </p>

            <dl className="space-y-4 mb-8">
              {[
                {
                  key: 'claims[]',
                  body: 'Each claim decomposed into 1–5 elements — the separate things that must hold for the claim to hold.',
                },
                {
                  key: 'elements[].state',
                  body: 'supported, disputed, unresolved, or contextual — the last meaning related evidence exists but none of it directly bears on the element. Derived mechanically from what is mapped to that element, never asserted by a model on its own.',
                },
                {
                  key: 'elements[].evidenceRefs[]',
                  body: 'The link between an element and a source: relationship (supports / challenges / context) plus one sentence of reasoning.',
                },
                {
                  key: 'evidence[]',
                  body: 'Every source classified by tier (primary / reporting / commentary) and type (data / official / news / analysis / opinion / academic), with snippet, published date and archive URL.',
                },
                {
                  key: '_meta',
                  body: 'executedTier, chargedPence, limitations, and a landscape block covering element states, source diversity, freshness and named gaps.',
                },
                {
                  key: '_computed',
                  body: 'Ready-made analytics — tier and type distributions, corroboration groups, diagnostic values. Included by default; send compact: true to drop it and the evidence arrays.',
                },
                {
                  key: '_manifest',
                  body: 'A signed hash of the landscape plus a verifyUrl. Null when manifest signing is not enabled on the deployment serving you.',
                },
              ].map((row) => (
                <div key={row.key} className="border-l-2 border-zinc-200 pl-4">
                  <dt className="font-mono text-sm font-semibold text-zinc-900">{row.key}</dt>
                  <dd className="text-sm text-zinc-600 mt-1 leading-relaxed">{row.body}</dd>
                </div>
              ))}
            </dl>

            <p className="text-sm text-zinc-500 mb-3 font-mono text-xs tracking-wide uppercase">
              _meta, abridged
            </p>
            <pre className="bg-zinc-950 text-zinc-300 p-4 overflow-x-auto text-xs font-mono leading-relaxed">
{`"_meta": {
  "executedTier": "quick",
  "chargedPence": 7,
  "limitations": [
    "heuristic_classification", "no_api_sources", "no_coverage_recovery",
    "no_factcheck_lookup", "reduced_query_breadth", ...
  ],
  "landscape": {
    "elementCount": 3,
    "elementStates": { "supported": 2, "unresolved": 1 },
    "sourceDiversity": { "uniqueDomains": 5, "typeCoverage": 3 },
    "freshness": { "freshestDaysAgo": 2, "undatedCount": 1 },
    "gaps": [{ "reason": "no_primary_sources" }],
    "providerStatus": null
  }
}`}
            </pre>

            <div className="flex gap-3 bg-zinc-50 border border-zinc-200 p-4 mt-6">
              <div className="flex-shrink-0 w-6 h-6 bg-zinc-100 text-zinc-500 flex items-center justify-center font-mono text-xs font-bold rounded">?</div>
              <div className="text-xs text-zinc-600">
                <p className="font-semibold text-zinc-900 mb-1">limitations is the honest part</p>
                <p>
                  It is derived from the pipeline configuration rather than written by hand, so it cannot
                  drift from what the tier actually skipped. A quick call returns eleven entries. A full
                  call returns none. If you are served a cached analysis produced at a lower tier,{' '}
                  <code className="text-zinc-400">cachedTier</code> says so.
                </p>
              </div>
            </div>

            <p className="text-sm text-zinc-500 mt-6">
              Field-by-field schemas for every endpoint live in the{' '}
              <Link
                href={`${API_BASE}/api/docs`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-accent underline underline-offset-2 hover:text-zinc-900"
              >
                interactive reference
              </Link>
              , generated from the running API.
            </p>
          </section>

          {/* Divider */}
          <div className="border-t border-zinc-200 my-12 md:my-16" />

          {/* Limits, errors & webhooks — operational surface, kept short.
              Legacy anchors preserved so older inbound links still land. */}
          <section id="limits" className="mb-16 md:mb-20 scroll-mt-28">
            <span id="rate-limits" className="block scroll-mt-28" aria-hidden="true" />
            <span id="errors" className="block scroll-mt-28" aria-hidden="true" />
            <span id="webhooks" className="block scroll-mt-28" aria-hidden="true" />
            <span id="async" className="block scroll-mt-28" aria-hidden="true" />
            <span id="batch" className="block scroll-mt-28" aria-hidden="true" />
            <span id="discovery" className="block scroll-mt-28" aria-hidden="true" />
            <SheetHeader number="06" label="Operations" />
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-normal text-zinc-900 mb-6 md:mb-8">
              Limits, Errors, Webhooks
            </h2>

            <div className="space-y-8 text-base text-zinc-600 leading-relaxed">
              <div>
                <h3 className="text-sm font-semibold text-zinc-900 mb-3">Rate limits</h3>
                <p className="text-sm mb-4">
                  Applied <strong className="text-zinc-900">per API key</strong>, not per IP — agents sharing
                  a cloud IP do not interfere with each other.
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <tbody className="text-zinc-600">
                      <tr className="border-b border-zinc-100"><td className="py-2 pr-4"><code className="text-xs">POST /agent/full · /agent/batch</code></td><td className="py-2 pl-2 font-mono text-xs">5 / minute</td></tr>
                      <tr className="border-b border-zinc-100"><td className="py-2 pr-4"><code className="text-xs">POST /agent/check · /agent/quick</code></td><td className="py-2 pl-2 font-mono text-xs">10 / minute</td></tr>
                      <tr className="border-b border-zinc-100"><td className="py-2 pr-4"><code className="text-xs">POST /agent/lookup · GET /agent/result/*</code></td><td className="py-2 pl-2 font-mono text-xs">30 / minute</td></tr>
                      <tr><td className="py-2 pr-4"><code className="text-xs">GET /agent/health · /tiers · /me · /credits/balance</code></td><td className="py-2 pl-2 font-mono text-xs">60 / minute</td></tr>
                    </tbody>
                  </table>
                </div>
                <p className="text-sm text-zinc-500 mt-4">
                  Pipeline endpoints also cap <strong className="text-zinc-700">5 simultaneous processing checks</strong>{' '}
                  per key. Exceeding either limit returns 429 with a{' '}
                  <code className="text-zinc-400">Retry-After</code> header.
                </p>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-zinc-900 mb-3">Errors worth handling</h3>
                <p className="text-sm">
                  Every error returns JSON with a <code className="text-zinc-400">detail</code> field. Four
                  matter operationally: <strong className="text-zinc-900">402</strong> means top up (
                  <code className="text-zinc-400">/agent/credits/purchase</code>);{' '}
                  <strong className="text-zinc-900">429</strong> means wait for{' '}
                  <code className="text-zinc-400">Retry-After</code>;{' '}
                  <strong className="text-zinc-900">409</strong> means an{' '}
                  <code className="text-zinc-400">Idempotency-Key</code> was reused with different
                  parameters; <strong className="text-zinc-900">502</strong> is a pipeline failure and
                  refunds your credits, <strong className="text-zinc-900">504</strong> is a timeout and
                  applies no charge at all. Either way you are{' '}
                  <strong className="text-zinc-900">not billed for work that did not complete</strong>. The
                  full code list is in the API reference.
                </p>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-zinc-900 mb-3">Webhooks</h3>
                <p className="text-sm mb-4">
                  Register a callback with your API key and skip polling. Up to 5 active webhooks per
                  account; HTTPS and public addresses only.
                </p>
                <pre className="bg-zinc-950 text-zinc-300 p-4 overflow-x-auto text-xs font-mono leading-relaxed">
{`curl -X POST https://api.trueight.com/api/v1/webhooks \\
  -H "X-API-Key: $TRU8_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"url": "https://example.com/hooks/tru8",
       "events": ["check.completed", "check.failed"]}'

# The response carries a signing secret, shown once. Store it.`}
                </pre>

                <div className="grid sm:grid-cols-2 gap-4 mt-4">
                  <div className="bg-zinc-50 border border-zinc-200 p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Radio size={14} className="text-accent" />
                      <p className="text-xs font-semibold text-zinc-900">Payload shape</p>
                    </div>
                    <pre className="bg-zinc-950 text-zinc-300 p-3 overflow-x-auto text-[11px] font-mono leading-relaxed">
{`{
  "event": "check.completed",
  "timestamp": "2026-08-06T12:00:00Z",
  "data": {
    "checkId": "...",
    "status": "completed",
    "tier": "quick"
  }
}`}
                    </pre>
                  </div>
                  <div className="bg-zinc-50 border border-zinc-200 p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Bell size={14} className="text-accent" />
                      <p className="text-xs font-semibold text-zinc-900">Verify before you trust it</p>
                    </div>
                    <p className="text-xs text-zinc-500">
                      Each delivery carries <code className="text-zinc-400">X-Tru8-Signature</code>: an
                      HMAC-SHA256 hex digest of the raw body, keyed with your signing secret. Recompute it
                      and compare before acting. <code className="text-zinc-400">X-Tru8-Event</code> names
                      the event.
                    </p>
                  </div>
                </div>

                <p className="text-sm text-zinc-500 mt-4">
                  Delivery is best-effort: 2 attempts with exponential backoff, and a webhook is
                  deactivated after 10 consecutive failures. Make your handler idempotent — the same event
                  may arrive twice. <code className="text-zinc-400">check.failed</code> carries an{' '}
                  <code className="text-zinc-400">error</code> string in place of the tier, and its credits
                  have already been refunded.
                </p>
              </div>
            </div>
          </section>

          {/* Divider */}
          <div className="border-t border-zinc-200 my-12 md:my-16" />

          {/* FAQ */}
          <section id="faq" className="mb-16 md:mb-20 scroll-mt-28">
            <SheetHeader number="07" label="FAQ" />
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-normal text-zinc-900 mb-8 md:mb-10">
              Frequently asked questions
            </h2>
            <dl className="divide-y divide-zinc-100 border-t border-zinc-100">
              {DEV_FAQS.map((item) => (
                <div key={item.q} className="py-6 md:py-7">
                  <dt className="text-base md:text-lg font-semibold text-zinc-900 mb-2">
                    {item.q}
                  </dt>
                  <dd className="text-sm md:text-base text-zinc-600 leading-relaxed">
                    {item.a}
                  </dd>
                </div>
              ))}
            </dl>
          </section>

          {/* Divider */}
          <div className="border-t border-zinc-200 my-12 md:my-16" />

          {/* API Docs + Resources */}
          <section id="docs" className="mb-16 md:mb-20 scroll-mt-28">
            <SheetHeader number="08" label="Resources" />
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-normal text-zinc-900 mb-6 md:mb-8">
              Documentation
            </h2>

            <p className="text-base text-zinc-600 leading-relaxed mb-8">
              Both references are generated from the running API, so they cannot fall behind it.
            </p>

            <div className="grid md:grid-cols-2 gap-6">
              <Link
                href={`${API_BASE}/api/docs`}
                target="_blank"
                rel="noopener noreferrer"
                className="border border-zinc-200 p-6 hover:border-zinc-400 transition-colors group"
              >
                <div className="flex items-center gap-3 mb-3">
                  <BarChart3 size={20} className="text-zinc-400 group-hover:text-zinc-900 transition-colors" />
                  <h3 className="font-semibold text-zinc-900">Interactive API Docs</h3>
                </div>
                <p className="text-sm text-zinc-600">
                  Swagger UI with all endpoints, request/response schemas, and try-it-out.
                </p>
                <div className="font-mono text-xs text-zinc-400 mt-3">/api/docs</div>
              </Link>

              <Link
                href={`${API_BASE}/api/redoc`}
                target="_blank"
                rel="noopener noreferrer"
                className="border border-zinc-200 p-6 hover:border-zinc-400 transition-colors group"
              >
                <div className="flex items-center gap-3 mb-3">
                  <FileJson size={20} className="text-zinc-400 group-hover:text-zinc-900 transition-colors" />
                  <h3 className="font-semibold text-zinc-900">ReDoc Reference</h3>
                </div>
                <p className="text-sm text-zinc-600">
                  Clean reference documentation with detailed type definitions.
                </p>
                <div className="font-mono text-xs text-zinc-400 mt-3">/api/redoc</div>
              </Link>
            </div>

            <p className="text-sm text-zinc-500 mt-6">
              New to the API?{' '}
              <Link
                href="/blog/evidence-research-for-agents"
                className="text-accent underline underline-offset-2 hover:text-zinc-900 transition-colors"
              >
                Read: why structured evidence research matters for AI agents →
              </Link>
            </p>
          </section>

          {/* CTA */}
          <div className="mt-16 md:mt-20 text-center border border-zinc-200 p-8 md:p-12">
            <div className="flex justify-center mb-4">
              <Key size={32} className="text-zinc-300" />
            </div>
            <h3 className="text-2xl md:text-3xl font-normal text-zinc-900 mb-4">
              Start Building
            </h3>
            <p className="text-zinc-500 mb-6 max-w-lg mx-auto">
              Create an API key and submit your first check in under a minute.
            </p>
            <TrackedLink
              event="get_api_key_click"
              eventProps={{ surface: 'developers_cta' }}
              href="/dashboard/settings?tab=developer"
              className="inline-flex items-center gap-2 px-8 py-4 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors"
            >
              Get API Key
            </TrackedLink>
          </div>

          {/* Mono metadata footer */}
          <div className="mt-12 pt-6 border-t border-zinc-100">
            <span className="font-mono text-[10px] tracking-widest uppercase text-zinc-400">
              TRU8 — DEVELOPERS — V2.0
            </span>
          </div>
        </div>
      </main>

      <Footer />
    </>
  );
}
