import { Navigation } from '@/components/layout/navigation';
import { MobileBottomNav } from '@/components/layout/mobile-bottom-nav';
import { Footer } from '@/components/layout/footer';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export const metadata = {
  title: 'Evidence Research for AI Agents, Developers, and MCP — Tru8 API',
  description:
    'Tru8 offers a structured evidence research API and MCP server for AI agents, developer tools, and automated workflows. Multi-source analysis with full provenance, available programmatically.',
  keywords: [
    'evidence research API',
    'fact checking API',
    'MCP server evidence',
    'AI agent evidence research',
    'structured evidence API',
    'claim verification API',
    'source classification API',
    'multi-source research tool',
    'evidence landscape API',
    'MCP tool evidence',
  ],
  openGraph: {
    type: 'article',
    publishedTime: '2026-03-25T00:00:00Z',
    title: 'Evidence Research for AI Agents, Developers, and MCP — Tru8 API',
    description:
      'Structured evidence research as an API. Multi-source analysis with provenance, classification, and six evidence views — for agents, developer tools, and automated workflows.',
  },
};

export default function EvidenceResearchForAgentsPage() {
  return (
    <>
      <Navigation />
      <MobileBottomNav />

      <main className="min-h-screen pt-24 md:pt-32 pb-24 md:pb-20">
        <div className="container mx-auto px-4 md:px-6 max-w-3xl">
          {/* Back Button */}
          <Link
            href="/blog"
            className="inline-flex items-center gap-2 text-zinc-400 hover:text-zinc-900 transition-colors mb-6 md:mb-8"
          >
            <ArrowLeft size={20} />
            <span className="text-sm font-medium">Back to Blog</span>
          </Link>

          {/* Article Header */}
          <header className="mb-10 md:mb-12">
            <div className="font-mono text-[10px] tracking-widest uppercase text-zinc-400 mb-4 flex items-center gap-4">
              <span>25 March 2026</span>
              <span>·</span>
              <span>5 min read</span>
            </div>

            <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold text-zinc-900 leading-tight">
              Evidence Research for AI Agents and Developer Tools
            </h1>

            <div className="mt-4 font-mono text-[10px] tracking-widest uppercase text-zinc-400">
              Author — Sam Yates-Smith
            </div>
          </header>

          {/* Article Content */}
          <article className="space-y-6 text-zinc-600 text-base md:text-lg leading-relaxed">
            <p className="text-xl md:text-2xl text-zinc-900 font-medium">
              Tru8&apos;s evidence research pipeline is now available as an API and MCP server — so developers, AI agents, and automated workflows can run structured, multi-source analysis programmatically.
            </p>

            <p>
              This post covers what the API does, how the MCP server works, and why structured evidence research is a useful capability for agent-based systems.
            </p>

            <h2 className="text-2xl md:text-3xl font-bold text-zinc-900 pt-6">
              Why Evidence Research Needs Structure
            </h2>

            <p>
              A web search returns links. A language model returns prose. Neither gives you a structured picture of what the evidence actually looks like across multiple source types.
            </p>

            <p>
              Tru8 sits in the gap between search and synthesis. Given a claim, it searches across 30+ source categories — government data, academic papers, news, official records, legislation, economic indicators, health data — and returns a structured evidence landscape. Every source is classified by tier (primary, reporting, commentary) and type (data, official, news, analysis, opinion, academic). Nothing is hidden; exclusions are logged with reasons.
            </p>

            <p>
              For developers building tools that need to reason about claims, this structure matters. It&apos;s the difference between &ldquo;here are some links&rdquo; and &ldquo;here is the shape of the evidence, classified and mapped to the specific parts of the claim they address.&rdquo;
            </p>

            <h2 className="text-2xl md:text-3xl font-bold text-zinc-900 pt-6">
              The API
            </h2>

            <p>
              The Tru8 API provides evidence research at multiple levels of depth, so you can choose the right balance of speed and thoroughness for your use case.
            </p>

            <h3 className="text-lg md:text-xl font-bold text-zinc-900 pt-4">Lookup</h3>
            <p>
              Instant retrieval of previously researched claims. If someone has already run a full analysis on a claim, you get the structured result immediately. Useful for high-volume systems that want to check before committing to a full research run.
            </p>

            <h3 className="text-lg md:text-xl font-bold text-zinc-900 pt-4">Quick Analysis</h3>
            <p>
              A streamlined evidence pass that completes in roughly 15 seconds. Core retrieval and classification without the full depth of coverage recovery or extended source searching. Well-suited for real-time applications, chatbots, or agent workflows where responsiveness matters.
            </p>

            <h3 className="text-lg md:text-xl font-bold text-zinc-900 pt-4">Full Analysis</h3>
            <p>
              The complete pipeline. Claims are decomposed into elements, evidence is retrieved from 30+ source categories, scored for relevance, classified by tier and type, and mapped back to the specific elements they address. The result is a full evidence landscape — the same structured output available in the Tru8 dashboard.
            </p>

            <h3 className="text-lg md:text-xl font-bold text-zinc-900 pt-4">Smart Endpoint</h3>
            <p>
              A single endpoint that handles tier selection automatically. It checks for cached results first, falls back to quick analysis if speed is preferred, and escalates to full analysis when depth is needed. One call, server-side routing.
            </p>

            <p>
              Every response includes full provenance — which sources were found, how they were classified, what was excluded (and why), and the method used for each classification decision.
            </p>

            <h2 className="text-2xl md:text-3xl font-bold text-zinc-900 pt-6">
              MCP Server for AI Agents
            </h2>

            <p>
              Tru8 provides a{' '}
              <span className="font-medium text-zinc-900">Model Context Protocol (MCP)</span>{' '}
              server, which means AI agents built on any supporting platform can call Tru8 as a tool — the same way they might call a calculator or a web browser.
            </p>

            <p>
              The MCP server exposes a single <code className="text-sm bg-zinc-100 px-1.5 py-0.5 font-mono">tru8_check</code> tool. An agent passes a claim and optionally a maximum tier, and receives a structured evidence landscape in return. Tier fallback is handled automatically — if a full analysis isn&apos;t available, the server returns the best available result.
            </p>

            <p>
              This is particularly useful for agent workflows that need to:
            </p>

            <ul className="list-disc list-outside ml-6 space-y-2 text-zinc-600">
              <li>Ground responses in real, cited evidence rather than parametric knowledge</li>
              <li>Verify claims before presenting them to users</li>
              <li>Provide structured source breakdowns alongside generated text</li>
              <li>Add evidence research as a step in a multi-tool reasoning chain</li>
              <li>Audit the provenance of information used in automated decision-making</li>
            </ul>

            <p>
              Because the output is structured (not prose), agents can reason over the evidence programmatically — filtering by tier, checking element-level support, or surfacing gaps where evidence is missing.
            </p>

            <h2 className="text-2xl md:text-3xl font-bold text-zinc-900 pt-6">
              What the Response Looks Like
            </h2>

            <p>
              Every Tru8 API response returns a consistent structure, regardless of tier:
            </p>

            <ul className="list-disc list-outside ml-6 space-y-2 text-zinc-600">
              <li><span className="font-medium text-zinc-900">Claims</span> — the input decomposed into discrete, researchable elements</li>
              <li><span className="font-medium text-zinc-900">Evidence</span> — sources found, each classified by tier (primary, reporting, commentary) and type (data, official, news, analysis, opinion, academic)</li>
              <li><span className="font-medium text-zinc-900">Mapping</span> — which evidence addresses which elements, and the relationship (supports, challenges, or provides context)</li>
              <li><span className="font-medium text-zinc-900">Landscape</span> — aggregate metrics including source diversity, tier distribution, and coverage gaps</li>
              <li><span className="font-medium text-zinc-900">Provenance</span> — classification method, relevance scores, content basis, and receipts for every exclusion</li>
            </ul>

            <p>
              This isn&apos;t a summary or a verdict. It&apos;s a structured dataset that your application or agent can interpret, filter, and present however it needs to.
            </p>

            <h2 className="text-2xl md:text-3xl font-bold text-zinc-900 pt-6">
              Use Cases
            </h2>

            <p>
              Some of the ways developers and teams are integrating Tru8:
            </p>

            <ul className="list-disc list-outside ml-6 space-y-2 text-zinc-600">
              <li><span className="font-medium text-zinc-900">AI assistants</span> — adding evidence grounding to conversational agents, so claims are checked before being surfaced to users</li>
              <li><span className="font-medium text-zinc-900">Content moderation</span> — automated evidence checks on user-submitted claims or flagged content</li>
              <li><span className="font-medium text-zinc-900">Research tools</span> — integrating structured evidence search into academic or journalistic workflows</li>
              <li><span className="font-medium text-zinc-900">Filings and disclosures</span> — checking claims in regulatory filings, reports, or public statements</li>
              <li><span className="font-medium text-zinc-900">Browser extensions</span> — inline evidence checks on articles, social media posts, or search results</li>
              <li><span className="font-medium text-zinc-900">Agent pipelines</span> — evidence research as one step in a larger automated reasoning or decision-making workflow</li>
            </ul>

            <h2 className="text-2xl md:text-3xl font-bold text-zinc-900 pt-6">
              Getting Started
            </h2>

            <p>
              The API is live and available now. API keys can be created from the{' '}
              <Link href="/developers" className="text-accent hover:underline font-medium">developer portal</Link>,
              which also includes endpoint documentation, example requests, and response schemas.
            </p>

            <p>
              The MCP server can be added to any MCP-compatible agent framework. Configuration details are in the developer documentation.
            </p>

            <p>
              If you&apos;re building something that needs structured evidence research — whether it&apos;s an agent, an internal tool, or a product feature — the pipeline is there. We&apos;d be interested to hear what you build with it.
            </p>
          </article>

          {/* CTA Section */}
          <div className="mt-12 md:mt-16 text-center border border-zinc-200 p-8 md:p-10">
            <h3 className="text-xl md:text-2xl font-bold text-zinc-900 mb-3">
              Start building with Tru8
            </h3>
            <p className="text-zinc-500 mb-6">
              API keys, documentation, and example requests — all in one place.
            </p>
            <Link
              href="/developers"
              className="inline-flex items-center gap-2 px-8 py-4 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors"
            >
              Developer Portal
            </Link>
          </div>

          {/* Back to Blog */}
          <div className="mt-10 pt-8 border-t border-zinc-200">
            <Link
              href="/blog"
              className="inline-flex items-center gap-2 text-zinc-400 hover:text-zinc-900 transition-colors"
            >
              <ArrowLeft size={18} />
              <span className="font-medium">Back to all posts</span>
            </Link>
          </div>
        </div>
      </main>

      <Footer />
    </>
  );
}
