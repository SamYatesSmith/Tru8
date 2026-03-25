import { Navigation } from '@/components/layout/navigation';
import { MobileBottomNav } from '@/components/layout/mobile-bottom-nav';
import { Footer } from '@/components/layout/footer';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import Link from 'next/link';

export const metadata = {
  title: 'Blog',
  description: 'News, updates, and insights on AI-powered evidence research from Tru8 — including the API, MCP server, and agent integrations.',
  alternates: { canonical: '/blog' },
};

const blogPosts = [
  {
    slug: 'evidence-research-for-agents',
    title: 'Evidence Research for AI Agents and Developer Tools',
    excerpt: 'Tru8\'s evidence research pipeline is now available as an API and MCP server. Structured, multi-source analysis for agents, developer tools, and automated workflows.',
    date: '25 March 2026',
    readTime: '5 min read',
  },
  {
    slug: 'first-public-release',
    title: 'Tru8 — A First Public Release',
    excerpt: 'The first public release of Tru8 — an evidence research platform with a dashboard, API, and MCP server for AI agents. No big announcement, just a tool that\'s ready.',
    date: '6 January 2026',
    readTime: '6 min read',
  },
];

export default function BlogPage() {
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

          {/* Page Header */}
          <div className="mb-12 md:mb-16">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4">
              Publication Archive
            </div>
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold text-zinc-900 mb-4">
              Blog
            </h1>
            <p className="text-lg text-zinc-500">
              News, updates, and insights from Tru8 — platform, API, and agent integrations
            </p>
          </div>

          {/* Blog Posts List */}
          <div className="space-y-6">
            {blogPosts.map((post) => (
              <Link
                key={post.slug}
                href={`/blog/${post.slug}`}
                className="block bg-white border border-zinc-200 hover:border-black p-6 md:p-8 transition-colors group"
              >
                <div className="flex items-center gap-4 font-mono text-[10px] tracking-widest uppercase text-zinc-400 mb-3">
                  <span>{post.date}</span>
                  <span>·</span>
                  <span>{post.readTime}</span>
                </div>

                <h2 className="text-xl md:text-2xl font-bold text-zinc-900 mb-3 group-hover:text-accent transition-colors">
                  {post.title}
                </h2>

                <p className="text-zinc-500 mb-4 leading-relaxed">
                  {post.excerpt}
                </p>

                <span className="inline-flex items-center gap-2 text-zinc-900 font-medium text-sm group-hover:gap-3 transition-all">
                  Read more
                  <ArrowRight size={16} />
                </span>
              </Link>
            ))}
          </div>
        </div>
      </main>

      <Footer />
    </>
  );
}
