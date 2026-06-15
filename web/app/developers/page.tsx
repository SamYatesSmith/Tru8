import { Navigation } from '@/components/layout/navigation';
import { MobileBottomNav } from '@/components/layout/mobile-bottom-nav';
import { Footer } from '@/components/layout/footer';
import { ArrowLeft, Key, Search, FileJson, BarChart3, ShieldCheck, Bell, Layers, Radio } from 'lucide-react';
import Link from 'next/link';
import { TrackedLink } from '@/components/analytics/tracked-link';

export const metadata = {
  title: 'API & MCP Server for AI Agents',
  description: 'Structured evidence research in one API call. Three tiers, three payment rails, MCP server for Claude and other AI agents. From £0.02/query.',
  alternates: { canonical: '/developers' },
};

const TOC_ITEMS = [
  { id: 'quick-start', label: 'Quick Start' },
  { id: 'pipeline', label: 'Pipeline' },
  { id: 'mcp', label: 'MCP' },
  { id: 'pricing', label: 'Pricing' },
  { id: 'async', label: 'Async' },
  { id: 'batch', label: 'Batch' },
  { id: 'webhooks', label: 'Webhooks' },
  { id: 'discovery', label: 'Discovery' },
  { id: 'rate-limits', label: 'Limits' },
  { id: 'errors', label: 'Errors' },
  { id: 'response', label: 'Response' },
  { id: 'docs', label: 'Docs' },
];

export default function DevelopersPage() {
  return (
    <>
      <Navigation />
      <MobileBottomNav />

      <main className="min-h-screen pt-24 md:pt-32 pb-24 md:pb-20">
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
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4">
              Module — Developer API
            </div>
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold text-zinc-900 mb-6 md:mb-8">
              The evidence landscape behind any claim. One API call.
            </h1>

            <div className="space-y-6 text-base md:text-lg text-zinc-600 leading-relaxed">
              <p>
                Submit a claim, URL, or article. Get back structured evidence — organised by source tier
                (primary, reporting, commentary) and type (data, official, news, analysis, academic),
                with element decomposition and relationship mapping.
              </p>

              <p>
                Grounding APIs return passages and a score. Tru8 returns structure:{' '}
                <code className="text-sm font-mono text-zinc-900">tier</code>,{' '}
                <code className="text-sm font-mono text-zinc-900">type</code>,{' '}
                <code className="text-sm font-mono text-zinc-900">relationship</code>,{' '}
                <code className="text-sm font-mono text-zinc-900">state</code>,{' '}
                <code className="text-sm font-mono text-zinc-900">gaps</code>,{' '}
                <code className="text-sm font-mono text-zinc-900">receipts</code>,{' '}
                <code className="text-sm font-mono text-zinc-900">manifest</code>.{' '}
                <Link
                  href="/compare"
                  className="text-accent underline underline-offset-2 hover:text-zinc-900 transition-colors"
                >
                  Same claim, Tru8 vs four grounding APIs →
                </Link>
              </p>

              <div className="bg-zinc-50 border-l-4 border-accent px-6 py-5 my-8">
                <p className="text-zinc-900 font-medium text-lg md:text-xl leading-relaxed">
                  One API call.<br />
                  Multi-source evidence retrieval.<br />
                  Structured, not summarised.<br />
                  <span className="text-accent">Your agent decides what matters.</span>
                </p>
              </div>
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
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4">
              Module — Quick Start
            </div>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-zinc-900 mb-6 md:mb-8">
              Three Steps
            </h2>

            <div className="space-y-8">
              {/* Step 1 */}
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 bg-accent text-white flex items-center justify-center font-mono text-sm font-bold">
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
                      <p>Your API key carries your identity and usage quota. Treat it like a password.</p>
                      <ul className="list-disc list-inside space-y-0.5 text-zinc-500">
                        <li>Store in environment variables or a secrets manager — never in source code</li>
                        <li>Never commit keys to git, logs, or client-side bundles</li>
                        <li>If a key is exposed, revoke it immediately in dashboard settings and create a new one</li>
                        <li>Use separate keys per agent or environment for auditability</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>

              {/* Step 2 */}
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 bg-accent text-white flex items-center justify-center font-mono text-sm font-bold">
                  2
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="text-lg font-semibold text-zinc-900 mb-2">Submit a claim</h3>
                  <pre className="bg-zinc-950 text-zinc-300 p-4 overflow-x-auto text-xs font-mono leading-relaxed">
{`curl -X POST https://api.trueight.com/api/v1/agent/quick \\
  -H "X-API-Key: $TRU8_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"claim": "Global average temperature rose 1.1°C since pre-industrial times"}'`}
                  </pre>
                  <p className="text-zinc-500 text-xs mt-2 font-mono">
                    Returns structured result with _meta (executedTier, chargedPence)
                  </p>
                </div>
              </div>

              {/* Step 3 */}
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 bg-accent text-white flex items-center justify-center font-mono text-sm font-bold">
                  3
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="text-lg font-semibold text-zinc-900 mb-2">Retrieve the result</h3>
                  <pre className="bg-zinc-950 text-zinc-300 p-4 overflow-x-auto text-xs font-mono leading-relaxed">
{`curl https://api.trueight.com/api/v1/agent/result/{check_id} \\
  -H "X-API-Key: $TRU8_API_KEY"`}
                  </pre>
                  <p className="text-zinc-500 text-xs mt-2 font-mono">
                    Completed checks return the full evidence landscape. Processing checks return status for polling.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Divider */}
          <div className="border-t border-zinc-200 my-12 md:my-16" />

          {/* Pipeline Depth */}
          <section id="pipeline" className="mb-16 md:mb-20 scroll-mt-28">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4">
              Module — Pipeline
            </div>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-zinc-900 mb-6 md:mb-8">
              What Each Tier Runs
            </h2>

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-200">
                    <th className="text-left py-3 pr-4 font-mono text-[10px] tracking-widest uppercase text-zinc-400">Pipeline stage</th>
                    <th className="text-center py-3 px-2 font-mono text-[10px] tracking-widest uppercase text-zinc-400">Quick</th>
                    <th className="text-center py-3 pl-2 font-mono text-[10px] tracking-widest uppercase text-accent">Full</th>
                  </tr>
                </thead>
                <tbody className="text-zinc-600">
                  <tr className="border-b border-zinc-50"><td className="py-2 pr-4">Claim extraction + decomposition</td><td className="text-center">Yes</td><td className="text-center">Yes</td></tr>
                  <tr className="border-b border-zinc-50"><td className="py-2 pr-4">Web search (Serper/Brave/SerpAPI)</td><td className="text-center">1 query/element</td><td className="text-center">3 queries/element</td></tr>
                  <tr className="border-b border-zinc-50"><td className="py-2 pr-4">Government + academic APIs</td><td className="text-center text-zinc-300">No</td><td className="text-center">Yes</td></tr>
                  <tr className="border-b border-zinc-50"><td className="py-2 pr-4">Google Fact-Check API</td><td className="text-center text-zinc-300">No</td><td className="text-center">Yes</td></tr>
                  <tr className="border-b border-zinc-50"><td className="py-2 pr-4">Evidence classification</td><td className="text-center">Heuristic</td><td className="text-center">LLM</td></tr>
                  <tr className="border-b border-zinc-50"><td className="py-2 pr-4">LLM relevance scoring</td><td className="text-center text-zinc-300">No</td><td className="text-center">Yes</td></tr>
                  <tr className="border-b border-zinc-50"><td className="py-2 pr-4">Evidence mapping + orientation</td><td className="text-center">Yes</td><td className="text-center">Yes</td></tr>
                  <tr><td className="py-2 pr-4">Coverage recovery</td><td className="text-center text-zinc-300">No</td><td className="text-center">Yes</td></tr>
                </tbody>
              </table>
            </div>
            <p className="text-xs text-zinc-400 mt-4">
              Lookup and Consensus tiers return previously computed results — no pipeline execution.
            </p>
          </section>

          {/* Divider */}
          <div className="border-t border-zinc-200 my-12 md:my-16" />

          {/* MCP Server */}
          <section id="mcp" className="mb-16 md:mb-20 scroll-mt-28">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4">
              Module — MCP Integration
            </div>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-zinc-900 mb-6 md:mb-8">
              MCP Server
            </h2>

            <p className="text-base md:text-lg text-zinc-600 mb-8 leading-relaxed">
              Tru8 exposes three tools via the{' '}
              <span className="text-zinc-900 font-medium">Model Context Protocol</span>.
              Any MCP-compatible agent (Claude, GPT, Gemini) can discover and use Tru8 automatically.
            </p>

            <div className="space-y-4">
              {[
                {
                  name: 'tru8_check',
                  desc: 'Evidence research with tier fallback (lookup \u2192 consensus \u2192 quick \u2192 full). Set max_tier to control depth and cost.',
                  time: 'varies',
                  icon: 'search' as const,
                  primary: true,
                },
                {
                  name: 'tru8_get_result',
                  desc: 'Retrieve completed check with pre-computed analytics (_computed block)',
                  time: '<1s',
                  icon: 'chart' as const,
                  primary: false,
                },
                {
                  name: 'tru8_get_result_raw',
                  desc: 'Retrieve raw check data without computed analytics',
                  time: '<1s',
                  icon: 'json' as const,
                  primary: false,
                },
              ].map((tool) => (
                <div key={tool.name} className={`flex items-start gap-4 border border-zinc-200 p-4 ${tool.primary ? 'border-l-4 border-l-accent' : ''}`}>
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

            <div className="mt-8">
              <p className="text-sm text-zinc-600 mb-3">Configure for Claude Desktop:</p>
              <pre className="bg-zinc-950 text-zinc-300 p-4 overflow-x-auto text-xs font-mono leading-relaxed">
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
                but ensure it is excluded from any version control or backup sync that could expose secrets.
              </p>
            </div>
          </section>

          {/* Divider */}
          <div className="border-t border-zinc-200 my-12 md:my-16" />

          {/* Pricing Model */}
          <section id="pricing" className="mb-16 md:mb-20 scroll-mt-28">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4">
              Module — Pricing
            </div>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-zinc-900 mb-6 md:mb-8">
              What You Pay For
            </h2>

            <div className="space-y-6 text-base text-zinc-600 leading-relaxed">
              <p>
                Agent API calls are charged <strong className="text-zinc-900">per call</strong>, deducted
                from your prepaid credit balance. This is separate from dashboard subscriptions.
              </p>

              <div className="bg-zinc-50 border border-zinc-200 p-6">
                <h3 className="font-mono text-[10px] font-bold tracking-widest uppercase text-zinc-400 mb-4">
                  Per-call pricing
                </h3>
                <div className="space-y-3">
                  <div className="flex justify-between items-baseline border-b border-zinc-100 pb-2">
                    <div>
                      <code className="text-sm font-mono font-semibold text-zinc-900">Lookup</code>
                      <span className="text-xs text-zinc-400 ml-2">instant</span>
                    </div>
                    <div className="text-right">
                      <span className="font-mono text-sm text-zinc-900">£0.02</span>
                      <p className="text-xs text-zinc-400">Cached prior analysis. Instant hash match on your previous research.</p>
                    </div>
                  </div>
                  <div className="flex justify-between items-baseline border-b border-zinc-100 pb-2">
                    <div>
                      <code className="text-sm font-mono font-semibold text-zinc-900">Consensus</code>
                      <span className="text-xs text-zinc-400 ml-2">instant</span>
                    </div>
                    <div className="text-right">
                      <span className="font-mono text-sm text-zinc-900">£0.03</span>
                      <p className="text-xs text-zinc-400">Cross-user aggregate landscape. Available when 3+ independent checks exist.</p>
                    </div>
                  </div>
                  <div className="flex justify-between items-baseline border-b border-zinc-100 pb-2">
                    <div>
                      <code className="text-sm font-mono font-semibold text-zinc-900">Quick</code>
                      <span className="text-xs text-zinc-400 ml-2">~15s</span>
                    </div>
                    <div className="text-right">
                      <span className="font-mono text-sm text-zinc-900">£0.07</span>
                      <p className="text-xs text-zinc-400">Web search + heuristic classification. Fast triage for time-sensitive queries.</p>
                    </div>
                  </div>
                  <div className="flex justify-between items-baseline">
                    <div>
                      <code className="text-sm font-mono font-semibold text-accent">Full</code>
                      <span className="text-xs text-zinc-400 ml-2">~60-90s</span>
                    </div>
                    <div className="text-right">
                      <span className="font-mono text-sm text-accent">£0.15</span>
                      <p className="text-xs text-zinc-400">30+ sources, LLM classification, element decomposition, coverage recovery.</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-zinc-50 border border-zinc-200 p-6">
                <h3 className="font-mono text-[10px] font-bold tracking-widest uppercase text-zinc-400 mb-4">
                  How it works
                </h3>
                <ul className="space-y-2 text-sm">
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
                    <span>Use <code className="text-zinc-400">max_tier</code> to cap maximum spend per call</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-accent mt-0.5">4.</span>
                    <span>You are only charged for the tier actually executed, not the tier requested</span>
                  </li>
                </ul>
              </div>

              <div className="flex gap-3 bg-zinc-50 border border-zinc-200 p-4">
                <div className="flex-shrink-0 w-6 h-6 bg-accent/10 text-accent flex items-center justify-center font-mono text-xs font-bold rounded">?</div>
                <div className="text-xs text-zinc-600">
                  <p className="font-semibold text-zinc-900 mb-1">Agent credits vs dashboard subscription</p>
                  <p>
                    Dashboard subscriptions (Starter, Professional) give you a monthly check allowance for the web dashboard.
                    Agent API credits are a separate prepaid balance for programmatic access. Both are available on any account —
                    you can use the dashboard and the API independently.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Divider */}
          <div className="border-t border-zinc-200 my-12 md:my-16" />

          {/* Async Mode */}
          <section id="async" className="mb-16 md:mb-20 scroll-mt-28">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4">
              Module — Async Mode
            </div>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-zinc-900 mb-6 md:mb-8">
              Non-Blocking Submission
            </h2>

            <div className="space-y-6 text-base text-zinc-600 leading-relaxed">
              <p>
                Add <code className="text-zinc-900 font-mono text-sm">?async=true</code> to{' '}
                <code className="text-zinc-400">/agent/quick</code> or{' '}
                <code className="text-zinc-400">/agent/full</code> to get an immediate 202 response.
                The pipeline runs in the background — poll for the result when ready.
              </p>

              <pre className="bg-zinc-950 text-zinc-300 p-4 overflow-x-auto text-xs font-mono leading-relaxed">
{`# Submit async
curl -X POST "https://api.trueight.com/api/v1/agent/full?async=true" \\
  -H "X-API-Key: $TRU8_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"claim": "The UK left the EU in 2020"}'

# Response: 202 Accepted
{
  "checkId": "abc-123",
  "status": "processing",
  "tier": "full",
  "chargedPence": 15,
  "pollUrl": "/api/v1/agent/result/abc-123",
  "estimatedSeconds": 60
}

# Poll for result
curl "https://api.trueight.com/api/v1/agent/result/abc-123" \\
  -H "X-API-Key: $TRU8_API_KEY"
# While processing: { "status": "processing", "checkId": "abc-123", "hit": false }
# When complete:   { full result payload }`}
              </pre>

              <p className="text-sm text-zinc-500">
                Prefer <a href="#webhooks" className="text-accent hover:underline">webhooks</a> over
                polling — register a callback URL and receive events when checks complete or fail.
              </p>
            </div>
          </section>

          {/* Divider */}
          <div className="border-t border-zinc-200 my-12 md:my-16" />

          {/* Batch Submission */}
          <section id="batch" className="mb-16 md:mb-20 scroll-mt-28">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4">
              Module — Batch Mode
            </div>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-zinc-900 mb-6 md:mb-8">
              Multi-Claim Submission
            </h2>

            <div className="space-y-6 text-base text-zinc-600 leading-relaxed">
              <p>
                Submit up to <strong className="text-zinc-900">10 claims</strong> in a single call.
                All claims run concurrently in the background at the same tier. Each creates its own
                check with a separate poll URL.
              </p>

              <pre className="bg-zinc-950 text-zinc-300 p-4 overflow-x-auto text-xs font-mono leading-relaxed">
{`curl -X POST https://api.trueight.com/api/v1/agent/batch \\
  -H "X-API-Key: $TRU8_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "tier": "quick",
    "claims": [
      { "claim": "Global sea levels rose 3.6mm per year since 2006" },
      { "claim": "The Amazon rainforest produces 20% of world oxygen" },
      { "claim": "Electric vehicles have lower lifetime emissions than petrol cars" }
    ]
  }'

# Response: 202 Accepted
{
  "accepted": 3,
  "tier": "quick",
  "totalChargedPence": 21,
  "estimatedSeconds": 15,
  "checks": [
    { "index": 0, "checkId": "...", "pollUrl": "/api/v1/agent/result/..." },
    { "index": 1, "checkId": "...", "pollUrl": "/api/v1/agent/result/..." },
    { "index": 2, "checkId": "...", "pollUrl": "/api/v1/agent/result/..." }
  ]
}`}
              </pre>

              <div className="grid sm:grid-cols-2 gap-4">
                <div className="bg-zinc-50 border border-zinc-200 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Layers size={14} className="text-accent" />
                    <p className="text-xs font-semibold text-zinc-900">Upfront balance check</p>
                  </div>
                  <p className="text-xs text-zinc-500">
                    Total cost is verified before any claims are submitted. If your balance
                    can&apos;t cover all claims, the entire batch is rejected with 402.
                  </p>
                </div>
                <div className="bg-zinc-50 border border-zinc-200 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Bell size={14} className="text-accent" />
                    <p className="text-xs font-semibold text-zinc-900">Webhook per claim</p>
                  </div>
                  <p className="text-xs text-zinc-500">
                    Each claim fires its own <code className="text-zinc-400">check.completed</code> or{' '}
                    <code className="text-zinc-400">check.failed</code> webhook event independently.
                  </p>
                </div>
              </div>

              <div className="flex gap-3 bg-zinc-50 border border-zinc-200 p-4">
                <div className="flex-shrink-0 w-6 h-6 bg-accent/10 text-accent flex items-center justify-center font-mono text-xs font-bold rounded">?</div>
                <div className="text-xs text-zinc-600">
                  <p className="font-semibold text-zinc-900 mb-1">Idempotency in batch</p>
                  <p>
                    If you send an <code className="text-zinc-400">Idempotency-Key</code> header, each claim
                    receives a derived key (<code className="text-zinc-400">your-key_0</code>,{' '}
                    <code className="text-zinc-400">your-key_1</code>, etc). Safe to retry the
                    entire batch on network failure.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Divider */}
          <div className="border-t border-zinc-200 my-12 md:my-16" />

          {/* Webhooks */}
          <section id="webhooks" className="mb-16 md:mb-20 scroll-mt-28">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4">
              Module — Webhooks
            </div>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-zinc-900 mb-6 md:mb-8">
              Event Notifications
            </h2>

            <div className="space-y-6 text-base text-zinc-600 leading-relaxed">
              <p>
                Register a webhook URL in your{' '}
                <Link href="/dashboard/settings?tab=developer" className="text-accent hover:underline">
                  dashboard settings
                </Link>
                {' '}to receive POST callbacks when checks complete or fail. No polling required.
              </p>

              <div className="space-y-4">
                {[
                  {
                    event: 'check.completed',
                    desc: 'Pipeline finished successfully. Result is ready to retrieve.',
                    payload: '{ "checkId": "...", "status": "completed", "tier": "quick" }',
                  },
                  {
                    event: 'check.failed',
                    desc: 'Pipeline error or timeout. Credits have been refunded.',
                    payload: '{ "checkId": "...", "status": "failed", "error": "Pipeline timed out" }',
                  },
                ].map((wh) => (
                  <div key={wh.event} className="border border-zinc-200 p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Radio size={14} className="text-accent" />
                      <code className="text-sm font-mono font-semibold text-zinc-900">{wh.event}</code>
                    </div>
                    <p className="text-sm text-zinc-600 mb-3">{wh.desc}</p>
                    <pre className="bg-zinc-950 text-zinc-300 p-3 overflow-x-auto text-xs font-mono">
{wh.payload}
                    </pre>
                  </div>
                ))}
              </div>

              <div className="flex gap-3 bg-zinc-50 border border-zinc-200 p-4">
                <div className="flex-shrink-0 w-6 h-6 bg-accent/10 text-accent flex items-center justify-center font-mono text-xs font-bold rounded">?</div>
                <div className="text-xs text-zinc-600">
                  <p className="font-semibold text-zinc-900 mb-1">Delivery guarantee</p>
                  <p>
                    Webhooks are delivered best-effort with automatic retries (2 attempts, exponential backoff).
                    If your endpoint returns a non-2xx status, delivery is retried. Design your handler to be
                    idempotent — you may receive the same event more than once.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Divider */}
          <div className="border-t border-zinc-200 my-12 md:my-16" />

          {/* Agent Discovery */}
          <section id="discovery" className="mb-16 md:mb-20 scroll-mt-28">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4">
              Module — Agent Discovery
            </div>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-zinc-900 mb-6 md:mb-8">
              Self-Service Endpoints
            </h2>

            <div className="space-y-6 text-base text-zinc-600 leading-relaxed">
              <p>
                These endpoints let agents inspect the API programmatically — check availability,
                discover pricing, and verify their own identity before submitting work.
              </p>

              <div className="space-y-3">
                {[
                  {
                    method: 'GET',
                    path: '/agent/health',
                    desc: 'API and dependency status (database, Redis). No auth required.',
                    auth: false,
                  },
                  {
                    method: 'GET',
                    path: '/agent/tiers',
                    desc: 'Available tiers with per-call pricing (pence) and estimated latency. No auth required.',
                    auth: false,
                  },
                  {
                    method: 'GET',
                    path: '/agent/me',
                    desc: 'Authenticated identity, provider type, and current credit balance.',
                    auth: true,
                  },
                  {
                    method: 'GET',
                    path: '/agent/stats',
                    desc: 'Usage analytics — transactions by tier and provider, total agent checks.',
                    auth: true,
                  },
                  {
                    method: 'GET',
                    path: '/agent/credits/balance',
                    desc: 'Current prepaid credit balance in pence.',
                    auth: true,
                  },
                ].map((ep) => (
                  <div key={ep.path} className="flex items-start gap-4 border border-zinc-200 p-4">
                    <div className="flex-shrink-0">
                      <span className="inline-block font-mono text-[10px] font-bold tracking-wider bg-zinc-100 text-zinc-500 px-2 py-1">
                        {ep.method}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <code className="text-sm font-mono font-semibold text-zinc-900">{ep.path}</code>
                      <p className="text-sm text-zinc-600 mt-1">{ep.desc}</p>
                    </div>
                    <div className="flex-shrink-0">
                      {ep.auth ? (
                        <span className="font-mono text-[10px] text-zinc-400 bg-zinc-50 px-2 py-1 border border-zinc-100">auth</span>
                      ) : (
                        <span className="font-mono text-[10px] text-zinc-300 bg-zinc-50 px-2 py-1 border border-zinc-100">public</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              <p className="text-sm text-zinc-500">
                An agent can call <code className="text-zinc-400">/agent/health</code> to confirm the API is live,
                then <code className="text-zinc-400">/agent/tiers</code> to discover current pricing, then{' '}
                <code className="text-zinc-400">/agent/me</code> to check its balance — all before submitting
                a single claim.
              </p>
            </div>
          </section>

          {/* Divider */}
          <div className="border-t border-zinc-200 my-12 md:my-16" />

          {/* Rate Limits */}
          <section id="rate-limits" className="mb-16 md:mb-20 scroll-mt-28">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4">
              Module — Rate Limits
            </div>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-zinc-900 mb-6 md:mb-8">
              Throttling
            </h2>

            <div className="space-y-6 text-base text-zinc-600 leading-relaxed">
              <p>
                Rate limits are applied <strong className="text-zinc-900">per API key</strong>, not per IP address.
                Agents sharing a cloud IP won&apos;t interfere with each other.
              </p>

              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-zinc-200">
                      <th className="text-left py-3 pr-4 font-mono text-[10px] tracking-widest uppercase text-zinc-400">Endpoint group</th>
                      <th className="text-left py-3 px-2 font-mono text-[10px] tracking-widest uppercase text-zinc-400">Limit</th>
                      <th className="text-left py-3 pl-2 font-mono text-[10px] tracking-widest uppercase text-zinc-400">Scope</th>
                    </tr>
                  </thead>
                  <tbody className="text-zinc-600">
                    <tr className="border-b border-zinc-50"><td className="py-2 pr-4"><code className="text-xs">POST /agent/lookup</code></td><td className="py-2 px-2">30/minute</td><td className="py-2 pl-2">Per API key</td></tr>
                    <tr className="border-b border-zinc-50"><td className="py-2 pr-4"><code className="text-xs">POST /agent/quick</code></td><td className="py-2 px-2">10/minute</td><td className="py-2 pl-2">Per API key</td></tr>
                    <tr className="border-b border-zinc-50"><td className="py-2 pr-4"><code className="text-xs">POST /agent/full</code></td><td className="py-2 px-2">5/minute</td><td className="py-2 pl-2">Per API key</td></tr>
                    <tr className="border-b border-zinc-50"><td className="py-2 pr-4"><code className="text-xs">POST /agent/check</code></td><td className="py-2 px-2">10/minute</td><td className="py-2 pl-2">Per API key</td></tr>
                    <tr className="border-b border-zinc-50"><td className="py-2 pr-4"><code className="text-xs">POST /agent/batch</code></td><td className="py-2 px-2">5/minute</td><td className="py-2 pl-2">Per API key</td></tr>
                    <tr className="border-b border-zinc-50"><td className="py-2 pr-4"><code className="text-xs">GET /agent/result/*</code></td><td className="py-2 px-2">30/minute</td><td className="py-2 pl-2">Per API key</td></tr>
                    <tr><td className="py-2 pr-4"><code className="text-xs">GET /agent/health, /tiers, /me</code></td><td className="py-2 px-2">60/minute</td><td className="py-2 pl-2">Per API key</td></tr>
                  </tbody>
                </table>
              </div>

              <p className="text-sm text-zinc-500">
                Pipeline endpoints also enforce a <strong className="text-zinc-700">concurrency limit</strong> of 5 simultaneous
                processing checks per API key. If you hit this limit, you&apos;ll receive a 429 with a
                <code className="text-zinc-400 ml-1">Retry-After: 30</code> header.
              </p>
            </div>
          </section>

          {/* Divider */}
          <div className="border-t border-zinc-200 my-12 md:my-16" />

          {/* Error Codes */}
          <section id="errors" className="mb-16 md:mb-20 scroll-mt-28">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4">
              Module — Error Handling
            </div>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-zinc-900 mb-6 md:mb-8">
              Error Codes
            </h2>

            <div className="space-y-6 text-base text-zinc-600 leading-relaxed">
              <p>
                All errors return JSON with a <code className="text-zinc-400">detail</code> field. Agents should
                handle these programmatically — retry on 429/504, alert on 402, and log on 502.
              </p>

              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-zinc-200">
                      <th className="text-left py-3 pr-4 font-mono text-[10px] tracking-widest uppercase text-zinc-400">Code</th>
                      <th className="text-left py-3 px-2 font-mono text-[10px] tracking-widest uppercase text-zinc-400">Meaning</th>
                      <th className="text-left py-3 pl-2 font-mono text-[10px] tracking-widest uppercase text-zinc-400">Agent action</th>
                    </tr>
                  </thead>
                  <tbody className="text-zinc-600">
                    <tr className="border-b border-zinc-50"><td className="py-2 pr-4 font-mono text-xs">401</td><td className="py-2 px-2">Missing or invalid API key</td><td className="py-2 pl-2 text-xs text-zinc-500">Check X-API-Key header</td></tr>
                    <tr className="border-b border-zinc-50"><td className="py-2 pr-4 font-mono text-xs">402</td><td className="py-2 px-2">Insufficient credit balance</td><td className="py-2 pl-2 text-xs text-zinc-500">Top up via /agent/credits/purchase</td></tr>
                    <tr className="border-b border-zinc-50"><td className="py-2 pr-4 font-mono text-xs">404</td><td className="py-2 px-2">Check not found or not owned</td><td className="py-2 pl-2 text-xs text-zinc-500">Verify check ID and ownership</td></tr>
                    <tr className="border-b border-zinc-50"><td className="py-2 pr-4 font-mono text-xs">409</td><td className="py-2 px-2">Idempotency key reused with different params</td><td className="py-2 pl-2 text-xs text-zinc-500">Use a new idempotency key</td></tr>
                    <tr className="border-b border-zinc-50"><td className="py-2 pr-4 font-mono text-xs">429</td><td className="py-2 px-2">Rate limit or concurrency limit exceeded</td><td className="py-2 pl-2 text-xs text-zinc-500">Wait for Retry-After header value</td></tr>
                    <tr className="border-b border-zinc-50"><td className="py-2 pr-4 font-mono text-xs">502</td><td className="py-2 px-2">Pipeline processing error</td><td className="py-2 pl-2 text-xs text-zinc-500">Retry with same idempotency key</td></tr>
                    <tr><td className="py-2 pr-4 font-mono text-xs">504</td><td className="py-2 px-2">Pipeline timed out (no charge)</td><td className="py-2 pl-2 text-xs text-zinc-500">Retry — consider async mode</td></tr>
                  </tbody>
                </table>
              </div>

              <div className="flex gap-3 bg-zinc-50 border border-zinc-200 p-4">
                <div className="flex-shrink-0 w-6 h-6 bg-accent/10 text-accent flex items-center justify-center font-mono text-xs font-bold rounded">?</div>
                <div className="text-xs text-zinc-600">
                  <p className="font-semibold text-zinc-900 mb-1">Refund policy</p>
                  <p>
                    Pipeline errors (502) and timeouts (504) are automatically refunded — credits are returned
                    to your balance immediately. Only successful completions are charged.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Divider */}
          <div className="border-t border-zinc-200 my-12 md:my-16" />

          {/* Response Shape */}
          <section id="response" className="mb-16 md:mb-20 scroll-mt-28">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4">
              Module — Response Shape
            </div>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-zinc-900 mb-6 md:mb-8">
              What You Get Back
            </h2>

            <pre className="bg-zinc-950 text-zinc-300 p-4 overflow-x-auto text-xs font-mono leading-relaxed">
{`{
  "id": "check-uuid",
  "status": "completed",
  "claims": [
    {
      "text": "Global average temperature rose 1.1°C since pre-industrial times",
      "claimType": "statistical",
      "claimMap": {
        "elements": [
          {
            "elementId": "e1",
            "text": "Global average temperature increase",
            "state": "supported",
            "evidenceRefs": [
              {
                "evidenceId": "ev1",
                "relationship": "supports",
                "reasoning": "NASA GISS dataset confirms 1.1°C anomaly..."
              }
            ]
          }
        ],
        "orientation": "Evidence broadly supports this claim..."
      },
      "evidence": [
        {
          "evidenceId": "ev1",
          "title": "GISS Surface Temperature Analysis",
          "url": "https://data.giss.nasa.gov/gistemp/",
          "tier": "primary",
          "evidenceType": "data",
          "snippet": "Global mean surface temperature anomaly..."
        }
      ]
    }
  ],
  "_meta": {
    "executedTier": "quick",
    "chargedPence": 7,
    "limitations": ["heuristic_classification", "no_coverage_recovery"],
    "cached": false,
    "landscape": {
      "sourceDiversity": { "uniqueDomains": 5, "typeCoverage": 3 },
      "freshness": { "freshestDaysAgo": 2, "undatedCount": 1 },
      "gaps": [],
      "providerStatus": null
    }
  },
  "_manifest": {
    "checkId": "check-uuid",
    "landscapeHash": "a1b2c3d4...",
    "signedAt": "2026-03-09T12:00:00Z",
    "signature": "hmac-sha256:...",
    "kid": "tru8-2026-03",
    "verifyUrl": "/verify/check-uuid"
  },
  "_computed": {
    "summary": { "totalElements": 3, "supported": 2, "disputed": 0, "unresolved": 1 },
    "evidenceByTier": { "primary": 4, "reporting": 8, "commentary": 2 },
    "evidenceByType": { "data": 3, "official": 2, "news": 5, "analysis": 3, "academic": 1 },
    "corroboration": { "groups": [...], "convergenceCount": 3 },
    "diagnosticValues": [...]
  }
}`}
            </pre>

            <div className="mt-6 space-y-3">
              <div className="flex gap-3 bg-zinc-50 border border-zinc-200 p-4">
                <div className="flex-shrink-0 w-6 h-6 bg-accent/10 text-accent flex items-center justify-center font-mono text-xs font-bold rounded">?</div>
                <div className="text-xs text-zinc-600">
                  <p className="font-semibold text-zinc-900 mb-1">claims[].claimMap</p>
                  <p>Each claim is decomposed into 1–5 elements. Evidence maps to elements with relationship types (supports/challenges/context) and reasoning.</p>
                </div>
              </div>
              <div className="flex gap-3 bg-zinc-50 border border-zinc-200 p-4">
                <div className="flex-shrink-0 w-6 h-6 bg-accent/10 text-accent flex items-center justify-center font-mono text-xs font-bold rounded">?</div>
                <div className="text-xs text-zinc-600">
                  <p className="font-semibold text-zinc-900 mb-1">_meta vs _computed</p>
                  <p><code className="text-zinc-400">_meta</code> is always present — tier, cost, limitations, landscape. <code className="text-zinc-400">_computed</code> requires <code className="text-zinc-400">?computed=true</code> — adds analytics, corroboration, diagnostics.</p>
                </div>
              </div>
              <div className="flex gap-3 bg-zinc-50 border border-zinc-200 p-4">
                <div className="flex-shrink-0 w-6 h-6 bg-accent/10 text-accent flex items-center justify-center font-mono text-xs font-bold rounded">?</div>
                <div className="text-xs text-zinc-600">
                  <p className="font-semibold text-zinc-900 mb-1">_manifest</p>
                  <p>HMAC-signed tamper-evidence. Agents can verify results haven&apos;t been modified via <code className="text-zinc-400">GET /verify/{'{'}<span>check_id</span>{'}'}</code>.</p>
                </div>
              </div>
            </div>
          </section>

          {/* Divider */}
          <div className="border-t border-zinc-200 my-12 md:my-16" />

          {/* API Docs + Resources */}
          <section id="docs" className="mb-16 md:mb-20 scroll-mt-28">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4">
              Module — Resources
            </div>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-zinc-900 mb-6 md:mb-8">
              Documentation
            </h2>

            <div className="grid md:grid-cols-2 gap-6">
              <Link
                href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/docs`}
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
                href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/redoc`}
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
          </section>

          {/* CTA */}
          <div className="mt-16 md:mt-20 text-center border border-zinc-200 p-8 md:p-12">
            <div className="flex justify-center mb-4">
              <Key size={32} className="text-zinc-300" />
            </div>
            <h3 className="text-2xl md:text-3xl font-bold text-zinc-900 mb-4">
              Start Building
            </h3>
            <p className="text-zinc-500 mb-6 max-w-lg mx-auto">
              Create an API key and submit your first check in under a minute.
            </p>
            <TrackedLink
              event="get_api_key_click"
              eventProps={{ surface: 'developers_cta' }}
              href="/dashboard/settings?tab=developer"
              className="inline-flex items-center gap-2 px-8 py-4 bg-accent hover:bg-accent/90 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors"
            >
              Get API Key
            </TrackedLink>
          </div>

          {/* Mono metadata footer */}
          <div className="mt-12 pt-6 border-t border-zinc-100">
            <span className="font-mono text-[10px] tracking-widest uppercase text-zinc-400">
              TRU8 — DEVELOPERS — V1.1
            </span>
          </div>
        </div>
      </main>

      <Footer />
    </>
  );
}
