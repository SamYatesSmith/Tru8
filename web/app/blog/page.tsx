import { Navigation } from '@/components/layout/navigation';
import { MobileBottomNav } from '@/components/layout/mobile-bottom-nav';
import { Footer } from '@/components/layout/footer';
import { ArrowLeft, Calendar, ArrowRight } from 'lucide-react';
import Link from 'next/link';

export const metadata = {
  title: 'Blog | Tru8',
  description: 'News, updates, and insights from Tru8 - the fact-checking platform.',
};

// Blog posts data - add new posts here
const blogPosts = [
  {
    slug: 'first-public-release',
    title: 'Tru8 — A First Public Release',
    excerpt: 'This is the first public release of Tru8. There\'s no big announcement behind it — just a tool that\'s ready to be used and tested outside of development.',
    date: '6 January 2026',
    readTime: '4 min read',
  },
];

export default function BlogPage() {
  return (
    <>
      {/* Navigation */}
      <Navigation />
      <MobileBottomNav />

      {/* Main Content */}
      <main className="min-h-screen bg-[#0f1419] pt-24 md:pt-32 pb-24 md:pb-20">
        <div className="container mx-auto px-4 md:px-6 max-w-4xl">
          {/* Back Button */}
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-slate-400 hover:text-[#f57a07] transition-colors mb-6 md:mb-8"
          >
            <ArrowLeft size={20} />
            <span className="text-sm font-medium">Back to Home</span>
          </Link>

          {/* Page Header */}
          <div className="mb-12 md:mb-16">
            <h1 className="text-4xl sm:text-5xl md:text-6xl font-black text-white mb-4">
              Blog
            </h1>
            <p className="text-lg text-slate-400">
              News, updates, and insights from Tru8
            </p>
          </div>

          {/* Blog Posts List */}
          <div className="space-y-6">
            {blogPosts.map((post) => (
              <Link
                key={post.slug}
                href={`/blog/${post.slug}`}
                className="block bg-slate-800/30 border border-slate-700 hover:border-[#f57a07]/50 rounded-xl p-6 md:p-8 transition-all group"
              >
                <div className="flex items-center gap-4 text-sm text-slate-400 mb-3">
                  <span className="flex items-center gap-1.5">
                    <Calendar size={14} />
                    {post.date}
                  </span>
                  <span>·</span>
                  <span>{post.readTime}</span>
                </div>

                <h2 className="text-xl md:text-2xl font-bold text-white mb-3 group-hover:text-[#f57a07] transition-colors">
                  {post.title}
                </h2>

                <p className="text-slate-300 mb-4 leading-relaxed">
                  {post.excerpt}
                </p>

                <span className="inline-flex items-center gap-2 text-[#f57a07] font-medium text-sm group-hover:gap-3 transition-all">
                  Read more
                  <ArrowRight size={16} />
                </span>
              </Link>
            ))}
          </div>
        </div>
      </main>

      {/* Footer */}
      <Footer />
    </>
  );
}
