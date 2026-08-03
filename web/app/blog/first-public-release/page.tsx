import { Navigation } from '@/components/layout/navigation';
import { MobileBottomNav } from '@/components/layout/mobile-bottom-nav';
import { Footer } from '@/components/layout/footer';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export const metadata = {
  title: 'Tru8 — A First Public Release',
  description: 'The first public release of Tru8 — an evidence research platform with a dashboard, API, and MCP server for AI agents.',
  openGraph: { type: 'article', publishedTime: '2026-01-06T00:00:00Z' },
};

export default function FirstPublicReleasePage() {
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
              <span>6 January 2026</span>
              <span>·</span>
              <span>6 min read</span>
            </div>

            <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold text-zinc-900 leading-tight">
              Tru8 — A First Public Release
            </h1>

            <div className="mt-4 font-mono text-[10px] tracking-widest uppercase text-zinc-400">
              Author — Sam Yates-Smith
            </div>
          </header>

          {/* Article Content */}
          <article className="space-y-6 text-zinc-600 text-base md:text-lg leading-relaxed">
            <p className="text-xl md:text-2xl text-zinc-900 font-medium">
              This is the first public release of Tru8.
            </p>

            <p>
              There&apos;s no big announcement behind it — just a tool that&apos;s ready to be used and tested outside of development. This post is here to explain what Tru8 is, why it exists, and what to expect from it at this stage.
            </p>

            <h2 className="text-2xl md:text-3xl font-bold text-zinc-900 pt-6">Why Tru8 Exists</h2>

            <p>
              The internet has never had more information, yet it often feels harder than ever to understand what&apos;s actually well-supported.
            </p>

            <p>
              Headlines are written to grab attention. Claims spread quickly. Different sources say different things about the same topic, and working out what&apos;s well-supported can take more time than most people realistically have.
            </p>

            <p className="text-zinc-900 font-medium">
              Tru8 exists to make that process simpler.
            </p>

            <p>
              It doesn&apos;t aim to replace research or tell people what to think. The goal is to take a claim and present the available evidence clearly, so people can understand what it&apos;s based on and decide for themselves.
            </p>

            <h2 className="text-2xl md:text-3xl font-bold text-zinc-900 pt-6">What Tru8 Does</h2>

            <p>
              Tru8 helps you research claims.
            </p>

            <p>
              You paste in a statement, and Tru8 searches for relevant sources, compares what they say, and presents the findings in a clear, structured way. All sources used are shown, so you can explore them further if you want to.
            </p>

            <p>
              The focus is on clarity rather than commentary — showing what sources say, where they agree, and where they don&apos;t.
            </p>

            <h2 className="text-2xl md:text-3xl font-bold text-zinc-900 pt-6">How Tru8 Might Be Useful</h2>

            <p>
              Tru8 is built around a simple idea: if you&apos;re looking at a claim and want to understand what the evidence says, it should be straightforward to find out. Here are some of the ways people are using it.
            </p>

            <h3 className="text-lg md:text-xl font-bold text-zinc-900 pt-4">Journalists and Editors</h3>
            <ul className="list-disc list-outside ml-6 space-y-2 text-zinc-600">
              <li>Quickly cross-reference claims before publication</li>
              <li>See which government data, academic papers, or official records relate to a story</li>
              <li>Identify where sources agree and where they diverge</li>
            </ul>

            <h3 className="text-lg md:text-xl font-bold text-zinc-900 pt-4">Students and Academics</h3>
            <ul className="list-disc list-outside ml-6 space-y-2 text-zinc-600">
              <li>Research essay topics with structured evidence from multiple source types</li>
              <li>Find academic papers, government data, and official records in one place</li>
              <li>Understand the balance of evidence before forming an argument</li>
              <li>Export sources and citations for bibliographies</li>
            </ul>

            <h3 className="text-lg md:text-xl font-bold text-zinc-900 pt-4">Content Creators and YouTubers</h3>
            <ul className="list-disc list-outside ml-6 space-y-2 text-zinc-600">
              <li>Verify claims before including them in videos or podcasts</li>
              <li>Research trending topics and understand what the evidence actually supports</li>
              <li>Build credibility with audiences by showing your claims are well-sourced</li>
              <li>Quickly sense-check statements from interviews or social media</li>
            </ul>

            <h3 className="text-lg md:text-xl font-bold text-zinc-900 pt-4">Professionals and Analysts</h3>
            <ul className="list-disc list-outside ml-6 space-y-2 text-zinc-600">
              <li>Research market claims, competitor statements, or industry data</li>
              <li>Compare what multiple sources say about economic or regulatory topics</li>
              <li>Prepare briefings with classified, cited evidence</li>
            </ul>

            <h3 className="text-lg md:text-xl font-bold text-zinc-900 pt-4">Everyday Use</h3>
            <ul className="list-disc list-outside ml-6 space-y-2 text-zinc-600">
              <li>Check headlines that feel exaggerated</li>
              <li>Research health, science, or political claims shared on social media</li>
              <li>Compare conflicting news articles to see the full picture</li>
              <li>Settle disagreements with evidence rather than opinion</li>
            </ul>

            <p>
              If you&apos;re unsure about a claim, that&apos;s usually a good moment to try Tru8.
            </p>

            <h2 className="text-2xl md:text-3xl font-bold text-zinc-900 pt-6">Feedback That Helps Most</h2>

            <p>
              If you do use Tru8, honest feedback is genuinely helpful.
            </p>

            <p>In particular:</p>

            <ul className="list-disc list-outside ml-6 space-y-2 text-zinc-600">
              <li>Are the results easy to understand?</li>
              <li>Do the sources feel relevant and trustworthy?</li>
              <li>Does the evidence report help you understand the claim?</li>
              <li>Where does Tru8 fall short or feel unclear?</li>
            </ul>

            <p>
              Knowing where Tru8 doesn&apos;t help is just as important as knowing where it does.
            </p>

            <h2 className="text-2xl md:text-3xl font-bold text-zinc-900 pt-6">For Developers and AI Agents</h2>

            <p>
              Everything available in the dashboard is also available programmatically. Tru8 offers a full API and an MCP server, so developers and AI agents can run structured evidence research from their own tools.
            </p>

            <p>The API supports multiple tiers depending on what you need:</p>

            <ul className="list-disc list-outside ml-6 space-y-2 text-zinc-600">
              <li><span className="font-medium text-zinc-900">Lookup</span> — instant cached results for claims that have already been researched</li>
              <li><span className="font-medium text-zinc-900">Quick</span> — a faster analysis (~15 seconds) with core evidence retrieval</li>
              <li><span className="font-medium text-zinc-900">Full</span> — the complete pipeline, searching published sources with tier and type classification, element decomposition, and six-view evidence landscape</li>
            </ul>

            <p>
              The MCP server means AI agents built on Claude, GPT, or other platforms can call Tru8 directly — adding structured evidence research to any agent workflow. Every response includes full provenance: which sources were found, how they were classified, and what was excluded (with reasons).
            </p>

            <p>
              Developer documentation and API keys are available from the{' '}
              <Link href="/developers" className="text-accent hover:underline font-medium">developer portal</Link>.
              For a deeper look at how the API and MCP server work in agent systems,{' '}
              <Link href="/blog/evidence-research-for-agents" className="text-accent hover:underline font-medium">
                read our guide to evidence research for AI agents
              </Link>.
            </p>

            <h2 className="text-2xl md:text-3xl font-bold text-zinc-900 pt-6">What Comes Next</h2>

            <p>
              This release is the foundation, not the ceiling. There is significant work underway to take Tru8 beyond single-claim analysis into deeper, more comprehensive research workflows.
            </p>

            <p>
              That means longer-form investigation across interconnected claims, richer output with detailed structured reports, and broader source coverage. The aim is for Tru8 to become a complete evidence research suite — from a quick headline check through to in-depth, multi-source analysis that you can act on, cite, or publish.
            </p>

            <p>
              Tru8 will continue to improve through better sourcing, broader coverage, and refinements shaped by real usage. The direction it takes will be informed by how people actually use it and where it falls short.
            </p>

            <p>
              The aim is to keep Tru8 grounded, transparent, and genuinely useful — for people and for the tools they build.
            </p>

            <h2 className="text-2xl md:text-3xl font-bold text-zinc-900 pt-6">A Final Note</h2>

            <p>
              Thanks for taking the time to try Tru8 or read about its first release.
            </p>

            <p>
              If it brings a little clarity to something you&apos;ve read online, then it&apos;s already moving in the right direction.
            </p>
          </article>

          {/* CTA Section */}
          <div className="mt-12 md:mt-16 text-center border border-zinc-200 p-8 md:p-10">
            <h3 className="text-xl md:text-2xl font-bold text-zinc-900 mb-3">
              Ready to try Tru8?
            </h3>
            <p className="text-zinc-500 mb-6">
              Try Tru8. Your first checks are free.
            </p>
            <Link
              href="/"
              className="inline-flex items-center gap-2 px-8 py-4 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors"
            >
              Get Started Free
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
