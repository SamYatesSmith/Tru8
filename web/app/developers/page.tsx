import { Navigation } from '@/components/layout/navigation';
import { MobileBottomNav } from '@/components/layout/mobile-bottom-nav';
import { Footer } from '@/components/layout/footer';
import { ArrowLeft, Key, Zap, Search, FileJson, BarChart3, ShieldCheck } from 'lucide-react';
import Link from 'next/link';

export const metadata = {
  title: 'Developers | Tru8',
  description: 'Tru8 API for AI agents — structured evidence research in one call. Submit claims or URLs, retrieve evidence organized by source tier and type.',
};

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
          <section className="mb-16 md:mb-20">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4">
              Module — Developer API
            </div>
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold text-zinc-900 mb-6 md:mb-8">
              Evidence Research for AI Agents
            </h1>

            <div className="space-y-6 text-base md:text-lg text-zinc-600 leading-relaxed">
              <p>
                Submit a claim or URL. Get back structured evidence — organized by source tier
                (primary, reporting, commentary) and type (data, official, news, analysis, academic),
                with element decomposition and relationship mapping.
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

          {/* Divider */}
          <div className="border-t border-zinc-200 my-12 md:my-16" />

          {/* Quick Start */}
          <section className="mb-16 md:mb-20">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4">
              Module — Quick Start
            </div>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-zinc-900 mb-6 md:mb-8">
              Three Steps
            </h2>

            <div className="space-y-8">
              {/* Step 1 */}
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 bg-zinc-900 text-white flex items-center justify-center font-mono text-sm font-bold">
                  1
                </div>
                <div>
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
                <div className="flex-shrink-0 w-8 h-8 bg-zinc-900 text-white flex items-center justify-center font-mono text-sm font-bold">
                  2
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-zinc-900 mb-2">Submit a claim</h3>
                  <pre className="bg-zinc-950 text-zinc-300 p-4 overflow-x-auto text-xs font-mono leading-relaxed">
{`curl -N -X POST https://api.tru8.app/api/v1/checks/stream \\
  -H "X-API-Key: $TRU8_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"input_type": "text", "content": "Global average temperature rose 1.1°C since pre-industrial times"}'`}
                  </pre>
                  <p className="text-zinc-500 text-xs mt-2 font-mono">
                    Returns SSE stream → completed event with check ID
                  </p>
                </div>
              </div>

              {/* Step 3 */}
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 bg-zinc-900 text-white flex items-center justify-center font-mono text-sm font-bold">
                  3
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-zinc-900 mb-2">Retrieve the result</h3>
                  <pre className="bg-zinc-950 text-zinc-300 p-4 overflow-x-auto text-xs font-mono leading-relaxed">
{`curl https://api.tru8.app/api/v1/checks/{check_id}?computed=true \\
  -H "X-API-Key: $TRU8_API_KEY"`}
                  </pre>
                  <p className="text-zinc-500 text-xs mt-2 font-mono">
                    ?computed=true adds pre-computed analytics — tier/type distributions, corroboration, diagnostics
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Divider */}
          <div className="border-t border-zinc-200 my-12 md:my-16" />

          {/* Pipeline Modes */}
          <section className="mb-16 md:mb-20">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4">
              Module — Pipeline Modes
            </div>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-zinc-900 mb-6 md:mb-8">
              Two Speeds
            </h2>

            <div className="grid md:grid-cols-2 gap-6">
              <div className="border border-zinc-200 p-6">
                <div className="flex items-center gap-3 mb-4">
                  <Search size={20} className="text-zinc-400" />
                  <h3 className="font-semibold text-zinc-900">Full Analysis</h3>
                </div>
                <p className="text-sm text-zinc-600 mb-3">
                  Complete pipeline: extract claims, retrieve evidence, decompose into elements,
                  map evidence to elements with relationship labels.
                </p>
                <div className="font-mono text-xs text-zinc-400">
                  60–120s · mode: &quot;full&quot; (default)
                </div>
              </div>

              <div className="border border-zinc-200 p-6">
                <div className="flex items-center gap-3 mb-4">
                  <Zap size={20} className="text-zinc-400" />
                  <h3 className="font-semibold text-zinc-900">Snapshot</h3>
                </div>
                <p className="text-sm text-zinc-600 mb-3">
                  Fast scan: extract claims and retrieve evidence only. No decomposition, no mapping.
                  Raw evidence with tier and type classification.
                </p>
                <div className="font-mono text-xs text-zinc-400">
                  12–18s · mode: &quot;snapshot&quot;
                </div>
              </div>
            </div>
          </section>

          {/* Divider */}
          <div className="border-t border-zinc-200 my-12 md:my-16" />

          {/* MCP Server */}
          <section className="mb-16 md:mb-20">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4">
              Module — MCP Integration
            </div>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-zinc-900 mb-6 md:mb-8">
              MCP Server
            </h2>

            <p className="text-base md:text-lg text-zinc-600 mb-8 leading-relaxed">
              Tru8 exposes four tools via the{' '}
              <span className="text-zinc-900 font-medium">Model Context Protocol</span>.
              Any MCP-compatible agent (Claude, GPT, Gemini) can discover and use Tru8 automatically.
            </p>

            <div className="space-y-4">
              {[
                {
                  name: 'tru8_check_claim',
                  desc: 'Full evidence research — claims, elements, evidence maps, computed analytics',
                  time: '60–120s',
                },
                {
                  name: 'tru8_quick_check',
                  desc: 'Fast evidence snapshot — claims with raw evidence, no decomposition',
                  time: '12–18s',
                },
                {
                  name: 'tru8_get_result',
                  desc: 'Retrieve completed check with pre-computed analytics (_computed block)',
                  time: '<1s',
                },
                {
                  name: 'tru8_get_result_raw',
                  desc: 'Retrieve raw check data without computed analytics',
                  time: '<1s',
                },
              ].map((tool) => (
                <div key={tool.name} className="flex items-start gap-4 border border-zinc-200 p-4">
                  <div className="flex-shrink-0 mt-0.5">
                    <FileJson size={16} className="text-zinc-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <code className="text-sm font-mono font-semibold text-zinc-900">{tool.name}</code>
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

          {/* Response Shape */}
          <section className="mb-16 md:mb-20">
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
        "orientationLine": "Evidence broadly supports this claim..."
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
  "_computed": {
    "summary": { "totalElements": 3, "supported": 2, "disputed": 0, "unresolved": 1 },
    "evidenceByTier": { "primary": 4, "reporting": 8, "commentary": 2 },
    "evidenceByType": { "data": 3, "official": 2, "news": 5, "analysis": 3, "academic": 1 },
    "corroboration": { "groups": [...], "convergenceCount": 3 },
    "diagnosticValues": [...]
  }
}`}
            </pre>
          </section>

          {/* Divider */}
          <div className="border-t border-zinc-200 my-12 md:my-16" />

          {/* API Docs + Resources */}
          <section className="mb-16 md:mb-20">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4">
              Module — Resources
            </div>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-zinc-900 mb-6 md:mb-8">
              Documentation
            </h2>

            <div className="grid md:grid-cols-2 gap-6">
              <Link
                href="https://api.tru8.app/api/docs"
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
                href="https://api.tru8.app/api/redoc"
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
            <Link
              href="/dashboard/settings?tab=developer"
              className="inline-flex items-center gap-2 px-8 py-4 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors"
            >
              Get API Key
            </Link>
          </div>

          {/* Mono metadata footer */}
          <div className="mt-12 pt-6 border-t border-zinc-100">
            <span className="font-mono text-[10px] tracking-widest uppercase text-zinc-400">
              TRU8 — DEVELOPERS — V1.0
            </span>
          </div>
        </div>
      </main>

      <Footer />
    </>
  );
}
